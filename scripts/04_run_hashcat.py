"""Последовательный запуск Hashcat только с файлами .hcmask."""
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from common import load_config, paths, ensure_dirs, configure_logging, write_json, utc_now, valid_sha1, mask_files

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--mask-file", default=None); parser.add_argument("--experiment-id", default=None); parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config); logger = configure_logging(config, "04_run_hashcat"); p = paths(config)
    try:
        ensure_dirs(config, ["raw_results", "cracked_hashes"]); merged = p["merged_hashes"] / "all_hashes.txt"
        if not merged.is_file(): raise FileNotFoundError(f"Не найден объединённый файл: {merged}")
        masks = [Path(args.mask_file).resolve()] if args.mask_file else mask_files(config)
        for mask in masks:
            if mask.suffix.lower() != ".hcmask" or not mask.is_file(): raise ValueError(f"Требуется существующий файл .hcmask: {mask}")
        executable = config["hashcat"].get("executable", "hashcat"); resolved = shutil.which(executable) or (str(Path(executable).expanduser()) if Path(executable).is_file() else None)
        if not resolved and not args.dry_run: raise FileNotFoundError(f"Hashcat не найден: {executable}")
        hashes = {line.strip().lower() for line in merged.read_text(encoding="utf-8").splitlines() if valid_sha1(line.strip())}
        experiment_id = args.experiment_id or config["experiment"].get("experiment_id") or datetime.now(timezone.utc).strftime("experiment_%Y%m%dT%H%M%SZ")
        run_root = p["raw_results"] / experiment_id; run_root.mkdir(parents=True, exist_ok=False)
        if args.dry_run:
            write_json(run_root / "dry_run.json", {"experiment_id": experiment_id, "mask_files": [str(mask) for mask in masks], "hashcat": resolved, "hashes": len(hashes), "status": "not_started"}); return 0
        version = subprocess.run([resolved, "--version"], capture_output=True, text=True, check=False)
        remaining = set(hashes); cumulative = set(); status = "completed"
        increment = config["experiment"].get("increment", {})
        for index, mask in enumerate(masks, 1):
            if not remaining:
                break
            active = run_root / f"active_{index:03d}.txt"; active.write_text("\n".join(sorted(remaining)) + "\n", encoding="utf-8")
            folder = run_root / f"mask_{index:02d}_{mask.stem}"; folder.mkdir(); started_iso = utc_now(); started = time.perf_counter(); cracked_file = folder / "cracked.txt"; potfile = folder / "hashcat.potfile"
            command = [resolved, "-m", str(config["hashcat"].get("hash_mode", 100)), "-a", "3", str(active), str(mask), "--potfile-path", str(potfile), "--outfile", str(cracked_file), "--outfile-format", "1,2", "--status", "--status-timer", str(config["hashcat"].get("status_interval", 10)), "--machine-readable", "--workload-profile", str(config["hashcat"].get("workload_profile", 2))]
            if increment.get("enabled", True): command.extend(["--increment", "--increment-min", str(increment.get("min_length", 4)), "--increment-max", str(increment.get("max_length", 12))])
            if config["hashcat"].get("optimized_kernel"): command.append("-O")
            metadata = {"experiment_id": experiment_id, "mask_name": f"mask_{index}", "mask_file": str(mask), "hashcat_version": version.stdout.strip(), "hash_mode": config["hashcat"].get("hash_mode", 100), "attack_mode": 3, "input_hashes": len(remaining), "start_time": started_iso, "platform": platform.platform(), "gpu_name": config["experiment"].get("gpu_name"), "increment": increment, "command": command}
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=(config["hashcat"].get("timeout_seconds") or None), check=False)
                status = "completed" if proc.returncode in (0, 1) else "failed"; (folder / "stdout.txt").write_text(proc.stdout or "", encoding="utf-8"); (folder / "stderr.txt").write_text(proc.stderr or "", encoding="utf-8"); metadata["return_code"] = proc.returncode
            except subprocess.TimeoutExpired as exc:
                status = "timeout"; (folder / "stdout.txt").write_text(exc.stdout or "", encoding="utf-8"); (folder / "stderr.txt").write_text(exc.stderr or "", encoding="utf-8")
            except KeyboardInterrupt:
                status = "interrupted"; metadata["return_code"] = None
            found = set()
            if cracked_file.exists():
                for line in cracked_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    value = line.split(":", 1)[0].strip().lower()
                    if value in remaining: found.add(value)
            cumulative.update(found); remaining.difference_update(found); ended = time.perf_counter(); metadata.update({"end_time": utc_now(), "duration_seconds": ended - started, "newly_cracked": len(found), "cumulative_cracked": len(cumulative), "remaining_hashes": len(remaining), "status": status}); write_json(folder / "metadata.json", metadata); write_json(folder / "status.json", {"status": status, "return_code": metadata.get("return_code"), "speed": None, "processed_combinations": None})
            if status in {"failed", "timeout", "interrupted"}: break
        write_json(run_root / "experiment_summary.json", {"experiment_id": experiment_id, "total_hashes": len(hashes), "cracked_hashes": len(cumulative), "remaining_hashes": len(remaining), "status": status, "hashcat_version": version.stdout.strip()})
        return 0 if status == "completed" else 1
    except (OSError, ValueError, subprocess.SubprocessError) as exc: logger.error(str(exc)); print(f"Ошибка: {exc}"); return 1
if __name__ == "__main__": raise SystemExit(main())
