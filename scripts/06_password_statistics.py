"""Статистика исходных текстовых наборов без публикации паролей."""
from __future__ import annotations
import argparse, csv, re
from collections import Counter
from statistics import mean, median, multimode
from pathlib import Path
from common import load_config, paths, ensure_dirs, write_json

def classify(value: str) -> dict[str, bool]:
    return {"lower_latin": bool(re.search(r"[a-z]", value)), "upper_latin": bool(re.search(r"[A-Z]", value)), "digits": bool(re.search(r"\d", value)), "special": bool(re.search(r"[^A-Za-z0-9\s]", value)), "spaces": bool(re.search(r"\s", value)), "other": bool(re.search(r"[^A-Za-z0-9\s]", value))}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--input", help="Файл или каталог")
    args = parser.parse_args(); config = load_config(args.config); p = paths(config); ensure_dirs(config, ["statistics"]); source = Path(args.input).resolve() if args.input else p["source"]; files = [source] if source.is_file() else sorted(source.glob("*.txt")); counts = Counter(); lengths = Counter(); categories = Counter(); total = 0
    for file in files:
        with file.open(encoding=config["experiment"].get("encoding", "utf-8"), errors="strict") as stream:
            for line in stream:
                value = line.rstrip("\r\n")
                if not value: continue
                total += 1; counts[value] += 1; lengths[len(value)] += 1
                for name, enabled in classify(value).items():
                    if enabled: categories[name] += 1
    length_values = [length for length, count in lengths.items() for _ in range(count)]; top = counts.most_common(config["experiment"].get("top_passwords", 100)); summary = {"files": [str(f) for f in files], "total_records": total, "unique_passwords": len(counts), "duplicate_records": total - len(counts), "length_distribution": dict(sorted(lengths.items())), "mean_length": mean(length_values) if length_values else None, "median_length": median(length_values) if length_values else None, "mode_length": multimode(length_values) if length_values else [], "category_counts": dict(categories), "top_100_count": len(top), "top_100_share_percent": (sum(count for _, count in top) / total * 100) if total else 0}
    write_json(p["statistics"] / "password_statistics.json", summary)
    with (p["statistics"] / "top_100.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(["rank", "length", "frequency", "share_percent"]); writer.writerows((rank, len(password), count, count / total * 100 if total else 0) for rank, (password, count) in enumerate(top, 1))
    return 0
if __name__ == "__main__": raise SystemExit(main())
