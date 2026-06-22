// Olive questionnaire — response receiver (hardened, self-reporting)
//
// SETUP: open your Google SHEET → Extensions → Apps Script → paste this (replace everything).
// DEPLOY: Deploy → Manage deployments → edit (pencil) the EXISTING web app
//         → Version: New version → Deploy.   (Keeps the same /exec URL.)
// SETTINGS: Execute as: Me   |   Who has access: Anyone
//
// TEST: paste the /exec URL into a browser. You should see {"ok":true,"msg":"Olive webhook is live"}.
//       If you get a Google login page or an HTML error instead, the problem is the
//       deployment/access (fix "Who has access: Anyone" and redeploy), NOT the code.

var SECRET = "Dana@2012";  // must match form_token in the app's Secrets (or "" to disable)

function doGet() {
  return _json({ ok: true, msg: "Olive webhook is live" });
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return _json({ ok: false, error: "No POST body received." });
    }
    var data = JSON.parse(e.postData.contents);

    // password check, then strip it so it is never stored
    var token = data.token;
    delete data.token;
    if (SECRET && token !== SECRET) {
      return _json({ ok: false, error: "unauthorized (token mismatch)" });
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) {
      return _json({ ok: false, error: "No active spreadsheet — this script is not bound to a Sheet. Create it from inside the Sheet via Extensions > Apps Script (not as a standalone project)." });
    }
    var sheet = ss.getSheetByName("responses") || ss.getActiveSheet();

    var headers = [];
    if (sheet.getLastRow() > 0) {
      headers = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 1)).getValues()[0];
      headers = headers.filter(function (h) { return h !== "" && h !== null; });
    }
    Object.keys(data).forEach(function (k) {
      if (headers.indexOf(k) === -1) headers.push(k);
    });
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

    var row = headers.map(function (h) {
      var v = data[h];
      if (v === undefined || v === null) return "";
      return (typeof v === "object") ? JSON.stringify(v) : v;
    });
    sheet.appendRow(row);

    return _json({ ok: true });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
