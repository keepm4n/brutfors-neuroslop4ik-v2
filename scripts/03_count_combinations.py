"""Точный подсчёт пространства масок Hashcat из .hcmask."""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path
from common import load_config, paths, ensure_dirs, write_json, mask_files

CHARSETS = {"l": 26, "u": 26, "d": 10, "h": 16, "H": 16, "s": 33, "a": 95, "b": 256}


def charset_size(value: str) -> int | None:
    """Возвращает размер объединения стандартных токенов и литералов."""
    literal = set()
    sizes = 0
    index = 0
    while index < len(value):
        if value[index] == "?":
            if index + 1 >= len(value) or value[index + 1] not in CHARSETS:
                return None
            sizes += CHARSETS[value[index + 1]]
            index += 2
        else:
            literal.add(value[index]); index += 1
    return sizes + len(literal)

def count_mask(mask: str) -> tuple[int | None, str, list[int]]:
    custom: dict[str, int] = {}
    sizes: list[int] = []
    if "," in mask:
        parts = [part.strip() for part in mask.split(",")]
        mask = parts[-1]
        for index, value in enumerate(parts[:-1], 1):
            size = charset_size(value)
            if size is None or size == 0:
                return None, f"unsupported_custom_charset_{index}", sizes
            custom[str(index)] = size
    i = 0
    while i < len(mask):
        if mask[i] == "?":
            if i + 1 >= len(mask): return None, "invalid", sizes
            code = mask[i + 1]
            if code in custom: sizes.append(custom[code])
            elif code not in CHARSETS: return None, f"unsupported_charset_?{code}", sizes
            else: sizes.append(CHARSETS[code])
            i += 2
        else: i += 1
    if not sizes: return None, "empty_or_literal_mask", sizes
    total = 1
    for size in sizes: total *= size
    return total, "exact", sizes

def read_masks(path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            value = line.strip()
            if value and not value.startswith("#"): yield number, value

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); parser.add_argument("--mask-file", default=None)
    args = parser.parse_args()
    try:
        config = load_config(args.config); p = paths(config); ensure_dirs(config, ["statistics"])
        files = [Path(args.mask_file).resolve()] if args.mask_file else mask_files(config)
        rows = []
        for file_index, mask_path in enumerate(files, 1):
            if mask_path.suffix.lower() != ".hcmask" or not mask_path.is_file(): raise FileNotFoundError(f"Файл .hcmask не найден: {mask_path}")
            file_rows = []
            for number, mask in read_masks(mask_path):
                count, status, sizes = count_mask(mask); file_rows.append({"source_line": number, "mask": mask, "length": len(sizes), "alphabet_sizes": ",".join(map(str, sizes)), "combinations": count, "status": status})
            if not file_rows: raise ValueError(f"Файл .hcmask не содержит масок: {mask_path}")
            exact = all(item["status"] == "exact" for item in file_rows)
            total = sum(item["combinations"] for item in file_rows) if exact else None
            rows.append({"name": f"mask_{file_index}", "type": "hcmask", "mask_file": str(mask_path), "line_count": len(file_rows), "min_length": min(item["length"] for item in file_rows), "max_length": max(item["length"] for item in file_rows), "combinations": total, "status": "exact" if exact else "indeterminate", "lines": file_rows})
        result = {"mask_files": [str(path) for path in files], "masks": rows}; write_json(p["statistics"] / "combination_counts.json", result)
        with (p["statistics"] / "combination_counts.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            flat_rows = [{key: value for key, value in row.items() if key != "lines"} for row in rows]
            writer = csv.DictWriter(stream, fieldnames=list(flat_rows[0])); writer.writeheader(); writer.writerows(flat_rows)
        return 0
    except (OSError, ValueError) as exc: print(f"Ошибка: {exc}"); return 1
if __name__ == "__main__": raise SystemExit(main())
