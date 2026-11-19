#!/usr/bin/env python3
"""Watch the official news pages in scripts/companies.json for new posts.

Used by collect.py. Standard library only.

The first time a page is seen, every post link on it is recorded as a baseline, so the
back catalog is not reported as news. After that, any link that wasn't there before is
returned as a candidate. A news URL may also be an official RSS/Atom feed (used for
companies whose own page needs JavaScript). State lives in data/newsroom_seen.json (committed by each run).

  python3 scripts/newsrooms.py --test    fetch every page and report how many post links
                                         were found, without changing any state
"""
import html
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = ROOT / "scripts" / "companies.json"
STATE = ROOT / "data" / "newsroom_seen.json"
UA = "Mozilla/5.0 (compatible; SpaceSlopBot/1.0; +https://spaceslop.beached.lol)"
TIMEOUT = 20
KEEP_PER_COMPANY = 400

SKIP_PATH = re.compile(
    r"/(tag|tags|category|categories|author|page|search|login|signin|careers|jobs|job|"
    r"privacy|terms|legal|cookie|contact|about|team|leadership|investors?/(?!news|press)|"
    r"wp-content|wp-json|feed|cdn-cgi)(/|$)|\.(pdf|jpe?g|png|gif|webp|svg|css|js|xml|zip|mp4)$",
    re.I,
)
ANCHOR = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.URLError as e:
        # Some sites ship incomplete certificate chains; the page is public, so retry
        # without verification rather than lose the source.
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            return r.read().decode("utf-8", "replace"), r.geturl()


def base_domain(host):
    parts = host.lower().split(".")
    if len(parts) > 2 and parts[-2] in ("co", "com", "org", "net", "gov", "ac"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def text_of(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def title_from_slug(path):
    slug = [s for s in path.split("/") if s][-1] if path.strip("/") else ""
    slug = re.sub(r"\.(html?|php|aspx?)$", "", slug)
    return slug.replace("-", " ").replace("_", " ").strip().capitalize()


def post_links(company, page_html, page_url):
    """Links on a news page that look like individual posts."""
    page = urllib.parse.urlparse(page_url)
    prefix = page.path.rstrip("/")
    if re.search(r"\.(html?|php)$", prefix):
        prefix = prefix.rsplit("/", 1)[0]
    domain = base_domain(page.hostname or "")
    out = {}
    for href, inner in ANCHOR.findall(page_html):
        url = urllib.parse.urljoin(page_url, html.unescape(href.strip()))
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname or base_domain(u.hostname) != domain:
            continue
        path = u.path.rstrip("/")
        if not path or path == prefix or SKIP_PATH.search(path):
            continue
        last = path.rsplit("/", 1)[-1]
        under_prefix = prefix and path.startswith(prefix + "/") and len(path) > len(prefix) + 4
        sluggy = last.count("-") >= 3 or re.search(r"\d{4,}", last)
        if not (under_prefix or sluggy):
            continue
        key = f"{u.hostname.lower().removeprefix('www.')}{path}".lower()
        title = text_of(inner)
        if len(title) < 15 or len(title) > 220 or title.lower() in ("read more", "learn more", "read article"):
            title = title_from_slug(path)
        if key not in out or len(title) > len(out[key]["title"]):
            out[key] = {"title": title[:300], "url": f"{u.scheme}://{u.netloc}{u.path}"}
    return out


NEWSY = re.compile(r"/(news|newsroom|press|press-releases?|updates?|blog|media|releases?|insights|stories|articles?|posts?|announcements?)(/|$)", re.I)


def sitemap_links(company):
    """Fallback for JavaScript-rendered pages: read post URLs from the site's sitemap."""
    page = urllib.parse.urlparse(company["news"])
    root = f"{page.scheme}://{page.netloc}"
    todo, seen, locs = [root + "/sitemap.xml", root + "/sitemap_index.xml"], set(), []
    while todo and len(seen) < 8:
        sm = todo.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            xml, _ = fetch(sm)
        except Exception:
            continue
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
            loc = html.unescape(loc)
            if loc.endswith(".xml"):
                # nested sitemap: follow only the ones that look like posts/news
                if re.search(r"post|news|press|update|blog|article|media|release", loc, re.I) or len(todo) < 2:
                    todo.append(loc)
            else:
                locs.append(loc)
    out = {}
    for url in locs:
        u = urllib.parse.urlparse(url)
        path = u.path.rstrip("/")
        last = path.rsplit("/", 1)[-1]
        if not NEWSY.search(path) or SKIP_PATH.search(path) or not (last.count("-") >= 2 or re.search(r"\d{4,}", last)):
            continue
        key = f"{(u.hostname or '').lower().removeprefix('www.')}{path}".lower()
        out[key] = {"title": title_from_slug(path), "url": f"{u.scheme}://{u.netloc}{u.path}"}
    return out


FEED_ITEM = re.compile(r"<(item|entry)\b.*?</\1>", re.I | re.S)


def feed_links(xml, base):
    """Post links from an RSS/Atom feed (for companies whose official news is only a feed)."""
    out = {}
    for m in FEED_ITEM.finditer(xml):
        block = m.group(0)
        link = re.search(r"<link[^>]*href=[\"']([^\"']+)[\"']", block, re.I) or re.search(r"<link>\s*(?:<!\[CDATA\[)?\s*([^<\s\]]+)", block, re.I)
        if not link:
            continue
        url = urllib.parse.urljoin(base, html.unescape(link.group(1).strip()))
        title = re.search(r"<title[^>]*>(.*?)</title>", block, re.I | re.S)
        title = text_of(re.sub(r"<!\[CDATA\[|\]\]>", "", title.group(1))) if title else ""
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            continue
        key = f"{u.hostname.lower().removeprefix('www.')}{u.path.rstrip('/')}{('?' + u.query) if u.query else ''}".lower()
        out[key] = {"title": (title or title_from_slug(u.path))[:300], "url": url}
    return out


def check(company):
    err = None
    try:
        page_html, final_url = fetch(company["news"])
        head = page_html[:600].lower()
        if "<rss" in head or "<feed" in head or "<rdf:rdf" in head:
            links = feed_links(page_html, final_url)
        else:
            links = post_links(company, page_html, final_url)
        if links:
            return company, links, None
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:120]}"
    try:
        links = sitemap_links(company)
        if links:
            return company, links, None
    except Exception:
        pass
    return company, {}, err


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def watch(update_state=True):
    """Return (new_items, report). New items are only reported for already-baselined pages."""
    companies = json.loads(COMPANIES.read_text(encoding="utf-8"))
    state = load_state()
    items, report = [], {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for company, links, err in pool.map(check, companies):
            name = company["name"]
            if err:
                report[f"{name} newsroom"] = err
                continue
            if not links:
                report[f"{name} newsroom"] = "no post links found (page may need JavaScript)"
                continue
            known = state.get(name)
            if known is None:
                report[f"{name} newsroom"] = f"baselined {len(links)} existing posts"
                known = []
                fresh = []
            else:
                known_set = set(known)
                fresh = [k for k in links if k not in known_set]
                report[f"{name} newsroom"] = len(links) if not fresh else f"{len(links)} ({len(fresh)} new)"
            for k in fresh:
                items.append({
                    "title": links[k]["title"],
                    "url": links[k]["url"],
                    "summary": f"New post on {name}'s official news page ({company['does']}).",
                    "published": None,
                    "source": f"{name} newsroom",
                    "company": name,
                })
            state[name] = (list(links.keys()) + [k for k in (known or []) if k not in links])[:KEEP_PER_COMPANY]
    if update_state:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return items, report


if __name__ == "__main__" and "--test" in sys.argv:
    companies = json.loads(COMPANIES.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, companies))
    ok = 0
    for company, links, err in results:
        status = err or (f"{len(links)} post links" if links else "NO post links found")
        if links and not err:
            ok += 1
        sample = next(iter(links.values()))["title"][:60] if links else ""
        print(f"{'ok  ' if links and not err else 'FAIL'} {company['name'][:26]:26} {status[:70]:70} {sample}")
    print(f"\n{ok}/{len(companies)} newsroom pages readable")
