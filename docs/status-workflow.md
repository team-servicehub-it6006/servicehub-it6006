# Booking status workflow

A booking moves through five statuses. This is a note on which moves are allowed, who is allowed
to make them, and why we wrote them down in one place instead of scattering the rules through the
views.

## The five statuses

| Status | What it means |
|---|---|
| Pending | Customer has booked. Nobody has looked at it yet. |
| Confirmed | An administrator has accepted it and assigned a cleaner. |
| In progress | The cleaner has arrived and started. |
| Completed | Job done. |
| Cancelled | Called off, by the customer or by an administrator. |

## Which moves are allowed

    pending      ->  confirmed, cancelled
    confirmed    ->  in progress, cancelled
    in progress  ->  completed
    completed    ->  nothing
    cancelled    ->  nothing

Completed and cancelled are the end of the line. Once a booking reaches either one it does not
move again.

The two that matter most are the ones missing from that list. A cancelled booking cannot go back
to confirmed, and an in progress job cannot be cancelled. If a cleaner has already turned up at
somebody's house, cancelling it after the fact would leave the record saying the job never
happened.

## Where the rule lives

All of it sits in one dictionary at the top of `bookings/models.py`, called
`ALLOWED_TRANSITIONS`. The model method `can_transition_to()` is the only thing that reads it, and
every view that changes a status has to go through that method.

We did it this way because the alternative is an `if` statement in each view, and the day somebody
adds a sixth status they will update four of the five places. Having it in one dictionary means
the rule is either right everywhere or wrong everywhere, and wrong everywhere is much easier to
spot.

It also has to be checked on the server, not just hidden in the template. If we only hide the
Cancel button, anyone can still send the POST by hand and cancel a completed job. Hiding the
button is for the person using the site. The transition check is what actually stops it.

## Who can move what

| Move | Who |
|---|---|
| pending to confirmed | Administrator |
| anything to cancelled | The customer who owns it, or an administrator |
| confirmed to in progress | The cleaner assigned to that job |
| in progress to completed | The cleaner assigned to that job |

The cleaner's two moves are guarded by the `update_job_status` permission, and on top of that the
view checks the cleaner is the one actually assigned. Holding the permission is not enough. A
cleaner cannot start somebody else's job.

## Editing a booking

A customer can change the date, time or address only while the booking is pending or confirmed.
That set is called `EDITABLE_STATUSES` and the `is_editable` property on the model is what the
templates ask. Once the cleaner is on site, editing the address makes no sense.

## Keeping the history

Every status change writes a row into `BookingStatusHistory`: the old status, the new one, who did
it, when, and an optional note. Nothing is overwritten.

This is here for the argument that happens later. If a customer says their job was never cancelled
and an administrator says it was, the history rows answer it with a timestamp and a name. It is
also part of what makes the audit trail worth anything, because a status field on its own only
ever tells you where a booking ended up, never how it got there.

## Still to decide

Whether an administrator should be able to force a move that is not in the table, for the case
where a cleaner marks a job completed by mistake. Right now nobody can, including administrators.
Leaving it strict for the assessment. If we allowed it, it would need its own permission and a
mandatory note explaining the override.
