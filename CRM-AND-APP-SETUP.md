# CRM, guest registration and the future Emergent app

## What works locally now

- Booking enquiries remain separate under **Bookings**. Pending requests do not reserve dates.
- The ROI calculator is anonymous: it asks only for property details and creates no lead on calculation. A dismissible invitation appears after the first result and a permanent proposal button remains below the estimate. Calculator details carry into the tailored-proposal form; only its completed, consented submission creates a lead. The server recalculates the illustrative revenue from the submitted property details.
- **Partner with us**, **Request my tailored proposal**, and **Sell your property** submissions go to the first-party CRM. The proposal button passes property scenario values, not contact details, in the URL. Complete answers, enquiry type, source page and consent version are retained.
- **CRM** provides search, type/stage filters, assignment, notes, follow-up dates in India time and a chronological history. Stages: New, Contacted, Assessment, Proposal sent, Negotiation, Won and Lost. Overdue follow-ups are highlighted. Email/push reminders and automatic notifications are not connected.
- Submissions return a reference. Retries with the same request ID and answers return the same reference. WhatsApp/email drafts remain available after a proposal is saved. Opening a draft does not send it.
- These records live in this app's SQLite database; this change does not connect Zoho or Google Sheets. The older Apps Script receiver is bypassed by the live Python website's property forms.

## Guest names and private ID images

The guest registration section is optional at the enquiry stage. If enabled, the list must include every checking-in guest, including an adult lead guest. Each entry needs a full name, a predefined relationship to the lead guest and an ID image. A minor is marked Under 18 and additionally needs a parent's/legal guardian's name, their selected relationship and a permission declaration. A relationship such as aunt or brother is not automatically treated as legal guardianship.

Supported images: JPEG, PNG and WebP, up to 2 MB each and under 24 MB per request including overhead. PDFs are not supported. Images are decoded, resized, stripped of metadata and encrypted using Fernet before storage in a separate private database table. They never enter the public photo library, public availability API, WhatsApp drafts or email drafts. No document numbers are requested as separate fields.

Admins can view each ID while authenticated, record Pending / Verified by staff / Needs attention, add a review note, or permanently delete that booking's ID images. Viewing IDs is audited. Booking history records the original request and subsequent booking/payment changes. Staff verification is manual; there is no automated identity or parental-consent verification service.

The form's permission checkbox is a declaration, not proof of legally sufficient parental consent. Before business launch, agree an appropriate parent/guardian verification process and the documents you actually need with your operating/legal team. Do not make a particular national ID compulsory without checking the applicable requirements. Official privacy rules reference: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digit

ID images expire after 30 days for unconfirmed/cancelled enquiries. On confirmation, expiry becomes checkout plus 30 days. Expired images are inaccessible immediately and deleted by the running app's background maintenance cycle. Guest names, notes, booking and payment history are retained separately. The 30-day policy is an initial operational default, not a claim about statutory record-retention requirements. Finalise it before launch.

The encryption key is stored in `.data/private-id-key`, or can be supplied as the hosting secret `BRITSMAID_ID_ENCRYPTION_KEY`. Preserve it: losing the key makes encrypted IDs unreadable. Never commit it to GitHub or return it to browsers. `cms/backup.py` includes the local key file when present, the database and uploaded property photos; protect the whole backup with restricted access/encrypted offsite storage. If using an environment key, back it up separately in your secret manager. Restoring an older backup can restore previously deleted IDs, so backups need a matching expiry policy.

## Cookies

Visitors see a first-visit notice with **Use essential only** and **Cookie settings**. They can reopen settings from the footer. Essential session cookies protect submissions/admin login. The cookie preference is stored in this browser's local storage for 180 days. Calculator property values (no contact details) and dismissal of the proposal prompt are kept in tab session storage for up to 30 minutes to support the handoff. Analytics and advertising choices are disabled because no such trackers are installed. Adding Google Analytics later requires a measurement ID, a consent-aware loader and an updated notice; ticking a box today does not activate analytics.

## Connect the Emergent app later

The Emergent app currently has no backend. The practical approach is **one shared backend and database**, used by both interfaces.

1. Export the app source to an account-owned GitHub repository and inspect the generated framework, authentication and data shapes. Keep the current website's property IDs and booking references as the shared identifiers.
2. Decide which service owns the backend. Reuse this Flask backend and extend it with a versioned API, or migrate its business logic/data to the app's chosen backend. Do not run two independent databases and attempt to synchronise them afterwards.
3. For a single website server, SQLite on a persistent volume is supported now. If the app and website need several backend processes/services, migrate to managed PostgreSQL first. Keep property photos in object storage and IDs in a separately restricted encrypted store. That migration is not implemented in this preview.
4. Add authenticated `/api/v1` endpoints for property reads/edits, booking creation/status changes, history, leads and media. Reuse the same validators, overlap checks, confirmations and version numbers used by the website. The website's existing `/admin/api` routes use browser sessions and CSRF; they are not a finished mobile authentication API.
5. Give app staff individual accounts and roles, with short-lived access tokens and revocable refresh tokens. Authorise each endpoint on the server. Public visitors must not be able to edit listings or view booking histories/IDs. Never embed an admin password or permanent backend secret in the distributed mobile app.
6. Point the app at that hosted HTTPS API. The app sends edits/bookings to the server; the website reads the same records. A saved property amendment appears on the next website load. App-created bookings should use the same workflow and audit source as website bookings. Use polling/refetch on screen focus initially; add server events or push notifications only if immediate open-screen updates are needed.
7. Use version checks to reject conflicting edits, idempotency keys for repeated submissions and transactions for confirmation/date blocking. Reuse one calendar worker. Payment status should eventually come from verified payment webhooks, not a mobile client saying a payment succeeded.
8. Test app → website and website → app for property edits, draft/publication state, booking requests, confirmation, cancellation, calendar blocks, history, ID permissions and failed-network retries. Migrate test data separately, take a backup, then connect the existing domain to the hosted website/backend.

No Emergent app code has been changed or connected in this turn. The versioned app API, app authentication and any PostgreSQL migration are the joint integration phase after the app source is available.

## Local verification

`python tests/test_crm_guests.py` checks lead capture, consent, server calculations, pipeline edit conflicts, all owner form types, encrypted ID access, minor/guardian validation, invalid-image rejection and expiry.

`node tests/verify_crm_guests.cjs` uses an isolated local database and fabricated ID images for the complete browser flow and mobile/desktop layouts. No real messages, ID documents, CRM accounts or cloud writes are used.

CRM refreshes every 20 seconds while visible and immediately when the window regains focus. Public GitHub showcase records use browser-local storage with a 24-hour expiry so demo leads can appear across tabs in the same browser. This is simulated, never the real database; use fictional details and Reset demo to clear them.
