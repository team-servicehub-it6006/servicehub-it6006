# Meeting notes

## 22 August, first meeting

Present: Himani, Salauddin, Jyoti.

Agreed the team name is Team ServiceHub. Spent most of the hour arguing about what the project
actually is, which was time well spent because we all had a different idea.

Decisions:

- Project is a booking system for a small home cleaning business. Not a CRM. We only store what
  we need to deliver and bill a booking.
- Three roles: customer, cleaner, administrator.
- Django, because the assessment is about authentication and authorisation and Django gives us
  those properly rather than as add-ons.
- GitHub for version control, GitHub Projects for the Kanban board, WhatsApp group for day to
  day, GitHub issues for anything that needs a record.
- Areas: Himani on authentication and permissions, Salauddin on bookings and validation, Jyoti
  on services, admin screens and the interface.

Actions:

- Everyone to read the brief properly before Monday.
- Himani to set up the org, repo and board.
- Salauddin to write up the problem statement.
- Jyoti to sketch the URL structure.

## 25 August

Tutor asked what the business actually is and pointed out that customer management is a huge
scope. Fair. We narrowed it: we store name, contact details and booking history, and nothing
else. Dropped the customer notes field entirely, nobody could say what it was for.

## 29 August

Talked about the database. SQLite for development because it is one file and nobody has to
install anything. PostgreSQL for production. Ran the migrations against both to check the
portability claim is real rather than something we just wrote down.

## 2 September

Went through the permission matrix line by line. The thing that took longest was working out
that the role on its own is not enough. Every cleaner holds the same permission, so if we only
check the role, any cleaner can open any job by changing the id in the address bar. We need a
second check on the actual record.

Also agreed: bookings get a UUID in the URL, not a number.

## 4 September

Dropped online payment from iteration 2. Storing card details properly brings obligations none
of us can meet in the time left, and doing it badly is worse than not doing it. It goes in the
backlog with a note saying why.

## 5 September

Mock-ups done and shared in the group chat before the end of the lab. Ten screens covering all
three roles. Two things left open: whether a cleaner needs anything beyond moving a job's status,
and whether a UUID in the booking URL is worth the ugliness. Both to be settled on Monday.

## 7 September, Monday meeting

Present: Himani, Salauddin, Jyoti. Weekly slot, 1pm.

Settled the two open questions. A cleaner moves a job's status and does nothing else, no
cancelling and no price changes, because a cleaner has no reason to touch either. The UUID stays.
An ugly URL is a cheaper problem than a guessable one.

Planning is finished, so the repository was created today and the board set up. From here the
contract stages map onto the repo:

- Stage 3, dev environment, GitHub setup and URL design, Salauddin, due Tuesday the 8th
- Stage 4, authentication, Himani, due Thursday the 10th
- Stage 5, authorisation, Jyoti, due Saturday the 12th
- Stage 6, validation and testing, Salauddin, due Monday the 14th
- Stage 7, hardening, documentation and submission, Himani, due Wednesday the 16th

Actions: everyone to accept the organisation invite and put their real name on their GitHub
profile, because the repository currently shows usernames and a marker cannot match a username to
a class list. Himani to open the issues and the board tonight.
