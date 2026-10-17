# Britsmaid — local content studio

This extends our original green-and-ivory website, not the agency Railway website. The full dynamic application needs a Python backend host; a GitHub Pages preview can show only static public content.

New: first-party CRM, ROI/proposal capture, booking guest registration with encrypted private IDs, booking event history and a cookie preference notice. See [CRM-AND-APP-SETUP.md](CRM-AND-APP-SETUP.md) for the current features, privacy/retention setup and the later Emergent app integration process.

## Open the preview

Public site: http://127.0.0.1:8000/

Admin: http://127.0.0.1:8000/admin

The running preview uses a randomly generated local admin password. Open `.data/local-login.txt` on your PC to read it. Do not upload that file. No default/shared password is shipped in source. You can change the password in Website & SEO > Account security.

To restart, run `python app.py` from this project folder, or `start-local.ps1`. The bundled Python and local dependencies are already set up on this PC. On another machine install Python 3.12 and run `python -m pip install -r requirements.txt` first. `.local-deps` and the incomplete `.venv` setup are ignored and are not deployment files.

## What you can manage

- Properties: add a home, edit name/location, description, bedrooms, beds, bathrooms, guest capacity, amenities, optional starting price and search metadata.
- Publish status: draft, published or archived. Archived content is retained rather than deleted. Existing URL names stay fixed so links do not silently break.
- Photographs: upload JPEG, PNG or WebP; resize to at most 2000×1600; convert to WebP; strip location/EXIF metadata; choose the cover, reorder and remove photographs from a listing. Each photo has editable alt text. Upload limit is 12 MB and 40 megapixels per photograph.
- Guest reviews: add approved guest feedback to a particular property or to Britsmaid generally; record source, source link and stay month; draft/publish/archive. Permission must be confirmed before publication. Reviews are editorial testimonials, not a verified-booking review system. No fake reviews or ratings are seeded.
- Website & SEO: homepage heading/intro/image, brand display name, WhatsApp/phone/email, final domain, homepage search title and description. Optional per-property SEO fields override defaults.
- Overview: published/draft counts and recent edit activity. Content backup export is JSON; it does not include account passwords or the photo files.

The two approved villas are imported from the original pages, retaining their text and optimised photography. No nightly prices have been invented. Empty price fields show a personalised-quote message.

## Database and photographs

SQLite stores the property/review records, publication states, photo paths, admin password hashes and edit history in `.data/britsmaid.sqlite3`. New photo files are stored separately in `.data/uploads`. Original optimised seed images remain in `assets/properties`.

Storing images as files/object storage and their paths in the database avoids putting large binary images inside database records. For the initial single-server deployment, use a persistent volume for the database and uploads. A PostgreSQL database plus S3/R2/Supabase Storage is an appropriate later migration if you need multiple application instances; this build currently uses SQLite and volume-based storage, not those cloud services.

Draft/archived page content is excluded from public listings and routes. Uploaded photos have public URLs if their paths are known; this library is not private document storage. Do not upload IDs, ownership papers or confidential guest documents here.

Backups: run `python cms/backup.py` to create a consistent SQLite+uploaded-media ZIP under `.data/backups`. Copy backups to a separate protected location regularly and test a restore. An app-host disk is not itself an offsite backup. Preserve `assets/properties` with the source checkout. SQLite backup contains the admin password hash; protect it and never commit it to GitHub.

## What this is and is not

This is a website CMS with moderated visitor feedback, saved booking requests, manual booking confirmation and periodic iCal imports/exports. Confirmed direct bookings block dates; pending requests do not. It does not provide instant OTA inventory, price distribution, automated payment collection, housekeeping or owner accounting. See [BOOKINGS-AND-CALENDARS.md](BOOKINGS-AND-CALENDARS.md) for the complete workflow and launch setup.

The prior Apps Script owner-enquiry configuration remains in place; its live delivery issue is not represented as fixed by this CMS work. Zoho is not connected by this change. No analytics tracker was silently installed.

## Hosting and GitHub

GitHub stores source code. GitHub Pages cannot run this Python admin, SQLite database or image-upload backend.

Recommended first launch: deploy this app as one web service with a persistent volume, connect your final domain, and use GitHub for its source. The Dockerfile is included. On a Docker host:

1. Set `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` of at least 12 characters before first startup. They initialise the first account only; later changes are made in the account panel. Store them as hosting secrets, not in source.
2. Set `BRITSMAID_ENV=production`, `HOST=0.0.0.0`, the platform's `PORT`, `BRITSMAID_DATA_DIR=/data`, and mount a persistent volume at `/data`.
3. If exactly one trusted reverse proxy sits in front of the service, set `BRITSMAID_TRUST_PROXY=1` so HTTPS origin checking and client-address handling work. Do not enable this for arbitrary untrusted proxies.
4. Route HTTPS to the service. Production cookies are Secure. Keep only one running instance while using SQLite. Do not run this on an ephemeral filesystem or a network-shared SQLite file.
5. Set the final domain in Website & SEO after the domain works. Until then, public HTML is marked noindex and robots disallows crawling.
6. Set up offsite backups and uptime monitoring. Review the existing prototype privacy/terms/cookie pages before business launch.
7. Confirm save/publish/upload/review flows on the hosted service before switching traffic.

An alternative is a read-only GitHub Pages snapshot: `python cms/export_static.py --base-path /Britsmaid-Demo-website`. It writes a new timestamped folder under `dist` and does not publish anything. It excludes the admin, credentials, database, original large image folders and unreferenced uploaded media. Snapshots are marked noindex to avoid competing with the eventual canonical site. Website edits require a fresh export and publish in this mode; the admin itself must still run locally or on a backend host. It is not live dynamic hosting on GitHub Pages.

The static snapshot also removes visitor feedback links and the availability panel. Its booking buttons prepare messages only; saved booking requests, feedback moderation and calendar synchronisation require the hosted Python app.

Publish only reviewed source. Never upload `.data`, `.env`, `.venv`, `.local-deps`, test results, guest IDs, encryption keys or the large original-photo folders. The `.gitignore` and `.dockerignore` cover these. A separate `.publish-repo` checkout is used on this PC to prepare updates while preserving the existing GitHub history; it must not be copied into deployment images.

## SEO included

- Public property content is rendered in HTML by the server, including headings, descriptions, photographs and guest notes.
- Stable `/stays/<url-name>` property URLs, with 301 redirects from the original villa URLs.
- Per-page titles and descriptions, canonical URLs after the final domain is entered, Open Graph sharing metadata, and basic truthful Organization/LodgingBusiness structured data. No invented rating markup, coordinates or rich-result eligibility claims.
- Dynamic XML sitemap with published properties only; robots rules exclude admin/API and keep local preview from indexing.
- Image alt descriptions, WebP uploads, lazy loading for secondary images and responsive layouts.
- Admin pages are always noindex/no-store. Public preview pages remain noindex until the final domain is set.

After hosting: verify the domain in Google Search Console, submit `/sitemap.xml`, inspect the property pages, review real search queries and maintain distinct local property copy. A complete Google Business Profile and consistent name/address/contact details support local discovery. Rankings and rich results are not guaranteed. Vacation-rental rich-result eligibility has additional Google requirements; generic schema alone does not establish eligibility.

## Design references

- Plum Guide: https://www.plumguide.com/ — editorial hierarchy and clear home presentation.
- SaffronStays: https://www.saffronstays.com/ — practical villa information and separation of guest/owner journeys.

The original premium-villa hero, real property photos and green/ivory palette are retained. Typography and decorative motion are quieter. The JPG logo's paper background has been replaced with a transparent monogram in `assets/britsmaid-mark.png` and its favicon derivative. Generated using the built-in image editing tool; source prompt: “Extract only the existing navy B/building/roof monogram and grey window details; remove paper texture, white background, circle, sparkle and the text below; preserve the existing monogram; true transparency.” Original image is retained. This is a raster cleanup for preview, not a commissioned vector master; compare the mark before approving it.

## Verification

`python tests/test_cms.py` runs isolated backend checks for access/CSRF controls, publication transitions, edit conflicts, review permissions and property scope, valid/invalid uploads, escaping and SEO.

`node tests/verify_cms.cjs` runs the local browser flow with an isolated test database. Its bundled runtime paths match this PC; adjust them on other machines. No real enquiries, external messages or cloud writes are made by either test.
