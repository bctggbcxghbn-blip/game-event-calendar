#!/usr/bin/env python3
"""Idempotent, narrow import of the verified NTE V1.4 Hunter Pass."""
import argparse
import json
from pathlib import Path

EVENT_ID = "nte-hunter-pass-v14-20260930"
NAME = "Ver.1.4 ハンター褒章"
SOURCE = "https://nte.perfectworld.com/jp/article/news/gamenews/20260929/264412.html"

def import_event(events):
    if not isinstance(events, list):
        raise ValueError("events.json must be an array")
    for event in events:
        if not isinstance(event, dict):
            continue
        name = str(event.get("name", ""))
        if event.get("id") == EVENT_ID or (event.get("game") == "nte" and ("ハンター褒章" in name or "hunter pass" in name.lower())):
            return events, False
    result = list(events)
    result.append({
        "id": EVENT_ID, "game": "nte", "name": NAME,
        "start": "2026-09-30", "end": "2026-11-11", "kind": "イベント",
        "source_status": "NTE公式Ver.1.4", "official_url": SOURCE,
        "start_label": "Ver.1.4アップデート後", "end_time": "00:59", "time_zone": "JST",
        "start_note": "正確な開始時刻は未発表",
        "end_note": "公式表記11月10日24:59 = 11月11日00:59 JST"
    })
    return result, True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="events.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = Path(args.events)
    original = path.read_text(encoding="utf-8")
    events, changed = import_event(json.loads(original))
    print("ADD" if changed else "SKIP: already registered")
    if changed and args.apply:
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Updated", path)
    elif changed:
        print("Dry run: pass --apply to write")

if __name__ == "__main__":
    main()
