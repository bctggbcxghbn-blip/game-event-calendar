#!/usr/bin/env python3
"""V60: Discover NTE official update announcements; review only, no event writes."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
INDEX = "https://nte.perfectworld.com/jp/article/news/gamenews/index.html"
BASE = "https://nte.perfectworld.com"
ARTICLE = re.compile(r"^/jp/article/news/gamenews/\d{8}/\d+\.html$")
VERSION = re.compile(r"Ver\.?\s*(\d+(?:\.\d+)+)", re.I)
KNOWN = "https://nte.perfectworld.com/jp/article/news/gamenews/20260929/264412.html"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []
    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(" ".join(self.text).split())))
            self.href = None
            self.text = []

def discover(html):
    parser = LinkParser()
    parser.feed(html)
    found = {}
    for href, title in parser.links:
        url = urljoin(INDEX, href)
        parsed = urlparse(url)
        if parsed.netloc != "nte.perfectworld.com" or not ARTICLE.fullmatch(parsed.path):
            continue
        version = VERSION.search(title)
        if not version or "アップデート" not in title:
            continue
        found[url] = {"version": version.group(1), "title": title, "url": url}
    return sorted(found.values(), key=lambda x: (tuple(map(int, x["version"].split("."))), x["url"]), reverse=True)

def build_report(html, known_urls):
    articles = discover(html)
    return {"status": "ok", "source": INDEX, "known_urls": sorted(known_urls),
            "candidates": [a for a in articles if a["url"] not in known_urls],
            "found": articles, "auto_imported": 0,
            "note": "Review candidates manually; dates and names are not auto-inferred."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--html-file", type=Path, help="Offline HTML input")
    p.add_argument("--report", type=Path, default=ROOT/".reports/nte-v60/report.json")
    p.add_argument("--strict", action="store_true", help="Fail on fetch errors")
    args = p.parse_args()
    try:
        if args.html_file:
            html = args.html_file.read_text(encoding="utf-8")
        else:
            req = Request(INDEX, headers={"User-Agent": "GameEventCalendar/1.0 (+read-only NTE update discovery)"})
            with urlopen(req, timeout=15) as response:
                html = response.read(2_000_000).decode("utf-8", errors="replace")
        known = {KNOWN}
        events = ROOT/"events.json"
        if events.exists():
            data = json.loads(events.read_text(encoding="utf-8"))
            known.update(e["official_url"] for e in data if e.get("game") == "nte" and e.get("official_url"))
        report = build_report(html, known)
    except Exception as exc:
        report = {"status": "fetch_error", "error": str(exc), "source": INDEX, "candidates": [], "auto_imported": 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"NTE V60 DISCOVERY status={report['status']} candidates={len(report['candidates'])} auto_imported=0")
    for a in report["candidates"]:
        print(f"REVIEW Ver.{a['version']}: {a['title']} {a['url']}")
    print(f"REPORT: {args.report}")
    if report["status"] != "ok" and args.strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
