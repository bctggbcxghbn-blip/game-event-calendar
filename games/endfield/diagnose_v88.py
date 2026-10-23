#!/usr/bin/env python3
"""Read-only Endfield official bulletin detail probe. Never edits calendar files."""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HOST = "https://web-news.gryphline.com/api/bulletin"
APP_CODE = "arknights_endfield_official"
LANG = "ja-jp"
OUT = Path(".reports/endfield-details-v88/report.json")
MAX_DETAILS = 35
KEYWORDS = ["帰野", "ミンホ", "天河", "俗世", "青藍", "玉書", "申請", "スカウト", "スタンプラリー", "イベント概要", "開催概要", "開催期間", "丹青渡", "万象一新"]


def get_json(url: str, timeout: int = 20):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; EndfieldCalendarDiagnostics/88)", "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        status = resp.status
        raw = resp.read(2_000_000)
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace")), None
    except Exception as exc:
        return status, None, f"JSON parse failed: {type(exc).__name__}: {exc}; preview={raw[:250].decode('utf-8', errors='replace')}"


def inventory():
    all_items, pages, total = [], [], None
    page = 1
    while page <= 20:
        params = urlencode({"lang": LANG, "code": APP_CODE, "page": page, "pageSize": 20})
        status, payload, err = get_json(f"{HOST}?{params}")
        record = {"page": page, "status": status, "error": err}
        if payload is not None:
            data = payload.get("data", payload)
            if isinstance(data, dict):
                listing = data.get("list", []) or []
                total = data.get("total", total)
                record.update({"api_code": payload.get("code", payload.get("code")), "total": total, "list_count": len(listing)})
                all_items.extend(listing)
            else:
                record["shape"] = type(data).__name__
        pages.append(record)
        if err or status != 200 or not payload:
            break
        data = payload.get("data", payload)
        if not isinstance(data, dict) or not data.get("list") or (total is not None and len(all_items) >= total):
            break
        page += 1
        time.sleep(0.15)
    dedup = {}
    for item in all_items:
        cid = str(item.get("cid", item.get("id", "")))
        if cid:
            dedup[cid] = item
    return list(dedup.values()), pages, total


def score_item(item):
    text = (str(item.get("title", "")) + " " + str(item.get("brief", ""))).lower()
    hits = [kw for kw in KEYWORDS if kw.lower() in text]
    # Give direct references and articles likely to include dates higher priority.
    score = len(hits)
    if any(x in text for x in ["帰野", "ミンホ", "天河", "俗世", "青藍", "玉書"]): score += 20
    if "開催期間" in text or "開催概要" in text or "イベント概要" in text: score += 3
    if "申請" in text or "スカウト" in text: score += 2
    return score, hits


def detail_url(cid: str):
    # The official frontend uses /api/bulletin/{cid}; include the same locale/app query fields.
    params = urlencode({"lang": LANG, "code": APP_CODE})
    return f"{HOST}/{cid}?{params}"


def main():
    items, pages, total = inventory()
    ranked = []
    for item in items:
        score, hits = score_item(item)
        if score:
            ranked.append((score, str(item.get("cid", item.get("id", ""))), item, hits))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    # Always include known high-value articles if present, then fill by relevance.
    by_cid = {cid: (score, item, hits) for score, cid, item, hits in ranked}
    selected = []
    for cid in ["9560", "2652", "4489", "7013", "5207", "0744"]:
        if cid in by_cid and cid not in {x["cid"] for x in selected}:
            score, item, hits = by_cid[cid]
            selected.append({"cid": cid, "score": score, "item": item, "keyword_hits": hits})
    for score, cid, item, hits in ranked:
        if len(selected) >= MAX_DETAILS: break
        if cid not in {x["cid"] for x in selected}:
            selected.append({"cid": cid, "score": score, "item": item, "keyword_hits": hits})
    results = []
    for target in selected:
        cid = target["cid"]
        result = {"cid": cid, "title": target["item"].get("title", ""), "tab": target["item"].get("tab", ""), "keyword_hits": target["keyword_hits"], "status": None, "detail": None, "error": None}
        try:
            status, payload, err = get_json(detail_url(cid))
            result["status"] = status
            if payload is not None:
                result["api_code"] = payload.get("code")
                result["message"] = payload.get("message")
                result["detail"] = payload.get("data", payload)
            result["error"] = err
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)
        time.sleep(0.15)
    report = {
        "version": 88,
        "mode": "read_only",
        "host": HOST,
        "app_code": APP_CODE,
        "inventory_total_reported": total,
        "inventory_unique_items": len(items),
        "inventory_pages": pages,
        "details_attempted": len(results),
        "detail_results": results,
        "warning": "Read-only public GET requests only. Detail fields are reported as returned by the official API. No calendar or events.json files were changed."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"V88 read-only detail diagnostic complete: inventory={len(items)}, detail_attempted={len(results)}")
    print(f"Report: {OUT}")
    print("No calendar files were modified.")

if __name__ == "__main__":
    main()
