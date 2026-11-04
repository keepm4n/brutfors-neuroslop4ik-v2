"""Потоковая генерация SHA-1 из текстовых файлов паролей."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
from common import load_config, paths, ensure_dirs, configure_logging, write_json, utc_now

def process_file(source: Path, output: Path, mapping: Path, encoding: str, logger) -> dict:
    started = time.perf_counter(); stats = {"source": source.name, "read_lines": 0, "processed": 0, "empty": 0, "errors": 0, "unique_passwords": 0}
    seen: set[str] = set(); output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("r", encoding=encoding, errors="strict", newline="") as inp, output.open("w", encoding="utf-8") as hashes, mapping.open("w", encoding="utf-8") as pairs:
        for line in inp:
            stats["read_lines"] += 1
            password = line.rstrip("\r\n")
            if password == "":
                stats["empty"] += 1; continue
            digest = hashlib.sha1(password.encode(encoding)).hexdigest()
            hashes.write(digest + "\n")
            pairs.write(json.dumps({"password": password, "sha1": digest}, ensure_ascii=False) + "\n")
            stats["processed"] += 1; seen.add(password)
    stats["unique_passwords"] = len(seen); stats["duration_seconds"] = time.perf_counter() - started
    return stats

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--input", help="Один файл вместо каталога")
    args = parser.parse_args()
    try:
        config = load_config(args.config); logger = configure_logging(config, "01_generate_hashes"); p = paths(config); ensure_dirs(config, ["individual_hashes", "processed_results"])
        source = Path(args.input).resolve() if args.input else p["source"]
        files = [source] if source.is_file() else sorted(source.glob("*.txt"))
        if not files: raise FileNotFoundError(f"Не найдены входные .txt файлы: {source}")
        all_stats = []
        for file in files:
            stem = file.stem; all_stats.append(process_file(file, p["individual_hashes"] / f"{stem}_sha1.txt", p["individual_hashes"] / f"{stem}_mapping.jsonl", config["experiment"].get("encoding", "utf-8"), logger))
        write_json(p["processed_results"] / "hash_generation_statistics.json", {"generated_at": utc_now(), "files": all_stats})
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Ошибка: {exc}"); return 1
if __name__ == "__main__": raise SystemExit(main())
