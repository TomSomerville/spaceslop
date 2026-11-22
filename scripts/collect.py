#!/usr/bin/env python3
"""SpaceSlop collector. Standard library only, so it runs anywhere with Python 3.9+.

Pulls RSS/Atom feeds, the Spaceflight News API and Launch Library 2, drops anything
already seen or too old, and writes:
  data/candidates.json  new items for the newsroom to consider (not committed)
  data/launches.json    upcoming and recent launches, for context (not committed)

  python scripts/collect.py              collect new candidates
  python scripts/collect.py --hours 48   look back further
  python scripts/collect.py --mark-seen  after a run: mark every current candidate as seen
  python scripts/collect.py --mark-seen --retry ID ...   ...except these (no source could
                                         be read); they are offered again on later runs
"""
import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
DATA = ROOT / "data"
SOURCES = ROOT / "scripts" / "sources.json"
SEEN = DATA / "seen.json"
CANDIDATES = DATA / "candidates.json"
LAUNCHES = DATA / "launches.json"
PUBLIC_LAUNCHES = ROOT / "assets" / "launches.json"

UA = "SpaceSlopBot/1.0 (+https://spaceslop.beached.lol)"
TIMEOUT = 20
SEEN_KEEP_DAYS = 21
# Stories skipped only because no source could be read are retried on later runs
# (see --retry), until they have been tried this many times or are this old.
RETRY = DATA / "retry.json"
RETRY_MAX_ATTEMPTS = 8
RETRY_MAX_HOURS = 48


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def clean(text, limit=700):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_feed(name, raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # Some feeds (e.g. The Space Review) declare UTF-8 but contain Windows-1252 bytes.
        # Decode leniently and parse the text instead of losing the whole feed.
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)
        root = ET.fromstring(text)
    items = []
    for el in root.iter():
        kind = local(el.tag)
        if kind == "item":  # RSS 2.0
            link = child_text(el, "link")
            items.append({
                "title": clean(child_text(el, "title"), 300),
                "url": link,
                "summary": clean(child_text(el, "encoded", "description")),
                "published": parse_date(child_text(el, "pubDate", "date")),
                "outlet": child_text(el, "source"),  # Google News names the real publisher here
            })
        elif kind == "entry":  # Atom
            link = ""
            for c in el:
                if local(c.tag) == "link" and c.get("rel", "alternate") == "alternate":
                    link = c.get("href", "")
                    break
            items.append({
                "title": clean(child_text(el, "title"), 300),
                "url": link,
                "summary": clean(child_text(el, "content", "summary")),
                "published": parse_date(child_text(el, "published", "updated")),
            })
    for i in items:
        outlet = i.pop("outlet", "")
        i["source"] = f"{outlet} (via Google News)" if outlet else name
        if outlet:
            # Google News titles end in " - Publisher"; the link is a Google redirect.
            i["title"] = re.sub(r"\s+-\s+[^-]+$", "", i["title"])
            i["needs_original_url"] = True
    return items


def get_rss(src):
    try:
        return src["name"], parse_feed(src["name"], fetch(src["url"])), None
    except Exception as e:  # one bad feed never stops the run
        return src["name"], [], f"{type(e).__name__}: {e}"


def get_snapi(url, cutoff, max_pages=10):
    """Page through the Spaceflight News API back to the lookback cutoff."""
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}published_at_gte={cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    results = []
    for _ in range(max_pages):
        data = json.loads(fetch(url))
        results += data.get("results", [])
        url = data.get("next")
        if not url:
            break
    out = []
    for a in results:
        out.append({
            "title": clean(a.get("title"), 300),
            "url": a.get("url", ""),
            "summary": clean(a.get("summary")),
            "published": parse_date(a.get("published_at")),
            "source": f"{a.get('news_site', 'Unknown')} (via SNAPI)",
        })
    return out


def get_launches(url):
    data = json.loads(fetch(url))
    out = []
    def name_of(d):
        return d.get("name") if isinstance(d, dict) else d

    for l in data.get("results", []):
        pad = l.get("pad") if isinstance(l.get("pad"), dict) else {}
        mission = l.get("mission") if isinstance(l.get("mission"), dict) else {}
        out.append({
            "name": l.get("name"),
            "net": l.get("net"),
            "status": name_of(l.get("status")),
            "provider": name_of(l.get("launch_service_provider")),
            "pad": pad.get("name"),
            "location": name_of(pad.get("location")),
            "mission": mission.get("description", "")[:400] or None,
        })
    return out


def key(item):
    u = (item.get("url") or "").split("?")[0].split("#")[0].rstrip("/").lower()
    basis = u or item.get("title", "").lower()
    return hashlib.sha1(basis.encode()).hexdigest()[:16]


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def mark_seen(retry_ids=()):
    """Mark this run's candidates seen, except those listed in retry_ids.

    retry_ids are candidates skipped only because no source could be read. They go to
    data/retry.json and come back as candidates on the next runs, until they have been
    tried RETRY_MAX_ATTEMPTS times or are RETRY_MAX_HOURS old; then they are marked seen.
    """
    seen = load_json(SEEN, {})
    retry = load_json(RETRY, {})
    cands = load_json(CANDIDATES, {}).get("items", [])
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    by_id = {c["id"]: c for c in cands}
    retry_ids = set(retry_ids)
    unknown = sorted(retry_ids - set(by_id))
    kept, gave_up, marked = 0, 0, 0
    for cid, c in by_id.items():
        if cid in retry_ids:
            entry = retry.get(cid) or {"first_kept": now, "attempts": 0}
            entry["attempts"] = entry.get("attempts", 0) + 1
            entry["last_tried"] = now
            entry["item"] = {k: v for k, v in c.items() if k not in ("retry_attempts",)}
            too_old = now_dt - datetime.fromisoformat(entry["first_kept"]) >= timedelta(hours=RETRY_MAX_HOURS)
            if entry["attempts"] >= RETRY_MAX_ATTEMPTS or too_old:
                seen[cid] = now
                retry.pop(cid, None)
                gave_up += 1
            else:
                retry[cid] = entry
                kept += 1
        else:
            seen[cid] = now
            retry.pop(cid, None)
            marked += 1
    # Anything already seen (published or rejected by another run) no longer needs a retry.
    retry = {k: v for k, v in retry.items() if k not in seen}
    cutoff = now_dt - timedelta(days=SEEN_KEEP_DAYS)
    seen = {k: v for k, v in seen.items() if datetime.fromisoformat(v) >= cutoff}
    save_json(SEEN, seen)
    save_json(RETRY, retry)
    print(f"Marked {marked} candidates as seen ({len(seen)} tracked). "
          f"Kept {kept} for retry, gave up on {gave_up} after too many tries ({len(retry)} waiting).")
    if unknown:
        print(f"WARNING: --retry ids not in data/candidates.json, ignored: {' '.join(unknown)}")


def collect(hours, dry_run=False):
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    seen = load_json(SEEN, {})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items, report = [], {}

    # Reddit throttles bursts, so its feeds go one at a time; everything else in parallel.
    feeds = cfg.get("rss", [])
    reddit = [f for f in feeds if "reddit.com" in f["url"]]
    others = [f for f in feeds if f not in reddit]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(get_rss, others))
    for f in reddit:
        results.append(get_rss(f))
        time.sleep(3)
    # Google News search feeds: one at a time so Google doesn't throttle us.
    for f in cfg.get("google_news", []):
        name, got, err = get_rss(f)
        got.sort(key=lambda i: i["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        for i in got:
            i["summary"] = ""  # Google's summary is just a list of links
        results.append((name, got[:60], err))
        time.sleep(1.5)
    for name, got, err in results:
        items += got
        report[name] = err or len(got)

    # Every company/agency on the watch list: one Google News search per small group of
    # names, plus a direct check of each official news page for new posts.
    companies = json.loads((ROOT / "scripts" / "companies.json").read_text(encoding="utf-8"))
    queries = [c["query"] for c in companies]
    for n in range(0, len(queries), 5):
        q = " OR ".join(f"({x})" for x in queries[n:n + 5]) + " when:2d"
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        label = "Google News · companies: " + ", ".join(c["name"] for c in companies[n:n + 5])
        name, got, err = get_rss({"name": label, "url": url})
        for i in got:
            i["summary"] = ""
        got.sort(key=lambda i: i["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        items += got[:60]
        report[label] = err or len(got)
        time.sleep(1.5)
    # Priority companies (see "priority" in companies.json): a dedicated Google News search
    # and a Spaceflight News API search every run, so they can never be crowded out.
    for c in [c for c in companies if c.get("priority")]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": c["query"] + " when:1d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        name, got, err = get_rss({"name": f"Google News · PRIORITY {c['name']}", "url": url})
        for i in got:
            i["summary"] = ""
            i["priority"] = c["name"]
        items += got
        report[name] = err or len(got)
        time.sleep(1.5)
        try:
            api = "https://api.spaceflightnewsapi.net/v4/articles/?" + urllib.parse.urlencode({"search": c["name"], "limit": 30, "ordering": "-published_at"})
            got = get_snapi(api, cutoff)
            for i in got:
                i["priority"] = c["name"]
            items += got
            report[f"Spaceflight News API · PRIORITY {c['name']}"] = len(got)
        except Exception as e:
            report[f"Spaceflight News API · PRIORITY {c['name']}"] = f"{type(e).__name__}: {e}"

    try:
        import newsrooms
        watched, nr_report = newsrooms.watch(update_state=not dry_run)
        items += watched
        report.update(nr_report)
    except Exception as e:
        report["Company newsrooms"] = f"{type(e).__name__}: {e}"

    for label, fn, url in [("Spaceflight News API", get_snapi, cfg.get("spaceflight_news_api"))]:
        if not url:
            continue
        try:
            got = fn(url, cutoff)
            items += got
            report[label] = len(got)
        except Exception as e:
            report[label] = f"{type(e).__name__}: {e}"

    launches = {}
    for label, url in [("upcoming", cfg.get("launch_library")), ("recent", cfg.get("launch_library_recent"))]:
        if not url:
            continue
        try:
            launches[label] = get_launches(url)
            report[f"Launch Library ({label})"] = len(launches[label])
        except Exception as e:
            report[f"Launch Library ({label})"] = f"{type(e).__name__}: {e}"
        time.sleep(1)

    fresh, ids = [], set()
    for i in items:
        if not i.get("title") or not i.get("url"):
            continue
        i["id"] = key(i)
        if i["id"] in seen or i["id"] in ids:
            continue
        if i["published"] and i["published"] < cutoff:
            continue
        ids.add(i["id"])
        i["published"] = i["published"].isoformat(timespec="minutes") if i["published"] else None
        fresh.append(i)
    # Stories an earlier run couldn't read a source for: offer them again even if they
    # have dropped out of the feeds or past the lookback window.
    retry = load_json(RETRY, {})
    for cid, entry in retry.items():
        if cid in seen or cid in ids or not entry.get("item"):
            continue
        item = dict(entry["item"])
        item["id"] = cid
        item["retry_attempts"] = entry.get("attempts", 0)
        ids.add(cid)
        fresh.append(item)
    fresh.sort(key=lambda i: i["published"] or "", reverse=True)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_json(CANDIDATES, {"collected_at": now, "lookback_hours": hours, "sources": report, "items": fresh})
    save_json(LAUNCHES, {"collected_at": now, **launches})
    # Public copy for the site's launch board (served from our own domain).
    if launches.get("upcoming"):
        board = [{k: l.get(k) for k in ("name", "net", "status", "provider", "location")} for l in launches["upcoming"]]
        save_json(PUBLIC_LAUNCHES, {"updated": now, "upcoming": board})

    print(f"{len(fresh)} new candidates from {len(items)} items (lookback {hours}h).")
    for name, r in report.items():
        bad = isinstance(r, str) and not re.match(r"^(baselined|\d+ \()", r)
        print(f"  {'FAIL' if bad else 'ok  '} {name}: {r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--mark-seen", action="store_true")
    ap.add_argument("--retry", nargs="*", default=[], metavar="ID",
                    help="with --mark-seen: candidate ids skipped only because no source could be read; "
                         "they are offered again on later runs instead of being marked seen")
    ap.add_argument("--dry-run", action="store_true", help="don't update newsroom baselines")
    a = ap.parse_args()
    if a.mark_seen:
        mark_seen(a.retry)
    else:
        collect(a.hours, a.dry_run)
