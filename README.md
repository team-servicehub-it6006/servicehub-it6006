# ServiceHub

ServiceHub manages home-cleaning bookings. Customers manage their own bookings, cleaners work through assigned jobs, and administrators manage bookings, services, staff accounts and roles.

## Open on Windows

1. Right-click `submission.zip`, choose **Extract All**, then open the extracted **ServiceHub** folder. Do not run it inside the ZIP.
2. Install Python 3.12, 3.13 or 3.14 from [python.org](https://www.python.org/downloads/windows/) if needed. Enable **Add Python to PATH** during installation.
3. Double-click **START.cmd**. The first start creates the environment, installs bundled dependencies, applies migrations and adds demonstration records. Later starts keep the database.
4. Wait for `Starting development server at http://127.0.0.1:8000/`.
5. Open **http://127.0.0.1:8000/** in your browser.
6. Keep the command window open. To stop the app, select that window and press **Ctrl+C**.

The app runs on your computer with SQLite. No hosting account, PostgreSQL or `.env` file is needed. Dependencies, styling and navigation assets are bundled locally. Python itself must be installed separately.

## Demonstration accounts

Every demonstration account uses **ServiceHub2026!**. Use fictional data when trying the app.

| Role | Email |
|---|---|
| Customer | h.thapa@example.com |
| Second customer | j.singh@example.com |
| Cleaner | a.williams@example.com |
| Second cleaner | s.pousini@example.com |
| Administrator | p.raman@example.com |
| Django superuser | admin@servicehub.local |

On a narrow window, select the navigation menu button to see links and **Sign out**. Sign out before switching accounts.

## Try the workflows

**Customer:** sign in, open **Services**, choose a service and select **Book this service**. Choose a future date, a start time between 07:00 and 18:59, an address and a four-digit postcode. Submit, check the total, then try **Edit booking** or **Cancel booking**. Select your name in the menu to update your profile or change your password.

**Administrator:** sign in and select **Assign** on a pending booking. Choose a cleaner and save; overlapping assignments are refused. Open a booking to edit or cancel it before work starts. Use **Manage services**, **Users** and **Audit log** for office tasks. Booked services are deactivated instead of deleted. A service duration cannot change while it has active bookings.

**Cleaner:** sign in, open **My jobs**, select **Start job**, then **Mark complete**. Only assigned jobs are listed. Customer and cleaner accounts cannot open management pages.

**Password reset:** select **Forgot your password?** and enter a demonstration email. The reset email appears in the command window in local mode. Copy its full link into the browser, choose a new password and sign in again. Local mode does not send real email.

## PowerShell setup

Open the extracted app folder in File Explorer. Click the address bar, type `powershell` and press Enter. Run each line separately:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-local.txt
$env:DJANGO_DEBUG = '1'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

If `python` is not recognised but the launcher is installed, use `py -3.14` on the first line. Use `py -3.13` or `py -3.12` for those versions. No environment activation or execution-policy change is needed.

## Checks and maintenance

After setup, run these in the app folder:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py clear_access_notes --dry-run
.\.venv\Scripts\python.exe manage.py clear_access_notes
```

Cleanup removes access notes 30 days after recorded completion or cancellation. The operator must run or schedule it regularly. It does not delete accounts or booking records.

## Troubleshooting

- **Port already in use:** stop the other window, or run `.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001` and open **http://127.0.0.1:8001/**.
- **No such table:** run migrations using the environment's Python, then run `seed_demo`.
- **Sign-in locked:** five failed attempts lock that email for 15 minutes. Wait before trying again.
- **Blank lists:** run `seed_demo`. Existing bookings are preserved.
- **Startup stops:** read the error in the command window. Check that the whole ZIP was extracted and Python is a supported version.

## Public deployment

The start script is for a local demonstration. Public deployment requires HTTPS, a private `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, explicit allowed hosts, SMTP, a suitable database and a shared cache for throttling across processes. Hosting location, backups and retention scheduling remain operator responsibilities. Demo seeding is blocked when debug is disabled. Do not expose the demo accounts publicly.

Repository: [team-servicehub-it6006/servicehub-it6006](https://github.com/team-servicehub-it6006/servicehub-it6006). Assessment agreements, contribution summaries and evaluation forms are separate from this app package.
