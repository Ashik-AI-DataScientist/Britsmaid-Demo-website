# Britsmaid enquiries and Zoho Bigin

## Current implementation

Two separate questionnaires are available: management on `partner-with-us.html` and sale on `sell-your-property.html`. Both require name, location, the core proposal details, consent and a mobile number or valid email. Preferred contact method must match the provided contact route. Management also captures rooms, furnishings, current status, goals, amenities, area, readiness and existing listing URL. Sale captures size with unit, optional asking price, ownership/title status, reason, timeline, listing status and interim-management preference.

Without a configured backend, submissions are **not delivered or saved centrally** and nobody receives an alert. The visitor sees an explicit message and may download their enquiry as JSON. Personal information remains in page memory until download, navigation or reload; there is no browser-storage lead database. This is a preview workflow, not a live enquiry service. Replace placeholder telephone/WhatsApp numbers and finish the draft legal policies before public launch.

## Recommendation and costs

Start with **Bigin Express**, owned by Britsmaid, using two pipelines (Management and Sales). It covers stages, contacts, notes and follow-up activities without needing full Zoho CRM. Express has three team pipelines and ten custom fields per module: use those fields for essential filters, and preserve the full questionnaire in a note plus your own backend record. If every proposal answer must be individually filterable/reportable in Bigin, use **Premier**, which has 25 custom fields per module and more advanced automation. Confirm the final mapping fits the purchased plan before implementation.

Official India prices checked 3 October 2026, before GST, billed annually:

| Users | Express / month equivalent | Express annual payment | Premier / month equivalent | Premier annual payment |
| --- | ---: | ---: | ---: | ---: |
| 1 | ₹400 | ₹4,800 | ₹720 | ₹8,640 |
| 2 | ₹800 | ₹9,600 | ₹1,440 | ₹17,280 |
| 5 | ₹2,000 | ₹24,000 | ₹3,600 | ₹43,200 |

Subscription prices exclude implementation, hosting, optional paid connectors and phone/messaging services. Confirm checkout pricing when purchasing. Bigin Free can trial the process but is limited to one user, one pipeline and 500 records; it is less suitable for two distinct team workflows. A shared spreadsheet plus form notifications is cheaper to start, but requires manual reminders and lacks a dependable consolidated activity history, permissions and pipeline automation. Full Zoho CRM becomes useful later for more complex reporting, approvals and broader sales operations.

Sources: [Official Indian pricing](https://www.bigin.com/articles/bigin-india-pricing-clarification.html), [plans](https://www.bigin.com/pricing.html), [official limits](https://www.bigin.com/articles/faqs-about-bigin.html).

## Integration process

1. Britsmaid creates and owns the Zoho account, billing and administrator access; enable MFA and invite staff with appropriate roles. Select the intended data centre. Do not create the production account in a contractor's name.
2. Create Management and Sales pipelines. Suggested management stages: New → Contacted → Assessment scheduled → Proposal sent → Follow-up → Agreement → Onboarding → Won / Lost. Sale stages: New → Qualified → Title review → Valuation → Listed → Buyer discussions → Completed / Lost. Assign an owner to each enquiry.
3. Map contact name/email/mobile to Contacts. Map property location/type and key sale or management fields to a pipeline record. Store all answers, form type, source page, timestamp, consent evidence and estimate assumptions in a related note and durable backend record. Use the field-metadata API to discover actual account field names rather than guessing them. Track each property enquiry separately, even when a contact already exists.
4. For the custom design and calculator, create a same-origin serverless `POST /api/leads` endpoint. Register a Zoho OAuth client owned by Britsmaid. Complete OAuth for the appropriate data centre and store client secret, refresh token and access tokens only on the server. Use least-privilege scopes for the records and notes you need. The browser must never call Zoho with secret credentials.
5. Validate every answer and consent again on the server; impose length/type limits, rate limiting and spam protection. Persist the enquiry with its submission ID before contacting Zoho, deduplicate contact records by email/mobile and use the submission ID for idempotency. Keep the complete answers even if a CRM write fails.
6. Create/update the Contact, create the linked pipeline record at New, append a full questionnaire note, then trigger an assigned-owner email notification and create a follow-up task. Configure Bigin workflow alerts or an outbox/worker on your backend. Test notification delivery and retries. A Bigin webhook reports CRM changes; it does not itself email your team.
7. Configure `window.BritsmaidConfig = {leadEndpoint: '/api/leads'}` before loading `assets/enquiries.js`, or update its default. The endpoint must return JSON `{ "accepted": true, "submission_id": "..." }` only after durable receipt. Failed/unconfirmed responses leave the answers available for retry or download. For asynchronous CRM sync, queue safely and monitor failures independently.
8. Test management and sale separately, email-only and phone-only contact routes, unchecked consent, invalid values, repeat requests, CRM outages, full answer preservation, source page, workflow notifications and task creation. Staff can add notes, log calls, schedule activities and review record history in Bigin.

Bigin native webforms or Zoho Forms can be a lower-code alternative. Verify field limits, conditional contact validation, calculator result mapping and hidden source fields before replacing the custom forms; paid connector costs may apply.

Developer references: [Bigin APIs and OAuth](https://www.bigin.com/developer/docs/apis/v2/), [create records and data-centre endpoints](https://www.bigin.com/developer/docs/apis/v2/insert-records.html).

## Website payload contract

The browser generates `submission_id`, `form_type` (`management` or `sale`), `source_page`, `submitted_at`, `consent` (accepted, policy URL and capture time), and `answers` containing every named input. Management includes an `amenities` array and, for 1–12 bedrooms, `calculator` with its input and estimate/model version. The backend should compute its own trusted timestamps, retain the policy version, validate the payload, and recompute the estimate rather than trusting browser values. No CRM lead tracking or alert delivery is implemented in this static website.

## Calculator model

`assets/earnings.js` is a pure reusable calculation function. It uses an illustrative nightly base of ₹1,800 + ₹1,100 per bedroom (1–12 bedrooms). Pool +20%, gym +5%, garden +4%, parking +2%, AC +6%, Wi-Fi +3%; land adds up to 5% at 50 cents. The total uplift is capped at 45%. Monthly gross booking revenue uses 30 days at 45–60% occupancy, rounded to ₹100. A three-bedroom home without extras shows ₹68,900–₹91,800/month; with a pool it shows ₹82,600–₹1,10,200/month.

These are aspirational scenario assumptions, not researched rates or a prediction. The public result states that operating costs, commissions, management fees and taxes are excluded. Location is collected but never affects the calculation. Land alone does not produce an unlimited increase. Real projections must be prepared after inspection and comparable-market research; have the team approve these assumptions before publishing.
