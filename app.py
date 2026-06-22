"""
Olive LCSA — Social questionnaire platform  (plain, multilingual HE/AR/EN, no AI)
Questions are loaded from questions.json (generated from the approved ethics file).
Storage: posts each response to a Google Apps Script web app (WEBHOOK_URL),
with a local responses.csv fallback for testing.
"""
import csv, json, os, random, string
import datetime as dt
import streamlit as st
try:
    from streamlit_drawable_canvas import st_canvas
    HAVE_CANVAS = True
except Exception:
    HAVE_CANVAS = False

# ---------- load question bank ----------
HERE = os.path.dirname(os.path.abspath(__file__))
def _load(name, default):
    try:
        return json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    except Exception:
        return default
QDATA = _load("questions.json", {"scales": {}, "forms": {}})
SCALES = QDATA.get("scales", {})
FORMS = QDATA.get("forms", {})
CONSENT_DATA = _load("consent.json", None)

# ---------- storage ----------
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwCa1e2XSAH4h9L7ACpThC8jkaBpevywpwVezTcp3H32xhC17k1eN5wA7XoNpO7tls5tg/exec"   # paste your Apps Script /exec URL here, or set webhook_url in Secrets
def _secret(k, fallback=""):
    try:
        if k in st.secrets:
            return st.secrets[k]
    except Exception:
        pass
    return fallback

def _save_row(row):
    """Returns (status, detail). status in: sheet, rejected, csv_error, csv_nourl."""
    import urllib.request
    url = _secret("webhook_url", WEBHOOK_URL)
    if url:
        try:
            payload = dict(row)
            tok = _secret("form_token", "")
            if tok:
                payload["token"] = tok
            req = urllib.request.Request(
                url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            body = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            if '"ok":true' in body.replace(" ", ""):
                return ("sheet", "")
            return ("rejected", body[:300])
        except Exception as e:
            _csv(row)
            return ("csv_error", str(e))
    _csv(row)
    return ("csv_nourl", "")

def _csv(row):
    path = os.path.join(HERE, "responses.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(list(row.keys()))
        w.writerow([json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for v in row.values()])

# ---------- helpers ----------
def OPT(he, ar, en): return {"he": he, "ar": ar, "en": en}
def t(d, lang):
    if not isinstance(d, dict): return d or ""
    return d.get(lang) or d.get("he") or d.get("en") or ""
def tlist(d, lang):
    return d.get(lang) or d.get("he") or d.get("en") or []

# respondent code: <FARM>-<rel><age><pay>-<rand>
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_REL = {"owner":"O","worker":"W","family":"F","friend":"C"}
_AGE = {"adult":"A","adolescent":"T","child":"K"}
_PAY = {"paid":"P","volunteer":"V",None:"X"}
def make_code(owner, rel, age, comp):
    farm = "".join(ch for ch in owner.upper() if ch.isalnum())[:5] or "FARM"
    rand = "".join(random.choices(ALPHABET, k=4))
    return f"{farm}-{_REL[rel]}{_AGE[age]}{_PAY.get(comp,'X')}-{rand}"

def form_for(relation, comp, age):
    if comp == "paid": return "worker"
    if relation == "owner": return "owner"
    if age == "child": return "family_child"
    if age == "adolescent": return "family_adolescent"
    if relation == "friend": return "volunteer"
    return "family_adult"

def consent_variant(rel, age, comp):
    if age == "child": return "child"
    if age == "adolescent": return "adolescent"
    if comp == "paid": return "worker"
    if rel == "friend": return "volunteer"
    return rel  # owner / family

# ---------- UI strings ----------
UI = {
 "title": OPT("שאלון — גידול זיתים בישראל","استبيان — زراعة الزيتون في إسرائيل","Questionnaire — Olive cultivation in Israel"),
 "pick_lang": OPT("בחרו שפה","اختر اللغة","Choose a language"),
 "no_owner": OPT("קישור לא תקין — אנא השתמשו בקישור האישי שקיבלתם.","رابط غير صالح — يرجى استخدام الرابط الشخصي.","Invalid link — please use the personal link you were given."),
 "next": OPT("המשך","متابعة","Continue"),
 "submit": OPT("שליחה","إرسال","Submit"),
 "relation_q": OPT("מה הקשר שלך לחווה?","ما علاقتك بالمزرعة؟","What is your relation to the farm?"),
 "rel_owner": OPT("בעל/ת החווה","صاحب/ة المزرعة","Owner"),
 "rel_worker": OPT("עובד/ת שכיר/ה (לא מהמשפחה)","عامل/ة مأجور (ليس من العائلة)","Hired worker (not family)"),
 "rel_family": OPT("בן/בת משפחה","فرد من العائلة","Family member"),
 "rel_friend": OPT("חבר/ה או בן/בת קהילה","صديق/ة أو فرد من المجتمع","Friend / community member"),
 "age_q": OPT("מהי קבוצת הגיל?","ما هي الفئة العمرية؟","Age group?"),
 "age_adult": OPT("מבוגר/ת (18+)","بالغ (18+)","Adult (18+)"),
 "age_adol": OPT("נער/ה (14–17)","مراهق (14–17)","Adolescent (14–17)"),
 "age_child": OPT("ילד/ה (8–13)","طفل (8–13)","Child (8–13)"),
 "comp_q": OPT("האם העבודה בשכר או בהתנדבות?","هل العمل بأجر أم تطوعي؟","Is the work paid or voluntary?"),
 "comp_paid": OPT("בשכר","بأجر","Paid"),
 "comp_vol": OPT("בהתנדבות","تطوعي","Voluntary"),
 "worker_locked": OPT("כעובד/ת בשכר — ההשתתפות מתייחסת לעבודה בשכר.","كعامل بأجر.","As a paid worker, this refers to paid employment."),
 "child_locked": OPT("בגיל זה ההשתתפות בהתנדבות בלבד.","في هذا العمر المشاركة تطوعية فقط.","At this age, participation is voluntary only."),
 "consent_h": OPT("הסכמה מדעת","الموافقة المستنيرة","Informed consent"),
 "agree": OPT("קראתי ואני מסכים/ה להשתתף","قرأت وأوافق على المشاركة","I have read this and agree to take part"),
 "parental": OPT("אני ההורה/אפוטרופוס ונותן/ת אישור","أنا الوالد/الوصي وأمنح الإذن","I am the parent/guardian and give permission"),
 "assent": OPT("אני מסכים/ה להשתתף","أوافق على المشاركة","I agree to take part"),
 "must_agree": OPT("יש לאשר את ההסכמה כדי להמשיך.","يجب الموافقة للمتابعة.","Please confirm consent to continue."),
 "select_all": OPT("(ניתן לבחור יותר מאחד)","(يمكن اختيار أكثر من واحد)","(select all that apply)"),
 "typing_help": OPT("אפשר לענות בעצמך, או שמישהו — הורה או אדם מבוגר יותר — יכול להקליד עבורך. רק אם בא לך.","يمكنك الإجابة بنفسك، أو يمكن لشخص — أحد الوالدين أو شخص أكبر — أن يكتب إجاباتك بدلاً عنك. فقط إذا أردت.","You can answer by yourself, or someone — a parent or an older person — can type your answers for you. Only if you want to."),
 "thanks": OPT("תודה רבה! התשובות נשמרו.","شكراً جزيلاً! تم حفظ إجاباتك.","Thank you! Your answers were saved."),
 "owner_prior": OPT("חתמת על טופס ההסכמה באופן אישי במהלך המפגש שלנו.",
                    "لقد وقّعت على نموذج الموافقة شخصياً خلال لقائنا.",
                    "You signed the consent form in person when we met."),
 "confirm_signed": OPT("אני מאשר/ת שחתמתי על טופס ההסכמה",
                       "أؤكد أنني وقّعت على نموذج الموافقة",
                       "I confirm that I have signed the consent form"),
 "sign_prompt": OPT("חתמו כאן באמצעות העכבר או האצבע:",
                    "وقّع هنا باستخدام الفأرة أو إصبعك:",
                    "Sign below using your mouse or finger:"),
 "parent_sign": OPT("הורה/אפוטרופוס: חתמו כאן:",
                    "الوالد/الوصي: وقّع هنا:",
                    "Parent / guardian: sign below:"),
 "typed_sig": OPT("הקלידו את שמכם המלא כחתימה:",
                  "اكتب اسمك الكامل كتوقيع:",
                  "Type your full name as your signature:"),
 "sign_required": OPT("יש לחתום כדי להמשיך.","التوقيع مطلوب للمتابعة.","A signature is required to continue."),
}

# fallback consent text (used only if consent.json is absent)
BASE = OPT("ההשתתפות התנדבותית; ניתן להפסיק בכל שלב. התשובות משמשות למחקר בלבד ונשמרות באופן מאובטח.",
           "المشاركة طوعية ويمكنك التوقف في أي وقت. تُستخدم الإجابات للبحث فقط.",
           "Participation is voluntary; you may stop at any time. Answers are used for research only and stored securely.")
def consent_text(variant):
    if CONSENT_DATA and variant in CONSENT_DATA:
        return CONSENT_DATA[variant]
    minor = variant in ("adolescent", "child")
    return {"body": BASE, "minor": minor}

def signature_widget(key):
    """Mouse/finger signature -> base64 PNG. Falls back to typed name if canvas unavailable."""
    if HAVE_CANVAS:
        res = st_canvas(stroke_width=2, stroke_color="#111111", background_color="",
                        height=160, width=420, drawing_mode="freedraw",
                        update_streamlit=True, key=key)
        try:
            arr = res.image_data
            if arr is not None and arr[:, :, 3].sum() > 0:
                from PIL import Image
                import io, base64
                buf = io.BytesIO()
                Image.fromarray(arr.astype("uint8")).save(buf, format="PNG")
                return "png:" + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return None
        return None
    name = st.text_input(t(UI["typed_sig"], lang), key=key)
    return ("typed:" + name.strip()) if name.strip() else None

# ---------- app ----------
st.set_page_config(page_title="Olive social questionnaire", page_icon="🫒")
ss = st.session_state
if "step" not in ss:
    ss.step = "lang"; ss.lang = "he"; ss.relation = None; ss.age = "adult"; ss.comp = None
lang = ss.lang
_align = "right" if lang in ("he","ar") else "left"
_dir = "rtl" if lang in ("he","ar") else "ltr"
st.markdown(f"<style>.block-container{{direction:{_dir};text-align:{_align};}} div[data-testid='InputInstructions']{{display:none!important;}}</style>", unsafe_allow_html=True)

owner_id = st.query_params.get("owner", "")
st.title("🫒 " + t(UI["title"], lang))
if not owner_id:
    st.warning(t(UI["no_owner"], lang)); st.caption("Developers: append ?owner=SOMEID to test."); st.stop()
def go(step): ss.step = step; st.rerun()

if ss.step == "lang":
    st.subheader(t(UI["pick_lang"], lang))
    c = st.radio("", ["עברית","العربية","English"], label_visibility="collapsed")
    ss.lang = {"עברית":"he","العربية":"ar","English":"en"}[c]
    if st.button(t(UI["next"], ss.lang)): go("relation")
    st.stop()

if ss.step == "relation":
    st.subheader(t(UI["relation_q"], lang))
    labels = {t(UI["rel_owner"],lang):"owner", t(UI["rel_worker"],lang):"worker",
              t(UI["rel_family"],lang):"family", t(UI["rel_friend"],lang):"friend"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.relation = labels[pick]
        if ss.relation in ("worker","family","friend"): go("age")
        else: ss.age="adult"; ss.comp=None; go("consent")
    st.stop()

if ss.step == "age":
    st.subheader(t(UI["age_q"], lang))
    if ss.relation == "worker":
        labels = {t(UI["age_adult"],lang):"adult", t(UI["age_adol"],lang):"adolescent"}
    else:
        labels = {t(UI["age_adult"],lang):"adult", t(UI["age_adol"],lang):"adolescent", t(UI["age_child"],lang):"child"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.age = labels[pick]
        if ss.relation == "worker": ss.comp="paid"; go("consent")
        elif ss.age == "child": ss.comp="volunteer"; go("consent")
        else: go("comp")
    st.stop()

if ss.step == "comp":
    st.subheader(t(UI["comp_q"], lang))
    labels = {t(UI["comp_paid"],lang):"paid", t(UI["comp_vol"],lang):"volunteer"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.comp = labels[pick]; go("consent")
    st.stop()

if ss.step == "consent":
    var = consent_variant(ss.relation, ss.age, ss.comp)
    cfg = consent_text(var)
    st.subheader(t(UI["consent_h"], lang))
    if ss.relation == "worker": st.info(t(UI["worker_locked"], lang))
    if ss.age == "child": st.info(t(UI["child_locked"], lang))
    sig = None; parental = assent = None; method = None
    if var == "owner":
        st.write(t(UI["owner_prior"], lang))
        ok = st.checkbox(t(UI["confirm_signed"], lang)); method = "prior_signed"
    else:
        st.markdown(t(cfg.get("body", BASE), lang))
        if cfg.get("minor"):
            st.markdown("**" + t(UI["parent_sign"], lang) + "**")
            sig = signature_widget("sig_" + var)
            assent = st.checkbox(t(UI["assent"], lang))
            parental = sig is not None
            ok = (sig is not None) and assent
            method = "parent_signed+assent"
        else:
            st.markdown("**" + t(UI["sign_prompt"], lang) + "**")
            sig = signature_widget("sig_" + var)
            ok = sig is not None
            method = "signed"
    if st.button(t(UI["next"], lang)):
        if not ok:
            st.error(t(UI["must_agree"], lang) if var == "owner" else t(UI["sign_required"], lang)); st.stop()
        ss.consent_variant = var; ss.parental = parental; ss.assent = assent
        ss.signature = sig if isinstance(sig, str) else None
        ss.consent_method = method
        ss.code = make_code(owner_id, ss.relation, ss.age, ss.comp)
        go("questions")
    st.stop()

if ss.step == "questions":
    rel, age, comp = ss.relation, ss.age, ss.comp
    form = form_for(rel, comp, age)
    items = FORMS.get(form, [])
    ans = {}
    st.info(t(UI["typing_help"], lang))
    # One form -> one Submit button at the end; respondents never press Enter per field.
    with st.form("qform", clear_on_submit=False):
        if not items:
            st.warning("No questions loaded for this form (check questions.json).")
        for q in items:
            label = t(q["text"], lang)
            typ = q["type"]
            if typ == "single":
                ans[q["id"]] = st.radio(label, tlist(q["options"], lang), index=None, key=q["id"])
            elif typ == "multi":
                st.markdown(f"**{label}** {t(UI['select_all'], lang)}")
                ans[q["id"]] = [o for o in tlist(q["options"], lang) if st.checkbox(o, key=f"{q['id']}_{o}")]
            elif typ == "scale":
                ans[q["id"]] = st.radio(label, tlist(SCALES.get(q["scale"], {}), lang), index=None, key=q["id"])
            elif typ == "plots_table":
                st.markdown(f"**{label}**")
                cfg = {}
                for c in q["columns"]:
                    clab = t(c["label"], lang)
                    if c["kind"] == "select":
                        cfg[c["key"]] = st.column_config.SelectboxColumn(clab, options=tlist(c["options"], lang))
                    else:
                        cfg[c["key"]] = st.column_config.TextColumn(clab)
                blank = [{c["key"]: None for c in q["columns"]} for _ in range(5)]
                ans[q["id"]] = st.data_editor(blank, column_config=cfg, num_rows="dynamic",
                                              hide_index=True, key=q["id"])
            elif typ == "longtext":
                ans[q["id"]] = st.text_area(label, key=q["id"])
            else:  # number or text -> free text box
                ans[q["id"]] = st.text_input(label, key=q["id"])
            st.divider()
        submitted = st.form_submit_button(t(UI["submit"], lang))
    if submitted:
        row = {"timestamp": dt.datetime.now().isoformat(timespec="seconds"),
               "owner_id": owner_id, "relation": rel, "age_group": age, "compensation": comp,
               "form": form, "language": lang, "consent_variant": ss.consent_variant,
               "parental_consent": ss.parental, "assent": ss.assent, "consent_method": ss.get("consent_method"),
               "signature": ss.get("signature"), "respondent_code": ss.code}
        row.update(ans)
        status, detail = _save_row(row)
        if status == "sheet":
            st.success(t(UI["thanks"], lang)); st.balloons()
            go("done")
        elif status == "rejected":
            st.error("Reached the Google script, but it refused to write the row. "
                     "This is almost always a password mismatch: the SECRET in the Apps Script "
                     "must equal form_token in the app's Secrets (or both be empty). "
                     f"Script replied: {detail}")
        elif status == "csv_error":
            st.error(f"Could not reach the Google script (saved a local copy only). Reason: {detail}")
        else:  # csv_nourl
            st.error("No Sheet is connected: the deployed app has an empty WEBHOOK_URL "
                     "(and no webhook_url in Secrets). Paste your /exec URL and redeploy. "
                     "A local copy was saved, but that is wiped on restart.")
    st.stop()

if ss.step == "done":
    st.success(t(UI["thanks"], lang)); st.stop()
