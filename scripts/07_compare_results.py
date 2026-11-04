"""Сопоставление масок, фактического времени и результатов."""
from __future__ import annotations
import argparse, csv, json
from common import load_config, paths, ensure_dirs, write_json

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--results", default=None); parser.add_argument("--counts", default=None)
    args = parser.parse_args(); config = load_config(args.config); p = paths(config); ensure_dirs(config, ["comparisons"]); result_path = Path(args.results) if args.results else p["processed_results"] / "experiment_results.json"; counts_path = Path(args.counts) if args.counts else p["statistics"] / "combination_counts.json"
    results = json.loads(result_path.read_text(encoding="utf-8")); counts = {row["name"]: row for row in json.loads(counts_path.read_text(encoding="utf-8")).get("masks", [])}; rows = []
    for row in results.get("runs", []):
        count = counts.get(row.get("mask_name"), {}); combinations = count.get("combinations"); speed = row.get("speed"); theoretical = combinations / speed if combinations and speed else None; rows.append({**row, "combinations": combinations, "theoretical_full_time_seconds": theoretical, "comparison_note": "Фактическое время не является временем полного пространства, если Hashcat завершился раньше."})
    write_json(p["comparisons"] / "mask_comparison.json", {"experiment_id": results.get("experiment_id"), "masks": rows})
    if rows:
        with (p["comparisons"] / "mask_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted({key for row in rows for key in row})); writer.writeheader(); writer.writerows(rows)
    return 0
from pathlib import Path
if __name__ == "__main__": raise SystemExit(main())
