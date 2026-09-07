# How this project works

Written so that any of the three of us can open the repository cold and explain what is in it.
One section per part. Each one says what it does, which files it lives in, and the short answer
to give if somebody asks why it is built that way.

Parts that are not built yet are marked TO COME and will be filled in as we get to them.

---

## The shape of the whole thing

ServiceHub is a Django web application for a home cleaning business. Three kinds of people use
it and they must not be able to do each other's jobs.

- **Customer** — browses services, books a clean, sees their own bookings, cancels one.
- **Cleaner** — sees the jobs assigned to them, moves a job through its statuses.
- **Administrator** — sees everything, assigns cleaners, manages services and users.

Everything else in the repository exists to keep those three apart.

The code is split into four Django apps:

| App | Holds |
|---|---|
| `accounts` | Who people are, and which role they hold |
| `services` | What the business sells, and what it costs |
| `bookings` | The actual jobs, and their history |
| `core` | Shared things: base templates, the audit log, security middleware |

Plus `config/`, which is settings and the master URL map, not really an app.

---

## Running it

    python manage.py migrate      # build the database
    python manage.py test         # run the tests
    python manage.py runserver    # start it, then open http://127.0.0.1:8000/

---

## Settings, and why nothing secret is in the file

**Files:** `config/settings.py`, `.env.example`, `.gitignore`

There is one settings file. It behaves differently in development and production because it reads
environment variables, not because there are two copies of it. Two copies drift apart, and the one
nobody is looking at is the one that ships insecurely.

The `SECRET_KEY` is what Django uses to sign session cookies. Anyone who has it can forge a login
session for any account. So it is read from the environment:

    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

and if it is missing while `DEBUG` is off, the application refuses to start. A loud crash at
start-up beats a public site quietly running on a key that is sitting in a public repository.
`.gitignore` keeps the real `.env` file and the database out of git entirely.

**If asked:** "Secrets come from the environment. The repository is public, so anything committed
to it is published. A missing key crashes the app on purpose rather than falling back to a
default."

---

## Users and roles

**Files:** `accounts/models.py`, `accounts/migrations/0002_seed_roles.py`

Email is the login field, not a username. The business already identifies customers by email, and
a separate username is a field nobody fills in honestly. `AbstractUser` gives us Django's password
hashing, permissions and admin integration for free; we only replace the login field.

Email is lower-cased on save, so `Himani@example.com` and `himani@example.com` cannot become two
separate accounts that slip past the unique constraint.

**Roles are Groups, not a column.** There is no `role = models.CharField(...)` on the user. A
person's role is which of the three auth Groups they belong to. Two reasons:

1. Permissions attach to the group. The answer to "who can assign a cleaner?" is one lookup, and
   revoking it is one change instead of an audit of every account.
2. A person can hold two roles if the business ever needs it, without a schema change.

The groups and their permissions are created by a **migration**, not by a script somebody has to
remember to run. That way a fresh clone, the test database and production all come up with
identical roles. Roles that differ between machines are how authorisation bugs stay hidden.

**If asked:** "Role is group membership. Permissions hang off the group, never off a person, and
the groups are seeded in a migration so every database is the same."

---

## Services and the price

**Files:** `services/models.py`

A service is one thing the business sells. Services are **deactivated, never deleted**, so a
booking taken against an old service keeps working and keeps its history.

The price is worked out by `Service.price_for(bedrooms, bathrooms)`:

> base price, plus $25 for every bedroom over two, plus $30 for every bathroom over one.

That method is the only place a price is decided. **The booking form never submits a price.** If
it did, anyone could open the browser inspector, change the hidden field to `1.00`, and pay a
dollar for a deep clean. The browser is not trusted with anything that matters.

**If asked:** "Pricing is server side. The form sends the property size, not the price."

---

## Bookings

**Files:** `bookings/models.py`

One booking is one job, at one address, on one date.

**The id is a UUID**, not `1, 2, 3`. If booking ids counted upwards, a signed-in customer could
change the number in the URL and walk through every booking in the system. The UUID makes that
guessing impractical. It is not the real defence — the ownership check below is — but it is the
layer underneath it.

Because a UUID is unusable over the phone, each booking also gets a short **reference** like
`SH-4A21` for humans to quote.

**The property address is separate from the customer's own address.** People book cleans for
places they do not live at: a rental, a parent's house, a flat they are moving out of. We got this
wrong in the first sketch and fixed it.

**`access_notes`** is the most sensitive field in the system, because it is how a cleaner gets
into someone's house. It is optional, and it is wiped 30 days after the job is done.

### Who is allowed to see a booking

One method, `Booking.visible_to(user)`, answers it:

    return (self.customer_id == user.id
            or self.cleaner_id == user.id
            or user.has_perm('bookings.view_all_bookings'))

This is the **object-level** check and it is the heart of the assignment. Holding the Cleaner role
is not enough, because *every* cleaner holds that same role. The question is not "are you a
cleaner" but "is this particular job yours". Keeping it in one method means the tests can point at
it and no view can forget it.

### Statuses

    pending     -> confirmed, cancelled
    confirmed   -> in_progress, cancelled
    in_progress -> completed
    completed   -> nothing
    cancelled   -> nothing

Declared once as a dictionary and checked on the server. The buttons on the page only ever offer
legal moves, but the buttons are not what the server receives. A hand-written request could ask
for anything, so the server checks.

Every change writes a `BookingStatusHistory` row: who changed it, from what, to what, when. That
is what settles an argument about a past job.

**If asked:** "UUID ids so URLs cannot be walked, one ownership method so no view can forget the
check, and status moves validated on the server rather than in the template."

---

## The audit log

**Files:** `core/models.py`

One row per privileged action: role changes, service deactivations, cleaner assignments. It stores
**what was done and by whom, not the contents of the record**. A log that copied every customer's
address would be a second copy of the exact thing we are protecting, kept for longer than the
original.

---

## Tests

**Files:** `core/tests.py`

Fourteen tests covering the three model rules where trusting the browser would be a security bug:
the price the server calculates, the status moves it allows, and who owns a booking.

    python manage.py test

The full access-control suite, driving each role at each URL, comes later and is issue #17.

---

## TO COME

- Templates and the Bootstrap layout (issue #7)
- Service catalogue and detail pages (issues #5, #10)
- Signup, login, lockout after five failures (issue #8)
- Dashboard that routes by role (issue #9)
- Booking create, list, cancel (issue #11)
- Cleaner job list under `/staff/` (issue #13)
- Admin screens under `/manage/` (issue #14)
- Privacy statement and terms (issue #15)
- Server-side validation on every form (issue #16)
- Access control test suite (issue #17)
- Session, cookie and transport hardening (issue #18)
