"""
Olive LCSA — Social questionnaire platform
==========================================
Plain, multilingual (HE / AR / EN). No AI, no LCI.

TWO INDEPENDENT AXES
--------------------
  relation     : owner / worker / family / friend
  compensation : paid / volunteer
Constraints:
  worker        -> paid (locked)
  family/friend -> paid OR volunteer (their choice)
  child (8-13)  -> volunteer (locked)        # "kids" rule
  owner         -> no compensation axis

AGE (family/friend only): adult / adolescent (14-17) / child (8-13)
  -> routes the CONSENT variant and the QUESTIONNAIRE version.

Per-owner link:  https://<app>/?owner=KMAHARAL   (everyone on that link -> same owner_id)

CONSENT: six variants. The wording below is PLACEHOLDER — replace each slot with
the approved Appendix-7 trilingual text from the ethics package.
"""

import csv, json, os, random, string
import datetime as dt
import streamlit as st


# PASTE your Apps Script web-app URL here (or set webhook_url in the Secrets box).
WEBHOOK_URL = ""

def _webhook_url():
    try:
        if "webhook_url" in st.secrets:
            return st.secrets["webhook_url"]
    except Exception:
        pass
    return WEBHOOK_URL

# Optional shared password. Best kept in the Secrets box:  form_token = "..."
FORM_TOKEN = ""
def _form_token():
    try:
        if "form_token" in st.secrets:
            return st.secrets["form_token"]
    except Exception:
        pass
    return FORM_TOKEN

def _save_row(row: dict):
    import urllib.request
    url = _webhook_url()
    if url:
        try:
            payload = dict(row)
            tok = _form_token()
            if tok:
                payload["token"] = tok
            req = urllib.request.Request(
                url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=15)
            return
        except Exception as e:
            st.session_state["_save_warn"] = str(e)
    # local-only fallback (works when running on your own computer)
    path = os.path.join(os.path.dirname(__file__), "responses.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(list(row.keys()))
        w.writerow([json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for v in row.values()])


def t(d, lang):
    return d.get(lang) or d.get("he") or d.get("en") or ""

def OPT(he, ar, en):
    return {"he": he, "ar": ar, "en": en}


# =====================================================================
UI = {
    "title": OPT("שאלון — גידול זיתים בישראל", "استبيان — زراعة الزيتون في إسرائيل", "Questionnaire — Olive cultivation in Israel"),
    "pick_lang": OPT("בחרו שפה", "اختر اللغة", "Choose a language"),
    "no_owner": OPT("קישור לא תקין — אנא השתמשו בקישור האישי שקיבלתם.",
                    "رابط غير صالح — يرجى استخدام الرابط الشخصي الذي تلقيته.",
                    "Invalid link — please use the personal link you were given."),
    "next": OPT("המשך", "متابعة", "Continue"),
    "submit": OPT("שליחה", "إرسال", "Submit"),
    "relation_q": OPT("מה הקשר שלך לחווה?", "ما علاقتك بالمزرعة؟", "What is your relation to the farm?"),
    "rel_owner": OPT("בעל/ת החווה", "صاحب/ة المزرعة", "Owner"),
    "rel_worker": OPT("עובד/ת שכיר/ה (לא מהמשפחה)", "عامل/ة مأجور (ليس من العائلة)", "Hired worker (not family)"),
    "rel_family": OPT("בן/בת משפחה", "فرد من العائلة", "Family member"),
    "rel_friend": OPT("חבר/ה או בן/בת קהילה", "صديق/ة أو فرد من المجتمع", "Friend / community member"),
    "age_q": OPT("מהי קבוצת הגיל?", "ما هي الفئة العمرية؟", "Age group?"),
    "age_adult": OPT("מבוגר/ת (18+)", "بالغ (18+)", "Adult (18+)"),
    "age_adol": OPT("נער/ה (14–17)", "مراهق (14–17)", "Adolescent (14–17)"),
    "age_child": OPT("ילד/ה (8–13)", "طفل (8–13)", "Child (8–13)"),
    "comp_q": OPT("האם העבודה בשכר או בהתנדבות?", "هل العمل بأجر أم تطوعي؟", "Is the work paid or voluntary?"),
    "comp_paid": OPT("בשכר", "بأجر", "Paid"),
    "comp_vol": OPT("בהתנדבות", "تطوعي", "Voluntary"),
    "comp_worker_locked": OPT("כעובד/ת בשכר — ההשתתפות מתייחסת לעבודה בשכר.",
                              "كعامل بأجر — تتعلق المشاركة بعمل مأجور.",
                              "As a paid worker, this refers to paid employment."),
    "comp_child_locked": OPT("בגיל זה ההשתתפות היא בהתנדבות בלבד.",
                             "في هذا العمر تكون المشاركة تطوعية فقط.",
                             "At this age, participation is voluntary only."),
    "consent_h": OPT("הסכמה מדעת", "الموافقة المستنيرة", "Informed consent"),
    "agree": OPT("קראתי ואני מסכים/ה להשתתף", "قرأت وأوافق على المشاركة", "I have read this and agree to take part"),
    "parental": OPT("אני ההורה/אפוטרופוס ונותן/ת אישור להשתתפות",
                    "أنا الوالد/الوصي وأمنح الإذن بالمشاركة",
                    "I am the parent/guardian and give permission to take part"),
    "assent_adol": OPT("אני מסכים/ה להשתתף", "أوافق على المشاركة", "I agree to take part"),
    "assent_child": OPT("אני רוצה לענות על השאלות", "أريد الإجابة على الأسئلة", "I want to answer the questions"),
    "must_agree": OPT("יש לאשר את ההסכמה כדי להמשיך.", "يجب الموافقة للمتابعة.", "Please confirm consent to continue."),
    "name_q": OPT("פרטיות", "الخصوصية", "Privacy"),
    "name_named": OPT("אפשר להשתמש בשמי", "يمكن استخدام اسمي", "You may use my name"),
    "name_anon": OPT("אני מעדיף/ה להישאר אנונימי/ת", "أفضّل أن أبقى مجهول الهوية", "I prefer to stay anonymous"),
    "name_field": OPT("שם (לא חובה)", "الاسم (اختياري)", "Name (optional)"),
    "select_all": OPT("(ניתן לבחור יותר מאחד)", "(يمكن اختيار أكثر من واحد)", "(select all that apply)"),
    "thanks": OPT("תודה רבה! התשובות נשמרו.", "شكراً جزيلاً! تم حفظ إجاباتك.", "Thank you! Your answers were saved."),
}

# ---- CONSENT TEXT (PLACEHOLDER — replace each with approved Appendix-7 wording) ----
EMPLOYER_FIREWALL = OPT(
    " המעסיק שלך אינו יכול לראות את תשובותיך בשום שלב.",
    " لا يمكن لصاحب العمل رؤية إجاباتك في أي مرحلة.",
    " Your employer cannot see your answers at any stage.")
BASE = OPT(
    "ההשתתפות התנדבותית; ניתן להפסיק בכל שלב. התשובות משמשות למחקר בלבד ונשמרות באופן מאובטח.",
    "المشاركة طوعية ويمكنك التوقف في أي وقت. تُستخدم الإجابات للبحث فقط وتُحفظ بشكل آمن.",
    "Participation is voluntary and you may stop at any time. Answers are used for research only and stored securely.")
CONSENT = {
    "owner":  {"body": BASE},
    "worker": {"body": OPT(BASE["he"] + EMPLOYER_FIREWALL["he"], BASE["ar"] + EMPLOYER_FIREWALL["ar"], BASE["en"] + EMPLOYER_FIREWALL["en"])},
    "family": {"body": BASE},
    "friend": {"body": BASE},
    "adolescent": {"body": BASE, "minor": True, "assent": UI["assent_adol"]},
    "child": {"body": OPT("נשאל אותך כמה שאלות על הזיתים והמשפחה. אפשר להפסיק מתי שרוצים.",
                          "سنسألك بعض الأسئلة عن الزيتون والعائلة. يمكنك التوقف متى أردت.",
                          "We will ask you a few questions about olives and family. You can stop whenever you want."),
              "minor": True, "assent": UI["assent_child"]},
}
def consent_variant(rel, age, comp):
    if age == "child": return "child"
    if age == "adolescent": return "adolescent"
    if comp == "paid": return "worker"   # paid adult -> worker consent (employer firewall)
    return rel                           # unpaid adult -> owner/family/friend

def form_for(rel, comp):
    """Which questionnaire to show: paid -> worker form; otherwise by relation."""
    return "worker" if comp == "paid" else rel

# Respondent code: meaningful to you, cryptic + non-identifying to others.
#   <FARM>-<relation><age><pay>-<random>     e.g.  KMAHA-FTV-7Q3K
#   relation O/W/F/C  | age A/T/K (adult/teen/kid) | pay P/V/X
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no O/0/I/1/L (avoids misreads)
_REL = {"owner": "O", "worker": "W", "family": "F", "friend": "C"}
_AGE = {"adult": "A", "adolescent": "T", "child": "K"}
_PAY = {"paid": "P", "volunteer": "V", None: "X"}
def make_code(owner, rel, age, comp):
    farm = "".join(ch for ch in owner.upper() if ch.isalnum())[:5] or "FARM"
    rand = "".join(random.choices(ALPHABET, k=4))
    return f"{farm}-{_REL[rel]}{_AGE[age]}{_PAY.get(comp,'X')}-{rand}"


# =====================================================================
SCALES = {
    "agree5": OPT(["מסכים/ה מאוד","מסכים/ה","ניטרלי/ת","לא מסכים/ה","כלל לא מסכים/ה"],
                  ["أوافق بشدة","أوافق","محايد","لا أوافق","لا أوافق إطلاقاً"],
                  ["Strongly agree","Agree","Neutral","Disagree","Strongly disagree"]),
    "agree4_kid": OPT(["מאוד","קצת","לא ממש","בכלל לא"], ["كثيراً","قليلاً","ليس حقاً","أبداً"],
                      ["A lot","A bit","Not really","No"]),
    "freq5": OPT(["תמיד","לעיתים קרובות","לפעמים","לעיתים רחוקות","אף פעם / כמעט אף פעם"],
                 ["دائماً","غالباً","أحياناً","نادراً","أبداً / نادراً جداً"],
                 ["Always","Often","Sometimes","Seldom","Never / hardly ever"]),
    "degree5": OPT(["במידה רבה מאוד","במידה רבה","במידה מסוימת","במידה מועטה","במידה מועטה מאוד"],
                   ["إلى حد كبير جداً","إلى حد كبير","إلى حد ما","إلى حد قليل","إلى حد قليل جداً"],
                   ["To a very large extent","To a large extent","Somewhat","To a small extent","To a very small extent"]),
    "sat4": OPT(["מרוצה מאוד","מרוצה","לא מרוצה","לא מרוצה כלל"],
                ["راضٍ جداً","راضٍ","غير راضٍ","غير راضٍ إطلاقاً"],
                ["Very satisfied","Satisfied","Unsatisfied","Very unsatisfied"]),
    "health5": OPT(["מצוין","טוב מאוד","טוב","סביר","גרוע"], ["ممتاز","جيد جداً","جيد","مقبول","سيئ"],
                   ["Excellent","Very good","Good","Fair","Poor"]),
}

# =====================================================================
# QUESTION BANK
#   rel  : which relations see it
#   age  : which age groups (default adult+adolescent; add "child" to show to kids)
#   comp : if set ("paid"/"volunteer"), only that compensation sees it
# Child sees ONLY items whose age includes "child" (heritage-only), on the 4-pt kid scale.
# =====================================================================
ALL = ["owner", "worker", "family", "friend"]
QUESTIONS = [
 {"section": OPT("רקע","معلومات عامة","Background"), "items":[
   {"id":"D_age","type":"single","form":ALL,"text":OPT("גיל","العمر","Age"),
    "options":OPT(["18–29","30–44","45–59","60+"],["18–29","30–44","45–59","60+"],["18–29","30–44","45–59","60+"])},
   {"id":"D_gender","type":"single","form":ALL,"text":OPT("מין","الجنس","Gender"),
    "options":OPT(["נקבה","זכר","אחר","מעדיף/ה לא לומר"],["أنثى","ذكر","آخر","أفضّل عدم الإجابة"],["Female","Male","Other","Prefer not to say"])},
   {"id":"D_minority","type":"single","form":ALL,"text":OPT("האם את/ה רואה את עצמך כחלק מקהילת מיעוט?","هل تعتبر نفسك جزءاً من مجتمع أقلية؟","Do you consider yourself part of a minority community?"),
    "options":OPT(["כן","לא","מעדיף/ה לא לומר"],["نعم","لا","أفضّل عدم الإجابة"],["Yes","No","Prefer not to say"])},
 ]},
 {"section": OPT("מדוע את/ה מגדל/ת זיתים?","لماذا تزرع الزيتون؟","Why do you grow olives?"), "items":[
   {"id":"M_owner","type":"multi","form":["owner"],"text":OPT("בחרו כל מה שמתאים","اختر كل ما ينطبق","Select all that apply"),
    "options":OPT(
     ["לרווח / תשואה כלכלית","כהכנסה משלימה","המשך חווה משפחתית שעברה בירושה","כדי להעביר את החווה לילדיי",
      "לעבוד יחד עם בני המשפחה","הזיתים הם חלק מהמורשת התרבותית שלי","משמעות דתית או רוחנית","קשר אישי לאדמה הזו",
      "לשמור על הבעלות / מעמד הקרקע","לשמר את נוף הזיתים של האזור","לצריכה עצמית של המשפחה","גאווה באיכות השמן",
      "להיות עצמאי/ת","אורח חיים כפרי / עבודה בחוץ","שייכות לקהילת מגדלים","אחריות סביבתית","קרקע כהשקעה",
      "אידיאל של עבודת האדמה","לא להשאיר אדמה מובטלת","אחר"], [],
     ["For profit / economic return","Supplementary income","Continuing an inherited family farm","To pass the farm to my children",
      "To work together with family","Olives are part of my cultural heritage","Religious or spiritual significance","Personal connection to this land",
      "To keep ownership / status of the land","To preserve the region's olive landscape","For my family's own consumption","Pride in high-quality oil",
      "To be self-employed","Rural lifestyle / outdoors","Belonging to a growers' community","Environmental stewardship","Land as investment",
      "The ideal of working the land","Not letting farmland sit idle","Other"])},
   {"id":"M_other","type":"multi","form":["worker","family","friend"],"text":OPT("בחרו כל מה שמתאים","اختر كل ما ينطبق","Select all that apply"),
    "options":OPT(
     ["אני זקוק/ה להכנסה — עבודה עיקרית","הכנסה משלימה","אין תעסוקה חלופית באזור","זו חווה של משפחתי / קרובים",
      "מסורת משפחתית","הזיתים הם חלק מהמורשת שלי","קשר לאדמה ולעבודה בחוץ","מיומנות / מומחיות בעבודת הזיתים",
      "משמעות דתית או רוחנית","אופי גמיש / עונתי","עבודה לצד משפחה או חברים","אני נהנה/ית מהעבודה","אחר"], [],
     ["I need the income — main job","Supplementary income","No other local employment","Family / relatives' farm",
      "Family tradition","Olives are part of my heritage","Connection to land and outdoor work","Skills / expertise in olive work",
      "Religious or spiritual significance","Flexible / seasonal work","Working alongside family or friends","I enjoy this work","Other"])},
 ]},
 {"section": OPT("מורשת וזהות","التراث والهوية","Heritage & identity"), "items":[
   {"id":"H_significance","type":"single","form":ALL,"age":["adult","adolescent","child"],
    "text":OPT("האם הזיתים בעלי משמעות תרבותית / מורשת עבורך?","هل للزيتون أهمية ثقافية / تراثية بالنسبة لك؟","Do olives have cultural / heritage significance for you?"),
    "options":OPT(["משמעות רבה","משמעות מסוימת","לא במיוחד","לא"],["أهمية كبيرة","بعض الأهمية","ليس بشكل خاص","لا"],["Strong significance","Some significance","Not particularly","No"])},
   {"id":"H_part_of_who","type":"scale","scale":"agree5","form":ALL,"age":["adult","adolescent","child"],
    "text":OPT("הזיתים הם חלק ממי שאני.","الزيتون جزء من هويتي.","Olives are part of who I am.")},
   {"id":"H_continuity","type":"scale","scale":"agree5","form":["owner","family"],"age":["adult","adolescent","child"],
    "text":OPT("חשוב לי שהמסורת הזו תימשך בדור הבא.","من المهم أن يستمر هذا التقليد للجيل القادم.","It matters to me that this tradition continues.")},
   {"id":"H_landscape","type":"scale","scale":"agree5","form":ALL,"age":["adult","adolescent","child"],
    "text":OPT("מטעי הזיתים הם חלק חשוב מהנוף.","بساتين الزيتون جزء مهم من المشهد.","Olive groves are an important part of the landscape.")},
 ]},
 {"section": OPT("מעורבות בעבודה","المشاركة في العمل","Involvement"), "items":[
   {"id":"I_hands_on","type":"scale","scale":"freq5","form":["owner","family"],
    "text":OPT("באיזו תדירות את/ה עוסק/ת בעצמך בעבודה הפיזית במטע?","كم مرة تقوم بنفسك بالعمل البدني في البستان؟","How often do you personally do the physical work?")},
   {"id":"I_season","type":"single","form":["worker","family","friend"],
    "text":OPT("מתי את/ה עובד/ת במטע?","متى تعمل في البستان؟","When do you work in the grove?"),
    "options":OPT(["כל השנה","בעיקר במסיק","מדי פעם","רק באירועים מיוחדים"],["طوال السنة","في الحصاد أساساً","أحياناً","في مناسبات خاصة فقط"],["Year-round","Mainly at harvest","Occasionally","Only special occasions"])},
 ]},
 {"section": OPT("עבודה ותעסוקה","العمل والتوظيف","Work & employment"), "items":[
   {"id":"S_employment","type":"single","form":["worker"],
    "text":OPT("כיצד את/ה מועסק/ת?","كيف يتم توظيفك؟","How are you employed?"),
    "options":OPT(["ישירות ע\"י בעל החווה","דרך קבלן","בן/בת משפחה בשכר","אחר"],["مباشرة من صاحب المزرعة","عبر مقاول","فرد عائلة بأجر","آخر"],["Directly by the owner","Through a contractor","Paid family member","Other"])},
   {"id":"S_fair_pay","type":"scale","scale":"agree5","form":["worker"],
    "text":OPT("השכר שאני מקבל/ת הוגן ועונה על צרכיי.","الأجر الذي أتقاضاه عادل ويلبي احتياجاتي.","The pay I receive is fair and meets my needs.")},
   {"id":"S_difficulty","type":"single","form":["worker","family","friend"],
    "text":OPT("הקושי הפיזי בעבודת המסיק","الصعوبة الجسدية في الحصاد","Physical difficulty of harvest work"),
    "options":OPT(["קל","בינוני","כבד","כבד מאוד"],["خفيف","متوسط","ثقيل","ثقيل جداً"],["Light","Moderate","Heavy","Very heavy"])},
   {"id":"S_injuries","type":"single","form":ALL,
    "text":OPT("פציעות בעבודה בשנה האחרונה","إصابات العمل في السنة الماضية","Work-related injuries in the last year"),
    "options":OPT(["אין","אחת","שתיים","שלוש או יותר"],["لا شيء","واحدة","اثنتان","ثلاث أو أكثر"],["None","One","Two","Three or more"])},
 ]},
 {"section": OPT("שביעות רצון ועתיד","الرضا والمستقبل","Satisfaction & future"), "items":[
   {"id":"S_satisfaction","type":"scale","scale":"sat4","form":ALL,
    "text":OPT("עד כמה את/ה מרוצה מהעיסוק בזיתים?","ما مدى رضاك عن العمل في الزيتون؟","How satisfied are you with working in olives?")},
   {"id":"S_health","type":"scale","scale":"health5","form":ALL,
    "text":OPT("באופן כללי, מצב בריאותך:","بشكل عام، حالتك الصحية:","In general, your health is:")},
   {"id":"S_future","type":"single","form":ALL,
    "text":OPT("האם בכוונתך להמשיך לעסוק בזיתים בעתיד?","هل تنوي الاستمرار في العمل بالزيتون مستقبلاً؟","Do you intend to continue in the future?"),
    "options":OPT(["בהחלט כן","כנראה כן","לא בטוח/ה","כנראה לא","בהחלט לא"],["بالتأكيد نعم","على الأرجح نعم","غير متأكد","على الأرجح لا","بالتأكيد لا"],["Definitely yes","Probably yes","Unsure","Probably no","Definitely no"])},
 ]},
 # VALIDATED BATTERIES (COPSOQ III / FSI / Place Attachment) — scales wired; paste approved items here.
]


# =====================================================================
st.set_page_config(page_title="Olive social questionnaire", page_icon="🫒")
ss = st.session_state
if "step" not in ss:
    ss.step = "lang"; ss.lang = "he"; ss.relation = None; ss.age = "adult"; ss.comp = None

lang = ss.lang
align = "right" if lang in ("he", "ar") else "left"
direction = "rtl" if lang in ("he", "ar") else "ltr"
st.markdown(f"<style>.block-container{{direction:{direction};text-align:{align};}}</style>", unsafe_allow_html=True)

owner_id = st.query_params.get("owner", "")
st.title("🫒 " + t(UI["title"], lang))
if not owner_id:
    st.warning(t(UI["no_owner"], lang))
    st.caption("Developers: append ?owner=SOMEID to the URL to test.")
    st.stop()

def go(step): ss.step = step; st.rerun()

# ---- language ----
if ss.step == "lang":
    st.subheader(t(UI["pick_lang"], lang))
    c = st.radio("", ["עברית", "العربية", "English"], label_visibility="collapsed")
    ss.lang = {"עברית":"he","العربية":"ar","English":"en"}[c]
    if st.button(t(UI["next"], ss.lang)): go("relation")
    st.stop()

# ---- relation ----
if ss.step == "relation":
    st.subheader(t(UI["relation_q"], lang))
    labels = {t(UI["rel_owner"],lang):"owner", t(UI["rel_worker"],lang):"worker",
              t(UI["rel_family"],lang):"family", t(UI["rel_friend"],lang):"friend"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.relation = labels[pick]
        if ss.relation in ("worker", "family", "friend"):
            go("age")
        else:  # owner
            ss.age = "adult"; ss.comp = None; go("consent")
    st.stop()

# ---- age (family/friend) ----
if ss.step == "age":
    st.subheader(t(UI["age_q"], lang))
    if ss.relation == "worker":
        labels = {t(UI["age_adult"],lang):"adult", t(UI["age_adol"],lang):"adolescent"}  # paid -> no child
    else:
        labels = {t(UI["age_adult"],lang):"adult", t(UI["age_adol"],lang):"adolescent", t(UI["age_child"],lang):"child"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.age = labels[pick]
        if ss.relation == "worker":
            ss.comp = "paid"; go("consent")        # hired worker: paid-locked
        elif ss.age == "child":
            ss.comp = "volunteer"; go("consent")   # kids: volunteer-locked
        else:
            go("comp")
    st.stop()

# ---- compensation (family/friend adult+adolescent) ----
if ss.step == "comp":
    st.subheader(t(UI["comp_q"], lang))
    labels = {t(UI["comp_paid"],lang):"paid", t(UI["comp_vol"],lang):"volunteer"}
    pick = st.radio("", list(labels.keys()), label_visibility="collapsed")
    if st.button(t(UI["next"], lang)):
        ss.comp = labels[pick]; go("consent")
    st.stop()

# ---- consent (variant by relation+age) ----
if ss.step == "consent":
    var = consent_variant(ss.relation, ss.age, ss.comp)
    cfg = CONSENT[var]
    st.subheader(t(UI["consent_h"], lang))
    if ss.relation == "worker":
        st.info(t(UI["comp_worker_locked"], lang))
    if ss.age == "child":
        st.info(t(UI["comp_child_locked"], lang))
    st.write(t(cfg["body"], lang))
    if cfg.get("minor"):
        parental = st.checkbox(t(UI["parental"], lang))
        assent = st.checkbox(t(cfg["assent"], lang))
        ok = parental and assent
    else:
        ok = st.checkbox(t(UI["agree"], lang))
        parental = None; assent = None
    if st.button(t(UI["next"], lang)):
        if not ok:
            st.error(t(UI["must_agree"], lang)); st.stop()
        ss.consent_variant = var; ss.parental = parental; ss.assent = assent
        ss.code = make_code(owner_id, ss.relation, ss.age, ss.comp)
        go("questions")
    st.stop()

# ---- questions ----
def show(q, rel, age, comp):
    if rel not in q["rel"]: return False
    if age not in q.get("age", ["adult", "adolescent"]): return False
    if "comp" in q and comp != q["comp"]: return False
    return True

if ss.step == "questions":
    rel, age, comp = ss.relation, ss.age, ss.comp
    form = form_for(rel, comp)
    ans = {}
    for block in QUESTIONS:
        items = [q for q in block["items"] if show(q, form, age)]
        if not items: continue
        st.markdown(f"### {t(block['section'], lang)}")
        for q in items:
            label = t(q["text"], lang)
            if q["type"] == "single":
                ans[q["id"]] = st.radio(label, t(q["options"], lang), index=None, key=q["id"])
            elif q["type"] == "multi":
                st.markdown(f"**{label}** {t(UI['select_all'], lang)}")
                ans[q["id"]] = [o for o in t(q["options"], lang) if st.checkbox(o, key=f"{q['id']}_{o}")]
            elif q["type"] == "scale":
                sc = "agree4_kid" if age == "child" else q["scale"]   # kid 4-pt scale
                ans[q["id"]] = st.radio(label, t(SCALES[sc], lang), index=None, key=q["id"])
        st.divider()
    if st.button(t(UI["submit"], lang)):
        row = {"timestamp": dt.datetime.now().isoformat(timespec="seconds"),
               "owner_id": owner_id, "relation": rel, "age_group": age, "compensation": comp, "form": form,
               "language": lang, "consent_variant": ss.consent_variant,
               "parental_consent": ss.parental, "assent": ss.assent,
               "respondent_code": ss.code}
        row.update(ans)
        _save_row(row)
        st.success(t(UI["thanks"], lang)); st.balloons()
        if "_save_warn" in ss:
            st.caption(f"(Saved to local CSV; Sheets note: {ss['_save_warn']})")
        go("done")
    st.stop()

if ss.step == "done":
    st.success(t(UI["thanks"], lang)); st.stop()
