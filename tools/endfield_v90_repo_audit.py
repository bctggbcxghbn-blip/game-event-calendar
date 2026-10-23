#!/usr/bin/env python3
"""Read-only audit of the repository's event schema and Endfield import path.

Writes reports under artifacts/ and never modifies events.json or application files.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def summarize_shape(value, depth=0, max_depth=3):
    if depth >= max_depth:
        return type(value).__name__
    if isinstance(value, dict):
        return {str(k): summarize_shape(v, depth + 1, max_depth) for k, v in list(value.items())[:30]}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "sample_shape": summarize_shape(value[0], depth + 1, max_depth) if value else None}
    return type(value).__name__


def main():
    report = {
        "version": "V90",
        "mode": "read_only",
        "warning": "This audit does not register events or modify events.json.",
        "events_json": {},
        "endfield_files": [],
        "workflow_files": [],
        "relevant_python_files": [],
        "duplicate_keys": {},
    }

    event_path = ROOT / "events.json"
    if event_path.exists():
        data, err = load_json(event_path)
        report["events_json"] = {"exists": True, "bytes": event_path.stat().st_size, "error": err}
        if err is None:
            report["events_json"].update({"root_type": type(data).__name__, "shape": summarize_shape(data)})
            events = data if isinstance(data, list) else data.get("events", []) if isinstance(data, dict) else []
            if isinstance(events, list):
                report["events_json"]["event_count"] = len(events)
                report["events_json"]["field_counts"] = dict(Counter(str(k) for e in events if isinstance(e, dict) for k in e.keys()))
                endfield = [e for e in events if isinstance(e, dict) and any("endfield" in str(e.get(k, "")).lower() for k in ("game", "game_id", "source", "url", "title", "id"))]
                report["events_json"]["endfield_count"] = len(endfield)
                report["events_json"]["endfield_samples"] = endfield[:5]
                keys = Counter()
                for e in events:
                    if isinstance(e, dict):
                        key = tuple(str(e.get(k, "")) for k in ("game", "game_id", "title", "name", "start", "start_date"))
                        keys[key] += 1
                report["duplicate_keys"] = [{"key": list(k), "count": n} for k, n in keys.items() if n > 1][:50]
    else:
        report["events_json"] = {"exists": False, "error": "events.json not found at repository root"}

    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", "site-packages"}
    for path in ROOT.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        low = rel.lower()
        if low.endswith((".yml", ".yaml")) and ("workflow" in low or ".github/" in low):
            report["workflow_files"].append(rel)
        if "endfield" in low or "arknights_endfield" in low:
            report["endfield_files"].append(rel)
        if low.endswith(".py"):
            try:
                txt = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(r"events\.json|endfield|arknights_endfield", txt, re.I):
                report["relevant_python_files"].append({"path": rel, "has_events_json": "events.json" in txt, "has_endfield_term": bool(re.search(r"endfield|arknights_endfield", txt, re.I)), "lines": len(txt.splitlines())})

    report["endfield_files"].sort()
    report["workflow_files"].sort()
    report["relevant_python_files"].sort(key=lambda x: x["path"])
    out_dir = ROOT / "artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "endfield-v90-repo-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# Endfield V90 repository audit", "", "- Mode: read-only", "- `events.json` and application files are not modified.", "", "## events.json", "", "```json", json.dumps(report["events_json"], ensure_ascii=False, indent=2), "```", "", "## Endfield-related files", ""]
    lines += [f"- `{x}`" for x in report["endfield_files"]] or ["- None found"]
    lines += ["", "## Workflow files", ""]
    lines += [f"- `{x}`" for x in report["workflow_files"]] or ["- None found"]
    lines += ["", "## Relevant Python files", ""]
    lines += [f"- `{x['path']}` (lines: {x['lines']}; events.json: {x['has_events_json']}; Endfield terms: {x['has_endfield_term']})" for x in report["relevant_python_files"]] or ["- None found"]
    lines += ["", "## Duplicate-key candidates", "", "```json", json.dumps(report["duplicate_keys"], ensure_ascii=False, indent=2), "```", "", "## Next step", "", "Use this report to decide the exact integration point and duplicate key before connecting V89 candidates. No events are auto-added by V90.", ""]
    (out_dir / "endfield-v90-repo-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print("V90 audit complete (read-only). Reports written to artifacts/endfield-v90-repo-audit.json and .md")

if __name__ == "__main__":
    main()
