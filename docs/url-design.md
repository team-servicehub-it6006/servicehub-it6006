# URL design

Decided before writing any views, because in Django the URL map is where the security boundary
is easiest to see and easiest to get wrong.

## Rules we agreed

1. Group by **who the URL is for**, not by what it acts on. Everything under `/manage/` is
   administrator-only, everything under `/staff/` is for cleaners. A route in the wrong group
   stands out in review without reading the view.
2. Never put a sequential id in a URL pointing at somebody's record. Bookings use a UUID.
3. Services use a slug, because the catalogue is public and a readable URL is worth more there
   than an opaque one. There is nothing to enumerate.
4. URLs read as nouns and end in a slash. Verbs live in the HTTP method, or in a trailing
   segment like `/cancel/` where a confirmation page is needed.
5. Namespaced per app, so templates reverse `bookings:detail` instead of hard-coding a path
   that quietly breaks later.

## The map

```
/                                 public   home and the service cards
/services/                        public   catalogue
/services/<slug>/                 public   one service
/privacy/  /terms/                public

/accounts/signup/                 public   always creates a Customer, never staff
/accounts/login/                  public   throttled
/accounts/logout/                 POST     not a link, so an image tag cannot trigger it
/accounts/password_change/        signed in
/accounts/password_reset/...      public
/accounts/profile/                signed in, edits request.user only

/dashboard/                       signed in, routes by role

/bookings/                        customer, own records
/bookings/new/<slug>/             customer
/bookings/<uuid>/                 owner, assigned cleaner, or admin
/bookings/<uuid>/edit/            owner, while pending or confirmed
/bookings/<uuid>/cancel/          owner, while pending or confirmed

/staff/jobs/                      cleaner, own jobs
/staff/jobs/<uuid>/status/        assigned cleaner, POST only

/manage/bookings/                 admin
/manage/bookings/<uuid>/assign/   admin
/manage/services/                 admin
/manage/services/new/             admin
/manage/services/<slug>/edit/     admin
/manage/services/<slug>/delete/   admin, POST only
/manage/users/                    admin
/manage/users/new/                admin
/manage/users/<id>/roles/         admin
/manage/audit/                    admin, read only

/servicehub-admin/                superuser. Moved off /admin/ so the default path 404s
```

## The one integer id

`/manage/users/<id>/roles/` uses the primary key. Considered and kept: the page is behind an
administrator permission, an administrator can already see every user, and a readable id makes
the office's job easier. Nothing a customer can reach uses a sequential id.
