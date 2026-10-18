# Britsmaid website and admin studio

The original Britsmaid villa website, extended with a Flask content studio, first-party CRM, moderated feedback, saved booking enquiries, private encrypted guest ID registration and periodic OTA iCal imports/exports.

Run `python -m pip install -r requirements.txt`, then `python app.py`. See [CMS-README.md](guides/CMS-README.md) for local credentials, persistent storage, production hosting and backups. Never publish `.data`, environment secrets, ID encryption keys, guest records or local login details.

The full application requires a Python backend host with HTTPS and persistent storage. **GitHub Pages cannot run the admin, database, CRM, saved enquiries, private ID uploads or calendar worker.** It can display only a read-only static preview generated with `python cms/export_static.py --base-path /Britsmaid-Demo-website`.

The `docs/` folder is a separate **public showcase**, generated with `python cms/export_showcase.py`. It includes the website and admin screens with clearly fictional sample data and simulated changes stored in that browser for 24 hours. Use fictional details only; Reset demo clears them. Public website pages remain snapshots. It sends no real enquiries and accepts no real uploads or payments. GitHub Pages serves `main` → `/docs`. The actual Flask application never loads the showcase adapter and remains ready for a backend host.

See [BOOKINGS-AND-CALENDARS.md](guides/BOOKINGS-AND-CALENDARS.md) for booking/payment placeholders and iCal limits, and [CRM-AND-APP-SETUP.md](guides/CRM-AND-APP-SETUP.md) for CRM, guest-document retention and the later Emergent app integration.

Payment processing, automatic email notifications, Google Analytics and the Emergent mobile app are not connected. No real guest records or secrets are included in the source repository.

## Project folders

Start locally by double-clicking `Start Britsmaid.cmd`. Keep its window open. Website: http://127.0.0.1:8000/ ; studio: http://127.0.0.1:8000/admin . Do not open the page-source files directly.

- `pages/`: original public page sources, served by the Python app at their existing URLs.
- `templates/`: dynamic property, feedback and admin templates.
- `assets/`: public styles, JavaScript, optimised photographs and logos.
- `cms/`: seed preparation, exports, publishing and backup utilities.
- `guides/`: hosting, CRM, app, bookings, calendar and older integration setup notes.
- `tests/`: current backend and browser checks.
- `docs/`: generated GitHub Pages showcase; do not edit manually.
- `deliverables/`: finished reports and documents for the business.
- `previews/website/`: local screenshots, excluded from publishing.
- `archive/`: historical integration screenshots and older static test scripts, excluded from publishing.
- `.data/`: private local database, account details, ID key and uploads; never publish.
- `.publish-repo/`: local Git publishing checkout; never copy into hosting images.
- `dist/` and `test-results/`: generated snapshots and isolated test output, not application source.

The Python entry point and backend modules stay at the root so existing launchers, imports and the Docker command remain straightforward. The public website URLs and private data location are unchanged.

The separate Emergent app is a different project. Its `frontend/node_modules` and Python virtual environments are generated dependencies and should live outside a OneDrive-synchronised working folder. Git ignore rules do not stop OneDrive from syncing them.
