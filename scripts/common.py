"""Общие функции конфигурации, путей, логирования и табличного вывода."""
from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "config.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path or DEFAULT_CONFIG).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Конфигурация не найдена: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON конфигурации: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Корень конфигурации должен быть объектом JSON")
    data["_config_path"] = str(config_path)
    data["_root"] = str(config_path.parent.parent)
    return data


def root_path(config: dict[str, Any], value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(config["_root"]) / path


def paths(config: dict[str, Any]) -> dict[str, Path]:
    return {name: root_path(config, value) for name, value in config.get("paths", {}).items()}


def mask_files(config: dict[str, Any]) -> list[Path]:
    experiment = config.get("experiment", {})
    configured = experiment.get("mask_files")
    if not configured:
        configured = [experiment.get("mask_file", "data/masks/experiment.hcmask")]
    return [root_path(config, value) for value in configured]


def ensure_dirs(config: dict[str, Any], names: Iterable[str] | None = None) -> None:
    resolved = paths(config)
    for name in names or resolved:
        if name in resolved:
            resolved[name].mkdir(parents=True, exist_ok=True)


def configure_logging(config: dict[str, Any], name: str) -> logging.Logger:
    log_dir = root_path(config, config.get("paths", {}).get("logs", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(console)
    return logger


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def iter_lines(path: Path, encoding: str = "utf-8") -> Iterable[tuple[int, str]]:
    with path.open("r", encoding=encoding, errors="strict", newline="") as stream:
        for number, line in enumerate(stream, 1):
            yield number, line.rstrip("\r\n")


def valid_sha1(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", value))


def parse_args_config(description: str):
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Путь к config.json")
    return parser
