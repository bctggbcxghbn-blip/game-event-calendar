#!/usr/bin/env python3
"""Read-only pagination and title inventory for Endfield's public news API."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HOST = "https://web-news.gryphline.com/api/bulletin"
APP_CODE = "arknights_endfield_official"
OUT = ".reports/endfield-v87/report.json"
KEYWORDS = ("活动", "限时", "开放", "开启", "结束", "招募", "寻访", "卡池", "签到", "危机合同", "危机契约", "商店", "兑换", "版本", "更新", "丹青渡", "武库", "天河", "帰野", "ミンホ", "イベント", "ガチャ", "作戦")


def request_page(page=1, page_size=50):
    pairs = [("lang", "ja-jp"), ("code", APP_CODE), ("page", str(page)), ("pageSize", str(page_size))]
    # An empty tabs[] is the verified all-categories request shape.
    url = HOST + "?" + urllib.parse.urlencode(pairs)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            status, raw = resp.status, resp.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read(30000).decode("utf-8", "replace")
    except Exception as e:
        return {"page": page, "page_size_requested": page_size, "status": None, "error": str(e)[:300], "items": []}
    try:
        data = json.loads(raw)
    except Exception:
        return {"page": page, "page_size_requested": page_size, "status": status, "error": "non_json", "preview": raw[:300], "items": []}
    payload = data.get("data") if isinstance(data, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    rows = payload.get("list") if isinstance(payload.get("list"), list) else []
    items = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        items.append({
            "cid": str(row.get("cid", "")),
            "title": row.get("title", ""),
            "tab": row.get("tab", ""),
            "displayTime": row.get("displayTime"),
            "brief": row.get("brief", ""),
            "author": row.get("author", ""),
            "sticky": row.get("sticky"),
        })
    return {"page": page, "page_size_requested": page_size, "status": status,
            "api_code": data.get("code") if isinstance(data, dict) else None,
            "message": data.get("msg") if isinstance(data, dict) else None,
            "total": payload.get("total"), "current": payload.get("current"),
            "page_size_returned": payload.get("pageSize"), "list_count": len(items), "items": items}


def main():
    # First test a larger page size. If server caps it, paginate using the returned page size.
    first = request_page(1, 50)
    pages = [first]
    total = first.get("total") or 0
    effective_size = first.get("page_size_returned") or first.get("list_count") or 10
    if first.get("status") == 200 and first.get("list_count", 0) > 0 and total:
        expected_pages = min(30, max(1, (int(total) + int(effective_size) - 1) // int(effective_size)))
        for page in range(2, expected_pages + 1):
            result = request_page(page, int(effective_size))
            pages.append(result)
            if result.get("status") != 200 or not result.get("list_count"):
                break
            time.sleep(0.12)
    items, seen = [], set()
    for result in pages:
        for item in result.get("items", []):
            key = item.get("cid") or (item.get("title"), item.get("displayTime"))
            if key not in seen:
                seen.add(key)
                items.append(item)
    candidates = [it for it in items if any(word.lower() in str(it.get("title", "")).lower() or word.lower() in str(it.get("brief", "")).lower() for word in KEYWORDS)]
    report = {
        "version": 87, "mode": "read_only", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": HOST, "app_code": APP_CODE, "request_shape": "GET with lang=ja-jp, code, page, pageSize; tabs omitted to retrieve all categories",
        "reported_total": total, "pages_fetched": len(pages), "unique_items_fetched": len(items),
        "page_results": [{k: v for k, v in p.items() if k != "items"} for p in pages],
        "items": items, "keyword_candidates": candidates,
        "warning": "Read-only public GET inventory. Keyword matches are review candidates, not verified events. No event/calendar files were changed."
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"V87 inventory complete: {len(items)} unique articles across {len(pages)} page(s) -> {OUT}")

if __name__ == "__main__":
    main()
