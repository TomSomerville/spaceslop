#!/usr/bin/env python3
"""Find freely licensed images for an article. Standard library only.

  python3 scripts/find_image.py "Vulcan Centaur rocket"
  python3 scripts/find_image.py "Starship Starbase" --limit 8

Searches Wikimedia Commons (public domain, CC0, CC BY, CC BY-SA only) and NASA's
image library (NASA-created media is public domain). Prints JSON candidates with
everything an article's `image:` front matter needs: path, credit, license,
source_url. Anything non-commercial (NC) or no-derivatives (ND) is filtered out.
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request

UA = "SpaceSlopBot/1.0 (+https://spaceslop.beached.lol)"
TIMEOUT = 20
ALLOWED = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by(-sa)?[ -]?\d)", re.I)
BLOCKED = re.compile(r"\b(nc|nd)\b|non-?commercial|no ?deriv|fair use", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def strip(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def commons(query, limit):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": limit * 3,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1280,
    }
    data = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    out = []
    for page in sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = strip(meta.get("LicenseShortName", {}).get("value", ""))
        if not lic or BLOCKED.search(lic) or not ALLOWED.search(lic):
            continue
        if info.get("width", 0) < 800:
            continue
        artist = strip(meta.get("Artist", {}).get("value", "")) or "Unknown"
        out.append({
            "path": (info.get("thumburl") or info.get("url") or "").split("?")[0],
            "credit": f"{artist[:120]} / Wikimedia Commons",
            "license": lic,
            "source_url": info.get("descriptionurl"),
            "title": page.get("title", "").replace("File:", ""),
            "description": strip(meta.get("ImageDescription", {}).get("value", ""))[:300],
        })
        if len(out) >= limit:
            break
    return out


def nasa(query, limit):
    data = get("https://images-api.nasa.gov/search?" + urllib.parse.urlencode({"q": query, "media_type": "image"}))
    out = []
    for item in data.get("collection", {}).get("items", []):
        d = (item.get("data") or [{}])[0]
        credit = str(d.get("photographer") or d.get("secondary_creator") or d.get("center") or "NASA")
        # Only NASA-made media is public domain. NASA's library also hosts photos made by
        # companies and other agencies (credited e.g. "Axiom Space" or "SpaceX"); skip any
        # item whose credit names someone other than NASA or a NASA center.
        credit_wo_nasa = re.sub(r"\b(nasa|jsc|ksc|msfc|gsfc|jpl|arc|grc|lrc|afrc|ssc|wff)\b|[/,&\s]|johnson|kennedy|marshall|goddard|glenn|langley|ames|armstrong|stennis|space center|flight center|research center", "", credit, flags=re.I)
        if credit_wo_nasa and not re.fullmatch(r"[A-Z][a-z]+[A-Z][a-z]+|[A-Za-z.\- ]+", credit_wo_nasa):
            continue
        if re.search(r"spacex|boeing|blue origin|axiom|lockheed|northrop|sierra|esa\b|jaxa|roscosmos|getty|ap photo|reuters|afp|courtesy", credit, re.I):
            continue
        nasa_id = d.get("nasa_id")
        if not nasa_id:
            continue
        thumb = next((l.get("href") for l in item.get("links", []) if l.get("rel") == "preview"), None)
        if not thumb:
            continue
        out.append({
            "path": thumb.replace("~thumb", "~large"),
            "credit": f"{credit} / NASA" if "nasa" not in str(credit).lower() else str(credit),
            "license": "Public domain (NASA)",
            "source_url": f"https://images.nasa.gov/details/{urllib.parse.quote(nasa_id)}",
            "title": d.get("title", ""),
            "description": strip(d.get("description", ""))[:300],
            "date": (d.get("date_created") or "")[:10],
        })
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    results = {}
    for name, fn in (("commons", commons), ("nasa", nasa)):
        try:
            results[name] = fn(a.query, a.limit)
        except Exception as e:  # one source failing is fine
            results[name] = {"error": f"{type(e).__name__}: {e}"}
    json.dump(results, sys.stdout, indent=1, ensure_ascii=False)
    print()
