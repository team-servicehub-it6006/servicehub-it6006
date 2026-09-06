# Roles and permissions

Three groups. Permissions hang off the group, never off a person, so changing what a role can do
is one change in one place and the answer to "who can do this" is one lookup.

| | Customer | Cleaner | Administrator |
|---|---|---|---|
| See the service catalogue | yes | yes | yes |
| Create a booking | yes | no | yes |
| See a booking | own only | assigned only | all |
| Edit a booking | own, before it starts | no | yes |
| Cancel a booking | own, before it starts | no | yes |
| Move a job's status | no | own jobs only | yes |
| Assign a cleaner | no | no | yes |
| Add, edit, deactivate a service | no | no | yes |
| Create a staff account | no | no | yes |
| Change somebody's role | no | no | yes |
| Read the audit log | no | no | yes |

## Custom permissions we need

Django gives us add/change/delete/view per model. These three do not fit that shape:

- `view_all_bookings` — the difference between "my bookings" and the whole list
- `assign_cleaner`
- `update_job_status`

## The thing that took us a whole meeting

Holding the Cleaner role is not enough to open a job. Every cleaner holds the same permission.
If we stop at the role check then any cleaner can open any booking by changing the UUID in the
address bar, and we would have built a permission system that does nothing.

So there are two checks and both have to pass:

1. Does this role get to do this kind of thing at all? (permission)
2. Is this particular record any of their business? (owner, or assigned cleaner, or admin)

The second one lives on the model as `Booking.visible_to(user)` so there is exactly one place
that answers it, and the tests point at the same method the views use.

## Other rules

- Self-registration always produces a Customer. There is no role field on the sign-up form, so
  nobody can promote themselves.
- Staff accounts are created by an administrator only.
- An administrator cannot remove their own administrator role. That is a safety rule, not a
  security one. It stops the business locking itself out with one careless click.
- People are deactivated, never deleted, so the jobs they worked stay attributable.
