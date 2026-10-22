#!/usr/bin/env python3
"""Read-only probe for the Endfield public news API tabs array parameter."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOST = "https://web-news.gryphline.com"
APP_CODE = "arknights_endfield_official"
OUT = Path(os.environ.get("ENDFIELD_V85_REPORT", ".reports/endfield-v85/report.json"))
BASE = {"lang": "ja-jp", "code": APP_CODE, "page": "1", "pageSize": "20"}

# Try common query encodings for an array. GET only; do not modify any data.
CASES = [
    ("tabs_brackets_empty", [("tabs[]", "")]),
    ("tabs_brackets_zero", [("tabs[]", "0")]),
    ("tabs_index_zero", [("tabs[0]", "0")]),
    ("tabs_repeated_zero_one", [("tabs", "0"), ("tabs", "1")]),
    ("tabs_json_array", [("tabs", '["0"]')]),
    ("tabs_json_array_one", [("tabs", '[1]')]),
    ("tabs_comma_list", [("tabs", "0,1")]),
]

def probe(case: str, tab_params: list[tuple[str, str]]) -> dict:
    params = list(BASE.items()) + tab_params
    url = HOST + "/api/bulletin?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "EndfieldCalendarDiagnostic/85"}, method="GET")
    row = {"case": case, "url": url}
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(30000)
            row.update(status=resp.status, content_type=resp.headers.get("Content-Type"), error=None)
    except urllib.error.HTTPError as exc:
        raw = exc.read(30000)
        row.update(status=exc.code, content_type=exc.headers.get("Content-Type"), error="http_error")
    except Exception as exc:  # diagnostics should continue after an individual failure
        raw = b""
        row.update(status=None, content_type=None, error=type(exc).__name__ + ": " + str(exc)[:240])
    text = raw.decode("utf-8", "replace")
    try:
        payload = json.loads(text) if text else None
    except json.JSONDecodeError:
        payload = None
    row["json"] = payload
    row["body_preview"] = text[:1200]
    if isinstance(payload, dict):
        row["top_level_keys"] = list(payload.keys())[:40]
        # Report only likely list metadata, avoiding an oversized artifact.
        for key in ("data", "list", "items", "results", "total", "page", "pageSize"):
            if key in payload:
                val = payload[key]
                if isinstance(val, list):
                    row[key + "_count"] = len(val)
                    if val and isinstance(val[0], dict):
                        row[key + "_first_item_keys"] = list(val[0].keys())[:40]
                elif not isinstance(val, (dict, list)):
                    row[key] = val
    return row

def main() -> int:
    rows = [probe(name, params) for name, params in CASES]
    successes = [r for r in rows if r.get("status") == 200 and r.get("error") is None]
    report = {
        "version": 85,
        "mode": "read_only",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "app_code": APP_CODE,
        "probe_count": len(rows),
        "probes": rows,
        "successful_cases": [r["case"] for r in successes],
        "json_endpoint_success": bool(successes),
        "event_modifications": 0,
        "warning": "Public GET diagnostics only. No event data was added or changed; a 200 response still needs schema review before importing articles."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"version": 85, "report": str(OUT), "probe_count": len(rows), "successful_cases": report["successful_cases"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
