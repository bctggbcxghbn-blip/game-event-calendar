#!/usr/bin/env python3
"""NTE V60: import only explicitly dated events from the latest JP update notice."""
import argparse, html as html_lib, json, re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
INDEX = "https://nte.perfectworld.com/jp/article/news/gamenews/index.html"
BASE = "https://nte.perfectworld.com"
ARTICLE_RE = re.compile(r"^/jp/article/news/gamenews/\d{8}/\d+\.html$")
VERSION_RE = re.compile(r"Ver\.?\s*(\d+(?:\.\d+)+)")
DATE_RE = re.compile(r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日(?:\s*[^-–—]*)\s*[-–—]\s*(?:(?P<end_month>\d{1,2})月)?(?P<end_day>\d{1,2})日")

class LinkParser(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.href=None; self.text=[]
    def handle_starttag(self, tag, attrs):
        if tag == "a": self.href=dict(attrs).get("href"); self.text=[]
    def handle_data(self, data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(" ".join(self.text).split())))
            self.href=None; self.text=[]

def discover_versions(index_html):
    p=LinkParser(); p.feed(index_html); found={}
    for href,title in p.links:
        url=urljoin(INDEX,href); path=urlparse(url).path; m=VERSION_RE.search(title)
        if urlparse(url).netloc != "nte.perfectworld.com" or not ARTICLE_RE.fullmatch(path) or not m or "アップデート" not in title: continue
        found[url]={"url":url,"version":m.group(1),"title":title}
    return sorted(found.values(), key=lambda x: tuple(map(int,x["version"].split("."))), reverse=True)

def plain_text(source):
    p=HTMLParser(); out=[]
    p.handle_data=lambda data: out.append(data)
    p.feed(source)
    return html_lib.unescape("\n".join(out))

def dated_events(source, url, version, year):
    text=plain_text(source); out=[]
    # Only lines with an explicit event period are eligible; update-relative dates are anchored
    # to the explicit maintenance date in the same official notice.
    for m in re.finditer(r"(?:期間|開催期間|開放期間)[：:]\s*([^\n]{0,100})", text):
        clause=m.group(1); dm=DATE_RE.search(clause)
        if not dm: continue
        start_month=int(dm.group("month")); end_month=int(dm.group("end_month") or start_month); end_day=int(dm.group("end_day"))
        start_day=int(dm.group("day")); start=f"{year:04d}-{start_month:02d}-{start_day:02d}"; end=f"{year:04d}-{end_month:02d}-{end_day:02d}"
        try: date.fromisoformat(start); date.fromisoformat(end)
        except ValueError: continue
        prefix=text[max(0,m.start()-180):m.start()]
        names=re.findall(r"[「『]([^」』]{2,40})[」』]", prefix)
        if not names: continue
        name=names[-1].strip()
        if name in {"イベント期間","開催期間","開放期間"}: continue
        slug=re.sub(r"[^0-9A-Za-z一-龯ぁ-んァ-ヶ]+","-",name).strip("-")[:60]
        out.append({"id":f"nte-official-v{version.replace('.','-')}-{slug}","game":"nte","name":name,"kind":"イベント","start":start,"end":end,"source_status":f"NTE公式Ver.{version}","official_url":url})
    unique={x["id"]:x for x in out}; return list(unique.values())

def merge(existing,incoming):
    if not isinstance(existing,list): raise ValueError("events.json must be a list")
    ids={x["id"] for x in incoming}; return sorted([x for x in existing if x.get("id") not in ids]+incoming,key=lambda x:(x.get("start",""),x.get("game",""),x.get("id","")))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); ap.add_argument("--path",type=Path,default=ROOT/"events.json"); ap.add_argument("--index-file",type=Path); ap.add_argument("--article-file",type=Path); args=ap.parse_args()
    index=args.index_file.read_text(encoding="utf-8") if args.index_file else urlopen(Request(INDEX,headers={"User-Agent":"GameEventCalendar/1.0"}),timeout=15).read().decode("utf-8","replace")
    versions=discover_versions(index)
    if not versions: print("NTE V60: no official version notice found; no changes"); return 0
    latest=versions[0]; article=args.article_file.read_text(encoding="utf-8") if args.article_file else urlopen(Request(latest["url"],headers={"User-Agent":"GameEventCalendar/1.0"}),timeout=15).read().decode("utf-8","replace")
    year=int(re.search(r"(20\d{2})",latest["url"]).group(1)); incoming=dated_events(article,latest["url"],latest["version"],year); data=json.loads(args.path.read_text(encoding="utf-8")); result=merge(data,incoming)
    print(f"NTE V60: Ver.{latest['version']} dated_events={len(incoming)} total={len(data)}->{len(result)}")
    if args.apply and result!=data: args.path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print("APPLIED")
    return 0
if __name__ == "__main__": raise SystemExit(main())
