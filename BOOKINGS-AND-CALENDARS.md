# Feedback, bookings and OTA calendars

These features run in the Python app, including the local preview. They cannot run on GitHub Pages. Nothing has been deployed, no real OTA feeds have been connected, and no payment provider has been selected.

## Feedback

Visitors use **Leave feedback** in the footer or on a property page. They can identify their feedback as a stay experience or website/service feedback. Name and feedback are required; property and private reply email are optional. Storage consent is required. Separate publication permission is optional and unchecked.

Visitors choose a required whole-number rating from 1 to 5, with no preselected score. The homepage has a prominent feedback invitation; each property has a review link near its title and in its guest-review section. The property is preselected when following its link.

Every submission enters **Reviews** as awaiting review. Admins can read, edit and publish with permission, or keep it private. **Unpublish review** removes a published review from the public pages while retaining it in the studio. Contact email and the original submission are retained privately. Each property shows published stay reviews, their scores, a one-decimal average out of 5 and the rated-review count on its cards and detail page. Only published, permissioned stay ratings for that property count; general website/service feedback and unrated older reviews do not affect its average. Unpublishing removes a review from public display and the average on the next page load. No ratings are invented for older reviews. These are moderated testimonials, not verified-booking ratings.

## Booking enquiry and confirmation

1. The visitor selects dates, guest count, name, phone or email, notes and consent on a property page.
2. Either enquiry button first saves the request in the website database and returns a reference. It then offers WhatsApp and email links containing all those details. The visitor must press Send in the chosen app; opening the link alone does not send a message. No automated email or WhatsApp notification is configured.
3. The request appears under **Bookings** with status Requested. It does not reserve dates. Known blocked nights and over-capacity requests are rejected.
4. Review the OTA calendars directly before confirming. Confirming requires an explicit availability acknowledgement. Overlaps with another direct confirmation or an imported enabled feed cannot be confirmed. Confirmed dates appear unavailable on the website and in its iCal export. Check-out is exclusive, so a new guest can arrive on that date.
5. Enter the agreed INR amount and, when available, paste a payment provider's HTTPS payment link. The payment link is an optional placeholder field for now: it does not create a link, charge a card or verify payment. Do not enter invented payment links on the live system.
6. Save, then use **Prepare WhatsApp** or **Prepare email** to send the confirmation/payment instructions. The generated message reflects the saved booking. A known conflict prevents preparation of a confirmation message.
7. After verifying funds in the provider or bank, mark Paid manually. Cancelling/declining releases only the direct booking block; any overlapping OTA block remains. Refund status is a manual record and does not issue a refund.

Later provider integration needs hosted credentials, order creation, signed webhook verification, idempotent payment processing and reconciliation. No provider secrets belong in browser code. The current build deliberately makes no automatic payment claims.

## Connect each property's calendars

1. Host the app with HTTPS and persistent storage; enter its final domain under **Website & SEO**. Local export URLs cannot be reached by an OTA.
2. Obtain the private iCal export URL for each property's listing on each OTA. In **Calendars → Add OTA calendar**, choose the matching property, give the feed a name and paste that URL. Never use another property's calendar or the public listing URL.
3. Save and click **Sync now**. Check last successful import and the blocked-night count. The app fetches enabled feeds every 15 minutes while `python app.py` is running. The Docker entry point starts this worker. If using a different WSGI entry point, start `operations.start_calendar_worker(app)` explicitly after loading the Flask application, or arrange a scheduler calling its `britsmaid_operations` extension's `sync_one` function for each enabled feed ID in an application context. Do not run multiple instances with SQLite.
4. Copy the property's website iCal export and import it into the matching listing on each OTA. Treat the tokenised link as private. It contains generic Reserved date blocks only, without guest names, contact details or notes.
5. Website exports include **direct confirmed bookings only**, avoiding re-export loops. Keep OTA-to-OTA imports connected separately so bookings on one OTA reach the others. This is periodic date exchange, not a full channel manager.
6. Test with a deliberate blocked-date example on each platform before accepting direct bookings. Cancel it afterwards and verify that all platforms release the right nights.

Airbnb says its calendar refreshes automatically every three hours: https://www.airbnb.com/help/article/99. Other platforms have their own schedules. The website's 15-minute polling cannot make an OTA publish/import faster. Concurrent reservations and delayed updates remain possible; verify dates manually before confirming or sending payment instructions. iCal does not distribute rates, payment records or complete guest details.

Imports cover approximately the next two years, handle date-based events and bounded recurrence, and respect exclusive checkout dates. Failed imports retain the last successful blocks and display a review warning. Disabling a feed removes its blocks from website availability; do that only when safe to release those dates. Calendar links must be direct HTTPS URLs from enabled trusted providers; redirects are rejected. A developer can add a trusted provider's exact domain with `ICAL_ALLOWED_HOSTS`. Never add arbitrary user-supplied domains.

## Storage and launch

Booking records, consent versions, private feedback, calendar URLs, date blocks and status history are stored in the persistent SQLite database. Images remain separate files. The admin content-only JSON export does not include booking/calendar records. Use `python cms/backup.py` for a full database and uploaded-photo backup and keep an offsite protected copy. These records and private feed URLs must never be committed to GitHub.

Public submissions use same-origin CSRF protection, an essential session cookie, a honeypot, an hourly per-client limit and idempotency references to avoid duplicate retries. This is an initial spam control; monitor real traffic after hosting. Agree a retention/deletion process for personal data before launch. The existing legal pages remain drafts needing review against the actual business operation.

These new guest submissions are stored in this app's database. They do not automatically write to Google Sheets or Zoho. The older owner-enquiry Apps Script delivery issue remains separate. No Google Analytics tracker has been added by this work.

Verification: `python tests/test_operations.py` and `node tests/verify_operations.cjs` use isolated test data. They do not send real messages, fetch real OTA calendars or take payments.
