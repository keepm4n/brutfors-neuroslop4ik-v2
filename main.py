"""Оркестратор этапов экспериментального исследования."""
from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path
from scripts.common import load_config, paths, ensure_dirs, mask_files

STAGES = {
    "hashes": "01_generate_hashes.py", "merge": "02_merge_hashes.py", "combinations": "03_count_combinations.py",
    "hashcat": "04_run_hashcat.py", "analyze": "05_analyze_results.py", "statistics": "06_password_statistics.py",
    "compare": "07_compare_results.py", "report": "08_export_report.py"
}

def check(config, include_hashcat: bool = True) -> list[str]:
    errors = []
    for key in ("source", "individual_hashes", "merged_hashes", "masks", "raw_results", "processed_results", "statistics", "comparisons", "reports", "logs"):
        if key not in paths(config): errors.append(f"Не задан путь: {key}")
    configured_masks = mask_files(config)
    for mask in configured_masks:
        if mask.suffix.lower() != ".hcmask" or not mask.is_file(): errors.append(f"Не найден .hcmask: {mask}")
    if not configured_masks: errors.append("Не задан ни один файл .hcmask")
    if include_hashcat and not (shutil.which(config["hashcat"].get("executable", "hashcat"))): errors.append("Hashcat не найден в PATH")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--check", action="store_true"); parser.add_argument("--stage", choices=[*STAGES, "all"], default="all"); parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(); config = load_config(args.config); ensure_dirs(config)
    errors = check(config, include_hashcat=False)
    if args.check:
        for error in errors: print(f"ERROR: {error}")
        print("Проверка завершена" if not errors else "Проверка обнаружила ошибки"); return 0 if not errors else 1
    selected = list(STAGES) if args.stage == "all" else [args.stage]
    for name in selected:
        command = [sys.executable, str(Path(__file__).parent / "scripts" / STAGES[name]), "--config", args.config or str(Path(config["_config_path"]))]
        if name == "hashcat" and args.dry_run: command.append("--dry-run")
        print(f"Запуск: {name}"); completed = subprocess.run(command)
        if completed.returncode != 0: return completed.returncode
    return 0
if __name__ == "__main__": raise SystemExit(main())
