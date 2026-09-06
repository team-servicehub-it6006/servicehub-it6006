# ServiceHub

A booking system for a small home cleaning business, built for IT6006 Assessment 2 at Whitecliffe
by Team ServiceHub.

Customers browse services and book their own cleans. Cleaners see the jobs assigned to them and
nothing else. The office manages services, bookings, users and roles.

The point of the project is the security work rather than the booking workflow: authentication,
role and object level authorisation, server-side validation, and a URL structure that does not
leak records.

## Team

| Name | Student ID | Area |
|---|---|---|
| Himani Thapa Magar | 20240670 | Authentication and permissions |
| Jyoti Singh | 20241046 | Services, admin screens, interface |
| Salauddin Ohine | 20251379 | Bookings and validation |

## Running it

Python 3.12 or newer.

```
python -m venv .venv
.venv\Scripts\activate          # macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS or Linux: cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

## Planning documents

- `docs/requirements-notes.md` — the problem, business requirements, user stories
- `docs/roles-and-permissions.md` — the permission matrix and why the role check is not enough
- `docs/url-design.md` — the URL map and the rules behind it
- `docs/meeting-notes.md` — decisions and who made them
