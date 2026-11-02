# NZ Tech Job Scout

A repeatable workflow for finding New Zealand software and mobile engineering roles that can
sponsor an Accredited Employer Work Visa (AEWV), verifying each employer on the official
Immigration New Zealand (INZ) register, and producing a tailored CV and outreach emails.

Built on 2 November 2026 with Claude Code. Everything in `reports/` and `data/` is from live
searches on that date and will go stale; rerun the runbook to refresh.

## What is here

| Path | What it is |
| --- | --- |
| `prompts/job-scout-system-prompt.md` | The system prompt that drives the search session |
| `prompts/outreach-prompts.md` | Reusable prompts for cover letters and CV tailoring per company |
| `docs/runbook.md` | Step-by-step of how the search and verification were actually done, including what failed |
| `reports/2026-11-02-search-report.md` | The full search output: verified matches, deep dives, visa notes |
| `data/job-listings.csv` | Every live listing found, with status and link |
| `data/accredited-employer-checks.csv` | Employer-by-employer result from the INZ register |
| `cv/manish-adhikari-cv.md` | The CV, benchmarked against NZ government CV guidance (contact details redacted) |
| `outreach/emails.md` | Draft emails per employer (contact details redacted) |
| `private/` | Gitignored. Versions of the CV and emails with real phone and email |

## Key findings (as of 2 Nov 2026)

- No live NZ iOS or Flutter listing stated "AEWV sponsorship offered" outright.
- One recruiter ad (Absolute IT, Senior iOS Engineer, Auckland) said the client will sponsor candidates who relocate at their own cost.
- Air New Zealand, Halter, NZ Automobile Association and SBS Bank had live senior iOS or mobile roles and are on the INZ accredited register, but their ads were silent on visas.
- Software Engineer (ANZSCO 261313) is Green List Tier 1 with a pay condition of NZD 70.00 per hour in the 9 March 2026 list. Verify the current list before negotiating.
- Flutter roles in NZ were close to zero on the search date.

## Rerunning

Follow `docs/runbook.md`. The INZ register is a JavaScript search with no public API, so the
accreditation step is done in a browser, one employer name at a time. Seek and Indeed block
plain HTTP fetches, so listings are read through a real browser session too.

## Publishing this repo

Keep `private/` out of git (it is in `.gitignore`). The CV and emails in the tracked folders
have the phone number and personal email replaced with placeholders.
