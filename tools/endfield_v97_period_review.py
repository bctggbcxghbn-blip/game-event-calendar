#!/usr/bin/env python3
"""V97: conservatively classify official event period clauses, without writing events.json."""
import json, re
from pathlib import Path

DATE = r"20\d{2}/\d{1,2}/\d{1,2}\s*\d{1,2}:\d{2}"

def classify(item):
    findings = []
    for match in item.get("matches", []):
        context = match.get("context", "")
        alias = match.get("alias", "")
        # Search ONLY the period clause immediately following the event's own title.
        # Other events' nearby dates are deliberately ignored.
        for m in re.finditer(re.escape(alias) + r".{0,50}?開催期間[：:]([^·■▼\n]{1,110})", context):
            clause = m.group(1).strip()
            if "メンテナンス前" in clause or "3回開催" in clause:
                status = "conditional_end"
                end = None
            else:
                dates = re.findall(DATE, clause)
                # Never infer an end from a single start or an unrelated date.
                status = "explicit_range_review" if len(dates) >= 2 and ("～" in clause or "〜" in clause) else "needs_review"
                end = None
            findings.append({"period_clause": clause, "status": status, "suggested_end": end})
    unique = list({f["period_clause"]: f for f in findings}.values())
    return {"id": item["id"], "title": item["title"], "registered": item.get("registered"),
            "calendar_end": item.get("calendar_end"), "periods": unique,
            "verified_end": None, "review_status": "manual_review_required"}

def run(input_path, output_dir):
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    results = [classify(x) for x in data["items"]]
    dest = Path(output_dir); dest.mkdir(parents=True, exist_ok=True)
    payload = {"version": 97, "mode": "read_only", "source_version": data.get("version"),
               "items": results, "verified_end_count": 0,
               "warning": "No event end dates were automatically verified or written."}
    (dest/"event-period-review.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines = ["# Endfield V97: 開催期間の厳密確認", "", "終了日の自動確定・events.jsonの変更は行いません。", ""]
    for item in results:
        lines.extend(["## "+item["title"], "登録: "+str(item["registered"]),
                      "終了日: 未確定", "開催期間候補:"])
        lines += ["- "+p["period_clause"]+" ("+p["status"]+")" for p in item["periods"]] or ["- 抽出できず（要確認）"]
        lines.append("")
    (dest/"event-period-review.md").write_text("\n".join(lines),encoding="utf-8")
    print("V97",len(results),"items; verified ends 0; read-only")

if __name__ == "__main__":
    run("artifacts/endfield-v96/event-date-context.json", "artifacts/endfield-v97")
