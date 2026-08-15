/**
 * AfriCloud Institute Gmail relay.
 * Sends website emails as africloudinstitute@gmail.com over HTTPS
 * (Render's free plan blocks SMTP).
 *
 * Setup:
 * 1. Open https://script.google.com while signed in as africloudinstitute@gmail.com
 * 2. New project, paste this file, save
 * 3. Project Settings -> Script properties -> Add:
 *      WEBHOOK_SECRET = (same value as GMAIL_WEBHOOK_SECRET in .env / Render)
 * 4. Deploy -> New deployment -> Type: Web app
 *      Execute as: Me
 *      Who has access: Anyone
 * 5. Copy the web app URL into GMAIL_WEBHOOK_URL
 */
function doPost(e) {
  var output = ContentService.createTextOutput;
  var json = ContentService.MimeType.JSON;

  try {
    var data = JSON.parse(e.postData.contents || "{}");
    var secret = PropertiesService.getScriptProperties().getProperty("WEBHOOK_SECRET") || "";
    if (!secret || data.secret !== secret) {
      return output(JSON.stringify({ ok: false, error: "unauthorized" })).setMimeType(json);
    }
    if (!data.to || !data.subject) {
      return output(JSON.stringify({ ok: false, error: "missing to/subject" })).setMimeType(json);
    }

    GmailApp.sendEmail(data.to, data.subject, data.text || "", {
      htmlBody: data.html || data.text || "",
      name: "AfriCloud Institute",
      replyTo: data.reply_to || Session.getEffectiveUser().getEmail(),
    });

    return output(JSON.stringify({ ok: true })).setMimeType(json);
  } catch (error) {
    return output(JSON.stringify({ ok: false, error: String(error) })).setMimeType(json);
  }
}
