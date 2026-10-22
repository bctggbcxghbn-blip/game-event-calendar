#!/usr/bin/env python3
"""Read-only probe of Endfield's public news API tab identifiers."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HOST = "https://web-news.gryphline.com/api/bulletin"
APP_CODE = "arknights_endfield_official"
OUT = ".reports/endfield-v86/report.json"


def fetch(tabs, page=1, page_size=10):
    pairs = [
        ("lang", "ja-jp"), ("code", APP_CODE), ("page", str(page)),
        ("pageSize", str(page_size)),
    ]
    pairs.extend(("tabs[]", str(tab)) for tab in tabs)
    url = HOST + "?" + urllib.parse.urlencode(pairs)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            raw = resp.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read(20000).decode("utf-8", "replace")
    except Exception as e:
        return {"tabs": tabs, "status": None, "error": str(e)[:300]}
    try:
        data = json.loads(raw)
    except Exception:
        return {"tabs": tabs, "status": status, "error": "non_json", "preview": raw[:300]}
    payload = data.get("data") if isinstance(data, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    items = payload.get("list") if isinstance(payload.get("list"), list) else []
    sample = []
    for item in items[:2]:
        if isinstance(item, dict):
            sample.append({k: item.get(k) for k in item.keys() if any(s in k.lower() for s in ("title", "name", "time", "date", "id", "url", "type", "tab"))})
    return {
        "tabs": tabs, "status": status, "api_code": data.get("code") if isinstance(data, dict) else None,
        "message": data.get("msg") if isinstance(data, dict) else None,
        "total": payload.get("total"), "current": payload.get("current"),
        "pageSize": payload.get("pageSize"), "list_count": len(items),
        "item_keys": sorted(items[0].keys()) if items and isinstance(items[0], dict) else [],
        "sample_items": sample,
    }


def main():
    cases = [[]] + [[i] for i in range(0, 16)] + [[0, 1], [1, 2], [2, 3], [0, 1, 2, 3, 4, 5, 6, 7]]
    results = []
    for tabs in cases:
        results.append(fetch(tabs))
        time.sleep(0.15)
    report = {
        "version": 86, "mode": "read_only", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": HOST, "app_code": APP_CODE, "probe_count": len(results), "probes": results,
        "nonempty_cases": [r for r in results if r.get("list_count", 0) > 0],
        "warning": "Public GET diagnostics only. No calendar or event data was changed. A non-empty response must be reviewed before importing.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"V86 diagnostic complete: {len(results)} read-only probes -> {OUT}")

if __name__ == "__main__":
    main()
