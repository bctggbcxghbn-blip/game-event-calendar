#!/usr/bin/env python3
"""V61 NTE official article extraction preview. Read-only; never writes events.json."""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
URL = "https://nte.perfectworld.com/jp/article/news/gamenews/20260929/264412.html"
DATE = re.compile(r"(20\\d{2})[年/.-]\\s*(\\d{1,2})[月/.-]\\s*(\\d{1,2})日?\\s*(?:(\\d{1,2}):([0-5]\\d))?")
RANGE = re.compile(r"(?:～|〜|~|－|—|–|から|至)")
GACHA = re.compile(r"ガチャ|召集|募集|ピックアップ|弧盤|キャラ|復刻|限定")
EVENT = re.compile(r"イベント|ログイン|報酬|遊園祭|昇段戦|秘宝|オーバーフロー")
TIMEZONE = re.compile(r"サーバー時間|日本時間|JST|UTC[+-]\\d+", re.I)

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
        self.block = {"p","div","li","h1","h2","h3","h4","tr","td","br"}
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"):
            self.skip += 1
        if tag in self.block:
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript") and self.skip:
            self.skip -= 1
        if tag in self.block:
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
    def lines(self):
        return [" ".join(line.split()) for line in "".join(self.parts).splitlines() if line.strip()]

def extract(html, url=URL):
    parser = TextParser()
    parser.feed(html)
    lines = parser.lines()
    records = []
    seen = set()
    for index, line in enumerate(lines):
        if not (GACHA.search(line) or EVENT.search(line)):
            continue
        context = " ".join(lines[max(0,index-1):min(len(lines),index+3)])
        dates = []
        for match in DATE.finditer(context):
            y, m, d, h, minute = match.groups()
            try:
                dt = datetime(int(y),int(m),int(d),int(h or 0),int(minute or 0))
            except ValueError:
                continue
            dates.append({"date": dt.strftime("%Y-%m-%d"), "time": f"{h.zfill(2)}:{minute}" if h else None,
                          "precision": "minute" if h else "date"})
        # A nearby date is not automatically assigned to an event: context is only evidence.
        kind = "gacha_candidate" if GACHA.search(line) else "event_candidate"
        key = (kind,line)
        if key in seen:
            continue
        seen.add(key)
        records.append({"kind":kind,"source_text":line[:250],"nearby_dates":dates[:4],
                        "has_range_marker":bool(RANGE.search(context)),
                        "timezone_evidence":list(dict.fromkeys(TIMEZONE.findall(context))),
                        "status":"review_required"})
    return {"status":"ok","source_url":url,"candidate_count":len(records),
            "candidates":records,"auto_imported":0,
            "note":"Context dates are evidence only; do not assume they belong to a candidate."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--html-file",type=Path)
    ap.add_argument("--url",default=URL)
    ap.add_argument("--report",type=Path,default=ROOT/".reports/nte-v61/report.json")
    ap.add_argument("--strict",action="store_true")
    args=ap.parse_args()
    try:
        if args.html_file:
            html=args.html_file.read_text(encoding="utf-8")
        else:
            req=Request(args.url,headers={"User-Agent":"Mozilla/5.0 (compatible; calendar NTE V61 preview)"})
            with urlopen(req,timeout=15) as response:
                html=response.read(3_000_000).decode("utf-8",errors="replace")
        report=extract(html,args.url)
    except Exception as e:
        report={"status":"fetch_error","source_url":args.url,"error":str(e),"candidates":[],"auto_imported":0}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"NTE V61 ARTICLE PREVIEW status={report['status']} candidates={len(report['candidates'])} auto_imported=0")
    print(f"REPORT: {args.report}")
    if report["status"]!="ok" and args.strict:
        raise SystemExit(1)

if __name__=="__main__":
    main()
