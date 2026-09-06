# Requirements working notes

Rough version. The tidy one goes in the Requirements Document.

## The problem

Fresh Start Home Cleaning takes forty to sixty jobs a week with six cleaners. Bookings arrive by
phone, by text and through a contact form on a website nobody can edit any more. They all end up
in one shared spreadsheet.

What goes wrong:

- Two cleaners sent to the same address, because two people edited the sheet at once.
- Changes written on the wrong row and then missed.
- Customers cannot see or change a booking without ringing during office hours.
- Anyone with the spreadsheet link can read every customer's home address, and there is no
  record of who looked.

Roughly fifteen hours a week goes on admin that produces nothing.

## Business requirements

- BR-01 Customers can see the services without making an account first.
- BR-02 Customers can register and manage their own bookings at any hour.
- BR-03 One booking, one record, one reference both sides can quote.
- BR-04 The office can assign and reassign a cleaner.
- BR-05 Cleaners see their own jobs and nothing else.
- BR-06 The office can add, edit, price and deactivate services without a developer.
- BR-07 The office can create staff accounts and change roles.
- BR-08 Customer details visible only to that customer, their cleaner, and administrators.
- BR-09 Every status change and role change recorded with who and when.
- BR-10 We can show a customer what we hold and correct it, as the Privacy Act 2020 requires.

## User stories, first cut

Accounts: browse services, view a service, register, sign in, sign out, change password, reset
password.

Customer: make a booking, see my bookings, open one booking, edit it, cancel it, fix my own
contact details.

Cleaner: see my jobs, mark a job started, mark it complete.

Admin: see every booking, filter it, assign a cleaner, manage services, manage users and roles,
read the audit log.

Twenty stories. Seven in iteration 1, the rest in iteration 2.

## Non-functional, the ones that will bite us

- Everything server-side. The browser is not trusted for anything.
- A cleaner must not be able to reach another cleaner's job by editing the URL. This is the one
  we are most likely to get wrong.
- Works on a 360px phone, because that is all a cleaner will ever use.
- Data stays in New Zealand. Client condition, and it is why the off-the-shelf option is out.
