# Britsmaid website and admin studio

The original Britsmaid villa website, extended with a Flask content studio, first-party CRM, moderated feedback, saved booking enquiries, private encrypted guest ID registration and periodic OTA iCal imports/exports.

Run `python -m pip install -r requirements.txt`, then `python app.py`. See [CMS-README.md](CMS-README.md) for local credentials, persistent storage, production hosting and backups. Never publish `.data`, environment secrets, ID encryption keys, guest records or local login details.

The full application requires a Python backend host with HTTPS and persistent storage. **GitHub Pages cannot run the admin, database, CRM, saved enquiries, private ID uploads or calendar worker.** It can display only a read-only static preview generated with `python cms/export_static.py --base-path /Britsmaid-Demo-website`.

See [BOOKINGS-AND-CALENDARS.md](BOOKINGS-AND-CALENDARS.md) for booking/payment placeholders and iCal limits, and [CRM-AND-APP-SETUP.md](CRM-AND-APP-SETUP.md) for CRM, guest-document retention and the later Emergent app integration.

Payment processing, automatic email notifications, Google Analytics and the Emergent mobile app are not connected. No real guest records or secrets are included in the source repository.
