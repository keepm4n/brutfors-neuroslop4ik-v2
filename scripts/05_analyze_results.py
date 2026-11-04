"""Преобразование raw-метаданных запусков в единую таблицу."""
from __future__ import annotations
import argparse, csv, json
from common import load_config, paths, ensure_dirs, write_json

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--experiment-id")
    args = parser.parse_args(); config = load_config(args.config); p = paths(config); ensure_dirs(config, ["processed_results"])
    root = p["raw_results"] / args.experiment_id if args.experiment_id else p["raw_results"]; rows = []
    if not root.is_dir(): raise SystemExit(f"Не найден каталог raw: {root}")
    for metadata_path in sorted(root.glob("mask_*/metadata.json")):
        data = json.loads(metadata_path.read_text(encoding="utf-8")); inp = data.get("input_hashes", 0); new = data.get("newly_cracked", 0); data["new_find_rate_percent"] = (new / inp * 100) if inp else 0; data["metadata_path"] = str(metadata_path); rows.append(data)
    result = {"experiment_id": root.name, "runs": rows}; write_json(p["processed_results"] / "experiment_results.json", result)
    if rows:
        with (p["processed_results"] / "experiment_results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted({key for row in rows for key in row})); writer.writeheader(); writer.writerows(rows)
    return 0
if __name__ == "__main__": raise SystemExit(main())
