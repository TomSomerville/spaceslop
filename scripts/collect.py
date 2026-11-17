#!/usr/bin/env python3
"""SpaceSlop collector. Standard library only, so it runs anywhere with Python 3.9+.

Pulls RSS/Atom feeds, the Spaceflight News API and Launch Library 2, drops anything
already seen or too old, and writes:
  data/candidates.json  new items for the newsroom to consider (not committed)
  data/launches.json    upcoming and recent launches, for context (not committed)

  python scripts/collect.py              collect new candidates
  python scripts/collect.py --hours 48   look back further
  python scripts/collect.py --mark-seen  after a run: mark every current candidate as seen
"""
import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = ROOT / "scripts" / "sources.json"
SEEN = DATA / "seen.json"
CANDIDATES = DATA / "candidates.json"
LAUNCHES = DATA / "launches.json"
PUBLIC_LAUNCHES = ROOT / "assets" / "launches.json"

UA = "SpaceSlopBot/1.0 (+https://spaceslop.beached.lol)"
TIMEOUT = 20
SEEN_KEEP_DAYS = 21


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
    root = ET.fromstring(raw)
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


def mark_seen():
    seen = load_json(SEEN, {})
    cands = load_json(CANDIDATES, {}).get("items", [])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for c in cands:
        seen[c["id"]] = now
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_KEEP_DAYS)
    seen = {k: v for k, v in seen.items() if datetime.fromisoformat(v) >= cutoff}
    save_json(SEEN, seen)
    print(f"Marked {len(cands)} candidates as seen ({len(seen)} tracked).")


def collect(hours):
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
        results.append((name, got[:25], err))
        time.sleep(1.5)
    for name, got, err in results:
        items += got
        report[name] = err or len(got)

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
        print(f"  {'FAIL' if isinstance(r, str) else 'ok  '} {name}: {r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--mark-seen", action="store_true")
    a = ap.parse_args()
    if a.mark_seen:
        mark_seen()
    else:
        collect(a.hours)
