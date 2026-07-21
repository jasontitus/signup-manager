# Staff Guide — Signup Manager

A plain-language guide for admins and vetters using the Signup Manager dashboard. For
technical/setup documentation, see [README.md](README.md).

## Member statuses, in order

1. **Pending** — just applied, waiting to be picked up by a vetter.
2. **Assigned** — a vetter is currently reviewing this person.
3. **Vetted** — approved. Starts the one-month follow-up timer (see below).
4. **Rejected** — not approved.
5. **Needs Follow Up** — a vetter flagged this person for a second look before a decision.
6. **In Signal** — the person has actually been added to Signal. This is the normal
   "resting" state for an active member, and starts the six-month check-in timer.
7. **Declined Signal** — they applied and were vetted, but decided not to join Signal
   after all.
8. **1-Month Followup** / **6-Month Followup** — set automatically by the system (see
   below), not something you set by hand. After checking in with the person, move them
   back to Vetted (for a 1-month followup) or In Signal (for a 6-month followup).

## The automated follow-up sequence

The system pings the follow-up contact automatically — you don't need to track this by
hand:

- **One month after someone is Vetted**, they're automatically moved to
  "1-Month Followup" and an email goes out. This happens for **everyone who was
  vetted**, whether or not they've been added to Signal yet.
- **Six months after someone enters "In Signal"**, they're moved to
  "6-Month Followup" and an email goes out. This only applies to people **actually on
  Signal** — it's a recurring check-in for active members.
- Moving someone back to "In Signal" after a 6-month check-in restarts the six-month
  clock, so people resurface for a check-in indefinitely as long as they stay active.

So: the 1-month ping is about "did we ever get back to this person after vetting them,"
and the 6-month ping is about "are our active Signal members still doing okay."

## Day-to-day tasks

- **Triage tab**: see pending applications. Vetters are auto-assigned the oldest pending
  candidate on login, and the next one automatically after they finish (mark
  Vetted/Rejected) — the "Get Next Candidate" button requests one manually.
- **Database tab**: search/filter all members, edit tags, export to CSV.
- **Tags**: category-based labels (skills, interests, etc.) editable per member or in
  bulk from the Database tab.
- **CSV Export**: pick which columns you want, sort, and export — respects whatever
  filter is currently active. Every export is logged (who, when, how many rows).
- **Stale assignments**: if a vetter goes inactive, their assigned candidates are
  automatically returned to the pending queue after 7 days. Admins can also reclaim
  manually.

## Customizing the signup form

Admins can add, remove, or edit the questions on the public signup form — ask an admin
or whoever maintains the codebase, since this currently requires editing a config file
rather than a form builder in the UI.

## Getting help / reporting a bug

If something looks wrong (a page won't load, an email seems off, a member's data looks
incorrect), report it with as much specific detail as you can: what you clicked, what
you expected, what happened instead, and roughly when. That's usually enough to track
down the cause quickly.
