# Runbook: how the search and verification were done

Date run: 2 November 2026. Tooling: Claude Code with web search, web fetch and a Chrome browser session.

## 1. Discovery

1. Web searches for Seek NZ, Indeed NZ and the named recruiters (Hays, Talent Army, Absolute IT, Find, Halcyon Knights, Enterprise) with iOS, Flutter, mobile and "visa sponsorship" terms.
2. Plain HTTP fetches of Seek, Indeed, Jora and Glassdoor returned 403, so listings were read in a real Chrome tab.
3. Seek searches used, sorted by listing date:
   - `https://www.seek.co.nz/jobs?keywords=iOS+Swift&sortmode=ListedDate`
   - `https://www.seek.co.nz/jobs?keywords=Flutter&sortmode=ListedDate`
   - `https://www.seek.co.nz/jobs?keywords=%22mobile+engineer%22+OR+%22mobile+developer%22&sortmode=ListedDate`
   - `https://www.seek.co.nz/jobs?keywords=iOS+Flutter+Developer&sortmode=ListedDate`
   - `https://www.seek.co.nz/jobs?keywords=%22visa+sponsorship%22+OR+%22accredited+employer%22+developer&sortmode=ListedDate&classification=6281`
4. Each shortlisted Seek listing was opened and the description text was scanned for visa, sponsor, work rights, relocation, citizen and resident.
5. Indeed NZ Flutter search (`https://nz.indeed.com/jobs?q=Flutter&sort=date`) returned four results, none Flutter-specific.
6. Recruiter boards: Absolute IT listing fetched directly; Talent Army job board checked (the iOS & Flutter ad had been removed); Seequent Workday board searched for "relocation" and "software engineer" in New Zealand (zero open roles).

## 2. Accreditation check

The INZ register at
`https://immigration.govt.nz/work/requirements-for-work-visas/approved-employers/accredited-employer-list`
is a JavaScript widget with no public API or bulk download. Each employer was typed into the keyword box
and the result list read. Some accredited employers opt out of publication, so "not found" is not proof
of non-accreditation. Results are in `data/accredited-employer-checks.csv`.

## 3. Green List check

Appendix 13 of the INZ Operational Manual (effective 9 March 2026, `https://www.immigration.govt.nz/opsmanual/89117.htm`)
lists Software Engineer 261313 under Tier 1 with remuneration of NZD 70.00 per hour or above
(about NZD 145,600 per year), or NZD 87.50 per hour plus 10 years' experience on a contract for services.
That page is marked archived, so a newer version exists; check the current Appendix 13 before relying on the number.

## 4. CV

Built from the candidate's existing CV files plus facts verified in the GME iOS repository (first commit date,
commit count, module structure, fastlane lanes, Tuist and SPM migration). Benchmarked against the Tahatū
(NZ government careers) CV guidance: two pages, plain font, no photo, no nationality, contact, personal statement,
key skills, reverse-chronological work history, education, referees on request. Numbers that could not be
proven were removed.

## 5. Outreach

Only Absolute IT publishes a recruiter name (no email). Air New Zealand and Halter accept applications only
through Seek or their careers sites. Gmail sending requires the user to authenticate the Gmail connector
(`/mcp` in Claude Code) with the sending account.

## What to redo on a rerun

- Steps 1.3 to 1.6 (listings change daily).
- Step 2 for any new employer.
- Step 3 once a year or after an INZ amendment circular.
