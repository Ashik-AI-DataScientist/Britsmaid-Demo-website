# Google Sheets enquiry capture

## Current status
The user has deployed the Apps Script receiver and supplied its /exec URL. That URL is now configured in assets/config.js. Local receiver and bridge tests passed. The updated website files still need to be uploaded to GitHub Pages, and a live submission must be checked against the Sheet before confirming end-to-end delivery.

Deployment URL: https://script.google.com/macros/s/AKfycbyF7wQraHbQwN1kogd8yhU4vGBB9SzGuC9o0JBkRpMhkKk_amn4DEFKJW7qPdW6_Ji4/exec

- Spreadsheet: https://docs.google.com/spreadsheets/d/15PSGnAJaCbfbyKWLcd6m_wSe9X-q39_Am5n7bkn3fMw/edit
- Prepared project: https://script.google.com/u/0/home/projects/13KiBfr4WBCWB2fgpyF-CIZWzxMLxtOmXtUjR4XYc1WCr6bYxv9ZFOaTl/edit
- Website: https://ashik-ai-datascientist.github.io/Britsmaid-Demo-website/
- Alert recipient: ashikmasharaf97@gmail.com

## Publish and verify
1. Upload the updated enquiry pages and assets/config.js, assets/sheets.js, assets/enquiries.js to the GitHub repository. This local folder is not a Git checkout; no push has been performed.
2. On the published GitHub Pages website, submit a clearly labelled test enquiry using each form.
3. Verify its on-screen reference matches a row in Website enquiries and check the email alert.
4. Test from the hosted HTTPS website, not a file opened from your computer: the receiver accepts the configured GitHub origin and repository path.
5. If you change Code.gs or Bridge.html, use Deploy > Manage deployments > Edit > New version > Deploy, retaining the same /exec URL.

The receiver creates a new Website enquiries tab automatically on the first valid submission (or run setup from the editor). Existing tabs are preserved. It stores every answer, form type, source page, client consent time, server received time, reference and full JSON including the calculator scenario. It provides Stage, Team notes and Follow up columns for manual tracking. These are not automatic reminders or a full CRM.

## How delivery works
The site embeds a tiny Apps Script HTML-service bridge. The bridge calls google.script.run, waits for a durable Sheet save and sends a verified receipt back. This avoids cross-origin fetch restrictions and does not use an opaque no-cors request as evidence of success. Contact details stay out of the bridge URL. Google credentials stay server-side.

Validation checks both forms, contact method, consent, payload limits, numeric bounds and a hidden spam field. A lock and submission reference prevent duplicate rows. Spreadsheet formulas are escaped. Email alert failure does not discard an already saved enquiry; inspect Alert status in the Sheet. Alerts contain a reference and private Sheet link rather than the visitor's answers. Google email/service quotas apply: https://developers.google.com/apps-script/guides/services/quotas

This is a simple demo backend with a public write receiver. Origin/nonce checks protect browser message routing, not against determined bots; there is a 100-new-submissions-per-hour global cache ceiling, but no CAPTCHA or durable per-person abuse control. For the production site add server-side bot verification/rate limiting or a managed form service. Keep sheet access restricted and review the site's existing draft privacy policy before a public business launch.

Booking buttons continue to prepare WhatsApp/email messages with villa, dates, guests and notes. They do not save bookings to Sheets or confirm reservations; visitors press Send in their app. The two owner enquiry forms use automatic Sheets delivery once configured, and retain direct-contact fallbacks on failure.

When moving to britsmaid.in, add its exact HTTPS origin to SETTINGS.origins, adjust pathPrefix for your new site path, and update the Apps Script deployment version. Frontend files contain no account secrets. Never publish your Sheet to the web.

Reference: https://developers.google.com/apps-script/guides/html/communication and https://developers.google.com/apps-script/guides/web
