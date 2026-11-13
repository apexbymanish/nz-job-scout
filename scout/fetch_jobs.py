#!/usr/bin/env python3
"""Fetch NZ job listings from Seek's search API and write site/jobs.json.

Standard library only, so it runs on a bare GitHub Actions runner.
Seek job detail pages block scripts (HTTP 403), so this only uses the search
API: title, company, location, salary, date, teaser and bullet points.
Visa signal comes from Seek's full-text search for "visa sponsorship",
"accredited employer" and "relocation": a hit means the ad mentions the term,
not that it offers sponsorship. Open the ad to read the wording.

The output file only changes when the set of jobs changes, so the scheduled
workflow commits only when there is something new.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scout" / "config.json"
ACCREDITED_CSV = ROOT / "data" / "accredited-employer-checks.csv"
OUT = ROOT / "site" / "jobs.json"
INTERVIEW_SRC = ROOT / "scout" / "interview.json"
INTERVIEW_OUT = ROOT / "site" / "interview.json"
LINK_CHECK_HOURS = 24
RULES_SRC = ROOT / "scout" / "rules.json"
RULES_OUT = ROOT / "site" / "rules.json"
NEWS_OUT = ROOT / "site" / "news.json"
NEWS_MINUTES = 60
# Public Google News RSS search feeds. INZ's own site blocks scripts, so official
# rule changes are tracked in scout/rules.json by a daily research agent instead.
NEWS_QUERIES = [
    '"Immigration New Zealand"',
    'AEWV visa',
    '"Skilled Migrant Category" New Zealand',
    '"Green List" New Zealand immigration',
    '"accredited employer" New Zealand visa',
    'New Zealand work visa changes',
]
NEWS_RELEVANT = re.compile(r"immigra|visa|aewv|migrant|residen|green list|accredited employer|\binz\b|work rights|deport|refugee|citizenship", re.I)
NEWS_BLOCKED_SOURCES = {"legit news", "yen news", "yen.com.gh", "legit.ng"}  # clickbait aggregators
NEWS_IRRELEVANT = re.compile(r"green party|iucn|protected area|election q ?& ?a", re.I)

API = "https://nz.seek.com/api/jobsearch/v5/search"  # www.seek.co.nz 308-redirects here
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

NEGATIVE_VISA = re.compile(
    r"(no|not|unable|cannot|can't|don't|do not|does not)[^.]{0,40}(sponsor|visa)|"
    r"must (have|hold)[^.]{0,30}(residen|citizen|work rights|right to work)", re.I)


def norm(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", " ", name)
    name = re.sub(r"\b(limited|ltd|nz|new zealand|group|holdings|inc|pty)\b", " ", name)
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def load_register():
    """Map normalised employer name -> (status, register name) from our manual INZ checks."""
    reg = {}
    if not ACCREDITED_CSV.exists():
        return reg
    with ACCREDITED_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            term = row["search_term"].split(" (")[0]
            key = norm(term)
            if key:
                reg[key] = (row.get("status") or "", row.get("register_result") or "")
    return reg


def register_status(company, reg, aliases):
    company = aliases.get(company, company)
    c = norm(company)
    if not c:
        return "unknown", ""
    for key, (status, result) in reg.items():
        if c == key or c.startswith(key + " ") or key.startswith(c + " "):
            return status or "unknown", result
    return "unchecked", ""


def fetch(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # network blips, 429s
            if attempt == 2:
                raise
            print(f"retry after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def link_ok(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def build_interview():
    """Copy the interview pack to site/ and re-check its links at most once a day."""
    if not INTERVIEW_SRC.exists():
        return
    src = json.loads(INTERVIEW_SRC.read_text())
    prev = {}
    if INTERVIEW_OUT.exists():
        try:
            prev = json.loads(INTERVIEW_OUT.read_text())
        except ValueError:
            prev = {}
    now = datetime.now(timezone.utc)
    last = prev.get("links_checked")
    fresh = last and now - datetime.fromisoformat(last.replace("Z", "+00:00")) < timedelta(hours=LINK_CHECK_HOURS)
    prev_status = {l["url"]: l.get("status") for l in prev.get("links", [])}
    same_links = set(prev_status) == {l["url"] for l in src["links"]}
    if fresh and same_links:
        for l in src["links"]:
            l["status"] = prev_status[l["url"]]
        src["links_checked"] = last
    else:
        for l in src["links"]:
            l["status"] = link_ok(l["url"])
            time.sleep(0.5)
        src["links_checked"] = now.strftime("%Y-%m-%dT%H:%MZ")
        bad = [l["url"] for l in src["links"] if l["status"] != 200]
        print(f"Checked {len(src['links'])} interview links; {len(bad)} not OK: {bad}")
    text = json.dumps(src, indent=1, ensure_ascii=False) + "\n"
    if not INTERVIEW_OUT.exists() or INTERVIEW_OUT.read_text() != text:
        INTERVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
        INTERVIEW_OUT.write_text(text)


def write_if_changed(path, obj):
    text = json.dumps(obj, indent=1, ensure_ascii=False) + "\n"
    if not path.exists() or path.read_text() != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return True
    return False


def build_rules():
    if RULES_SRC.exists():
        write_if_changed(RULES_OUT, json.loads(RULES_SRC.read_text()))


def build_news():
    """NZ immigration headlines from Google News RSS, refreshed at most hourly."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    prev = {}
    if NEWS_OUT.exists():
        try:
            prev = json.loads(NEWS_OUT.read_text())
        except ValueError:
            prev = {}
    now = datetime.now(timezone.utc)
    last = prev.get("fetched")
    if last and now - datetime.fromisoformat(last.replace("Z", "+00:00")) < timedelta(minutes=NEWS_MINUTES):
        return
    items = {}
    for q in NEWS_QUERIES:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:60d", "hl": "en-NZ", "gl": "NZ", "ceid": "NZ:en"})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                root = ET.fromstring(r.read())
        except Exception as e:
            print(f"news feed failed for {q}: {e}", file=sys.stderr)
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            source = (it.findtext("source") or "").strip()
            if source and title.endswith(" - " + source):
                title = title[: -len(source) - 3]
            if source.lower() in NEWS_BLOCKED_SOURCES:
                continue
            if not NEWS_RELEVANT.search(title) or NEWS_IRRELEVANT.search(title):
                continue
            try:
                when = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
            except Exception:
                continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())[:80]
            if key not in items:
                items[key] = {"date": when.strftime("%Y-%m-%d"), "title": title,
                              "source": source, "url": it.findtext("link") or ""}
        time.sleep(1)
    if not items:
        return  # keep the old feed rather than blanking it
    news = sorted(items.values(), key=lambda n: n["date"], reverse=True)[:40]
    old = [(n["title"], n["date"]) for n in prev.get("items", [])]
    if old == [(n["title"], n["date"]) for n in news]:
        return  # same headlines: do not touch the file, so nothing is committed
    write_if_changed(NEWS_OUT, {"fetched": now.strftime("%Y-%m-%dT%H:%MZ"), "items": news})
    print(f"News: {len(news)} headlines")


def main():
    build_interview()
    build_rules()
    build_news()
    cfg = json.loads(CONFIG.read_text())
    reg = load_register()
    aliases = cfg.get("employer_aliases", {})
    cat_patterns = {c: re.compile(p, re.I) for c, p in cfg["categories"].items()}
    title_ok = re.compile(cfg["title_must_match"], re.I)
    title_bad = re.compile(cfg["exclude_title"], re.I)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg["max_age_days"])

    previous = {}
    if OUT.exists():
        try:
            for j in json.loads(OUT.read_text()).get("jobs", []):
                previous[j["id"]] = j
        except (ValueError, KeyError):
            pass

    jobs = {}
    failures = 0
    for q in cfg["queries"]:
        for page in range(1, cfg["pages_per_query"] + 1):
            params = {
                "siteKey": "NZ-Main", "where": "All New Zealand", "locale": "en-NZ",
                "keywords": q["keywords"], "sortmode": "ListedDate",
                "page": page, "pageSize": cfg["page_size"],
            }
            if not q.get("any_classification"):
                params["classification"] = cfg["ict_classification"]
            try:
                data = fetch(params)
            except Exception as e:
                failures += 1
                print(f"FAILED {q['keywords']} p{page}: {e}", file=sys.stderr)
                break
            items = data.get("data", [])
            q_title = re.compile(q["title_regex"], re.I) if q.get("title_regex") else None
            for it in items:
                if it.get("displayType") == "promoted":
                    continue  # paid placements ignore the sort and keywords
                title = it.get("title", "")
                if not title_ok.search(title) or title_bad.search(title):
                    continue
                if q_title and not q_title.search(title):
                    continue
                listed = it.get("listingDate", "")
                try:
                    if datetime.fromisoformat(listed.replace("Z", "+00:00")) < cutoff:
                        continue
                except ValueError:
                    pass
                jid = str(it["id"])
                text = " ".join([title, it.get("teaser", "")] + (it.get("bulletPoints") or []))
                j = jobs.get(jid)
                if j is None:
                    company = it.get("companyName") or (it.get("advertiser") or {}).get("description", "")
                    status, reg_name = register_status(company, reg, aliases)
                    locs = it.get("locations") or [{}]
                    cats = {c for c, p in cat_patterns.items() if p.search(text)}
                    j = jobs[jid] = {
                        "id": jid,
                        "title": title,
                        "company": company,
                        "location": locs[0].get("label", ""),
                        "work_type": ", ".join(it.get("workTypes") or []),
                        "arrangement": (it.get("workArrangements") or {}).get("displayText", ""),
                        "salary": it.get("salaryLabel", ""),
                        "listed": listed,
                        "teaser": it.get("teaser", ""),
                        "classification": " / ".join(
                            x.get("description", "") for c in (it.get("classifications") or [])[:1]
                            for x in (c.get("classification", {}), c.get("subclassification", {}))),
                        "bullets": it.get("bulletPoints") or [],
                        "categories": sorted(cats),
                        "inz": status,
                        "inz_name": reg_name,
                        "visa_mention": False,
                        "visa_negative": bool(NEGATIVE_VISA.search(text)),
                        "url": f"https://www.seek.co.nz/job/{jid}",
                    }
                # Seek's keyword match is loose, so trust the ad's own text first and
                # only fall back to the query's category when the text says nothing.
                if q.get("category"):
                    j.setdefault("_query_cats", set()).add(q["category"])
                if q.get("visa_signal"):
                    j["visa_mention"] = True
            if len(items) < cfg["page_size"]:
                break
            time.sleep(1)  # be polite

    total_queries = sum(1 for _ in cfg["queries"])
    if failures >= total_queries:
        print("Every query failed; keeping the previous jobs.json", file=sys.stderr)
        sys.exit(1)

    for jid, j in jobs.items():
        j["first_seen"] = previous.get(jid, {}).get("first_seen") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        qc = j.pop("_query_cats", set())
        if not j["categories"]:
            j["categories"] = sorted(qc) or ["other"]

    ordered = sorted(jobs.values(), key=lambda j: j["listed"], reverse=True)
    old_ids = set(previous)
    new_ids = set(jobs)
    if old_ids == new_ids and OUT.exists():
        print(f"No change ({len(jobs)} jobs).")
        return

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "count": len(ordered),
        "added": sorted(new_ids - old_ids),
        "removed": len(old_ids - new_ids),
        "jobs": ordered,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(ordered)} jobs: {len(new_ids - old_ids)} new, {len(old_ids - new_ids)} gone.")


if __name__ == "__main__":
    main()
