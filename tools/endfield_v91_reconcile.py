#!/usr/bin/env python3
"""V91 read-only reconciliation of V89 Endfield candidates against events.json."""
import argparse, json, re
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "games/endfield/v89_verified_candidates.json"

def norm(value):
    value = str(value or "").casefold()
    return re.sub(r"[\s　「」『』【】（）()・：:!！?？\-—_]", "", value)

def audit(events_path, candidates_path=CANDIDATES):
    events = json.loads(Path(events_path).read_text(encoding="utf-8"))
    candidates = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    if not isinstance(events, list):
        raise ValueError("events.json must be a JSON array")
    rows = []
    for candidate in candidates.get("events", []):
        cid = candidate.get("id")
        title = candidate.get("title", "")
        exact_id = [e for e in events if e.get("id") == cid]
        exact_name = [e for e in events if e.get("game") == "endfield" and norm(e.get("name")) == norm(title)]
        similar = []
        for e in events:
            if e.get("game") != "endfield" or not e.get("name"):
                continue
            ratio = SequenceMatcher(None, norm(title), norm(e["name"])).ratio()
            if ratio >= 0.55 and e not in exact_name:
                similar.append({"id": e.get("id"), "name": e.get("name"), "start": e.get("start"), "end": e.get("end"), "similarity": round(ratio, 3)})
        if exact_id:
            status = "already_registered_id"
        elif exact_name:
            status = "already_registered_name"
        elif candidate.get("end_date") is None:
            status = "waiting_for_verified_end"
        else:
            status = "review_before_import"
        rows.append({
            "candidate_id": cid, "title": title, "start_date": candidate.get("start_date"),
            "start_time": candidate.get("start_time"), "end_date": candidate.get("end_date"),
            "end_condition": candidate.get("end_condition"), "source_cid": candidate.get("source_cid"),
            "status": status,
            "exact_id_matches": [{"id": e.get("id"), "name": e.get("name")} for e in exact_id],
            "exact_name_matches": [{"id": e.get("id"), "name": e.get("name")} for e in exact_name],
            "similar_name_candidates": sorted(similar, key=lambda x: x["similarity"], reverse=True)[:5]
        })
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"version": 91, "mode": "read_only", "events_count": len(events),
            "endfield_count": sum(e.get("game") == "endfield" for e in events),
            "candidate_count": len(rows), "status_counts": counts, "candidates": rows,
            "warning": "No events are added or modified. Similar-name matches are review hints, not proof of duplicates."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="events.json")
    parser.add_argument("--candidates", default=str(CANDIDATES))
    parser.add_argument("--out", default=".reports/endfield-v91/reconciliation.json")
    args = parser.parse_args()
    report = audit(args.events, args.candidates)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = out.with_suffix(".md")
    lines = ["# Endfield V91 reconciliation", "", "- Mode: read-only", f"- events.json rows: {report['events_count']}", f"- Endfield rows: {report['endfield_count']}", f"- Candidates: {report['candidate_count']}", "", "## Status counts", ""]
    lines += [f"- {k}: {v}" for k, v in sorted(report["status_counts"].items())]
    lines += ["", "## Candidates", "", "| Candidate | Status | Exact match | Similar-name hints | End date |", "|---|---|---|---:|---|"]
    for r in report["candidates"]:
        exact = len(r["exact_id_matches"]) + len(r["exact_name_matches"])
        lines.append(f"| {r['title']} | {r['status']} | {exact} | {len(r['similar_name_candidates'])} | {r['end_date'] or '未確認'} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"version": 91, "candidate_count": report["candidate_count"], "status_counts": report["status_counts"], "json": str(out), "markdown": str(md)}, ensure_ascii=False))
if __name__ == "__main__":
    main()
