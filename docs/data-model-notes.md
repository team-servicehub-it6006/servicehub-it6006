# Data model notes

## Entities

**User** — one table for all three roles. Role comes from group membership, not a role column,
so a person could hold two if we ever need it. Email is the login field because the business
already identifies customers by email; a separate username is a field nobody would fill in
honestly.

**Service** — what we sell. Deactivated, never deleted, so bookings taken against an old service
keep their history.

**Booking** — the central record. One job, one address, one date.

**BookingStatusHistory** — one row per status change. This is what settles an argument about a
past job.

**AuditLog** — privileged actions only.

## Booking fields, and the argument about each one

| Field | Keep? | Why |
|---|---|---|
| id | UUID | So nobody can find a valid booking by counting upwards |
| reference | yes | `SH-4A21`. People need something to say on the phone. The UUID is unusable out loud |
| customer | FK, PROTECT | Cannot delete a person out from under a booking |
| cleaner | FK, nullable | Not assigned when the booking is made |
| service | FK, PROTECT | Keeps history when a service is retired |
| scheduled_date, scheduled_time | yes | |
| street_address, suburb, postcode | yes | **Separate from the customer's own address.** People book cleans for properties they do not live at. We got this wrong in the first sketch |
| bedrooms, bathrooms | yes | Feeds the price and the duration |
| access_notes | yes, optional | Most sensitive field in the system. Cleared 30 days after the job |
| total_price | yes, decimal | Decimal not float. It is money |
| status | yes | pending, confirmed, in_progress, completed, cancelled |

## Cut from the first sketch

- Date of birth. Nobody could say what it was for.
- A free text "notes about the customer" field. Same problem, and it would have turned into the
  place where somebody writes something they should not.
- A separate CustomerProfile table. One extra join for two fields.

## Status transitions

```
pending     -> confirmed, cancelled
confirmed   -> in_progress, cancelled
in_progress -> completed
completed   -> nothing
cancelled   -> nothing
```

Declared once as a dictionary and checked on the server. The buttons only ever offer legal
moves, but the buttons are not what the server receives.

## Price

Base price plus $25 per bedroom over two plus $30 per bathroom over one. **Worked out on the
server every time.** The form does not submit a price. If it did, anyone could open the
inspector and pay a dollar.
