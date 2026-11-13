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
| `reports/2026-11-13-dotnet-remittance-fintech-report.md` | Second search: .NET/C#, remittance and fintech roles (Xe, Propellerhead, Bureau, Hnry, Sharesies) |
| `data/job-listings.csv` | Every live listing found, with status and link |
| `data/accredited-employer-checks.csv` | Employer-by-employer result from the INZ register |
| `cv/manish-adhikari-cv.md` | The CV, benchmarked against NZ government CV guidance (contact details redacted) |
| `outreach/emails.md` | Draft emails per employer (contact details redacted) |
| `private/` | Gitignored. Versions of the CV and emails with real phone and email |

## Key findings (as of 2 Nov 2026)

- No live NZ iOS or Flutter listing stated "AEWV sponsorship offered" outright.
- One recruiter ad (Absolute IT, Senior iOS Engineer, Auckland) said the client will sponsor candidates who relocate at their own cost.
- Air New Zealand, Halter, NZ Automobile Association and SBS Bank had live senior iOS or mobile roles and are on the INZ accredited register, but their ads were silent on visas.
- Software Engineer (ANZSCO 261313) is Green List Tier 1. **Updated 13 Nov 2026:** the live INZ Green List page now says NZD 72.80 per hour (208% of the 2025 median wage), or NZD 109.20 plus 10 years on a contract for services. The NZD 70.00 figure in the 2 Nov report is out of date.
- Flutter roles in NZ were close to zero on the search date.

## .NET, remittance and fintech search (13 Nov 2026)

- Best domain fit: Xe Full Stack Software Engineer, Christchurch (C#/.NET, KYC, payments, FX). No visa statement.
- Propellerhead (accredited) invites international applicants relocating to Auckland.
- Absolute IT has a Senior Software Engineer ad whose client will sponsor people moving at their own cost.
- The CV has no commercial .NET work, so these roles need a .NET project or honest positioning on domain fit.

## Live job board (auto-updated)

- Page: https://apexbymanish.github.io/nz-job-scout/ (plain-text notepad style; click a title for details, 25 per page)
- `scout/fetch_jobs.py` reads Seek NZ's search API (standard library only) for the mobile, server, UI/UX, product and fintech queries in `scout/config.json` (category rules live there too) and writes `site/jobs.json`.
- Each job is tagged with its INZ status from `data/accredited-employer-checks.csv`. Add a row there after checking a new employer on the register; the next run picks it up.
- `.github/workflows/job-scout.yml` runs every 15 minutes, commits `site/jobs.json` only when the job list changes, and redeploys GitHub Pages.
- Limits: Seek job detail pages block scripts, so the board shows the teaser only. "Mentions visa" means the ad matched a Seek search for visa/sponsorship/relocation words; it may say *no* sponsorship. GitHub can delay scheduled runs, and it disables them after 60 days without repository activity.
- Each job shows "listed N days ago" and "~N days left (est.)". Seek's search API has no closing date, so days left assumes the standard 30-day Seek ad.
- Interview prep (`#/interview` on the page, source `scout/interview.json`): sample questions and practice projects per category, plus NZ links. The questions and projects are NOT official; they were written for this repo. The links are official government pages (careers.govt.nz, Tahatū, Immigration NZ Live and Work) or job-board advice (SEEK, Trade Me). The scheduler rechecks the links once a day.
- NZ rules page (`#/rules`, source `scout/rules.json`): key AEWV, Green List, Straight to Residence and Skilled Migrant Category rules, each linked to its official INZ page, plus recent INZ changes and alerts. INZ's site blocks scripts, so these facts are read by hand or by a daily research agent, never scraped.
- News feed (`site/news.json`): NZ immigration headlines from Google News RSS, refreshed at most hourly by the same workflow. Labelled as news, not official.
- About page (`#/about`): what the project does and how it is built, for anyone reviewing the repo.
- Run locally: `python3 scout/fetch_jobs.py`, then `python3 -m http.server -d site 8000`.

## Rerunning

Follow `docs/runbook.md`. The INZ register is a JavaScript search with no public API, so the
accreditation step is done in a browser, one employer name at a time. Seek and Indeed block
plain HTTP fetches, so listings are read through a real browser session too.

## Publishing this repo

Keep `private/` out of git (it is in `.gitignore`). The CV and emails in the tracked folders
have the phone number and personal email replaced with placeholders.
