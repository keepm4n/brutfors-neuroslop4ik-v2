"""Проверка, нормализация и дедупликация SHA-1 файлов."""
from __future__ import annotations
import argparse, time
from common import load_config, paths, ensure_dirs, configure_logging, write_json, valid_sha1, utc_now

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--input-dir", default=None)
    args = parser.parse_args()
    try:
        config = load_config(args.config); logger = configure_logging(config, "02_merge_hashes"); p = paths(config); ensure_dirs(config, ["merged_hashes", "processed_results"])
        folder = p["individual_hashes"] if not args.input_dir else p["individual_hashes"].parent.parent / args.input_dir
        files = sorted(folder.glob("*_sha1.txt"));
        if not files: raise FileNotFoundError(f"Не найдены файлы хешей: {folder}")
        started = time.perf_counter(); unique: set[str] = set(); total = valid = invalid = duplicate = 0
        for file in files:
            with file.open(encoding="utf-8") as stream:
                for raw in stream:
                    total += 1; value = raw.strip()
                    if not valid_sha1(value): invalid += 1; continue
                    value = value.lower(); valid += 1
                    if value in unique: duplicate += 1
                    else: unique.add(value)
        result = p["merged_hashes"] / "all_hashes.txt"
        result.write_text("".join(value + "\n" for value in sorted(unique)), encoding="utf-8")
        stats = {"generated_at": utc_now(), "input_files": len(files), "total_lines": total, "valid_hashes": valid, "invalid_records": invalid, "duplicates": duplicate, "unique_hashes": len(unique), "duration_seconds": time.perf_counter() - started, "output": str(result)}
        write_json(p["processed_results"] / "merge_statistics.json", stats); return 0
    except (OSError, ValueError) as exc: print(f"Ошибка: {exc}"); return 1
if __name__ == "__main__": raise SystemExit(main())
