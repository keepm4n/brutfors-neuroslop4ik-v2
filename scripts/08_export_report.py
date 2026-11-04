"""Формирование Markdown-отчёта только по фактически сохранённым данным."""
from __future__ import annotations
import argparse, json
from common import load_config, paths, ensure_dirs, utc_now

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default=None); args = parser.parse_args(); config = load_config(args.config); p = paths(config); ensure_dirs(config, ["reports"])
    def load(path): return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    stats = load(p["statistics"] / "password_statistics.json"); counts = load(p["statistics"] / "combination_counts.json"); results = load(p["processed_results"] / "experiment_results.json"); comparison = load(p["comparisons"] / "mask_comparison.json")
    lines = [f"# {config['project']['name']}", "", f"Сформировано: {utc_now()}", "", "## Условия", f"- Алгоритм: {config['experiment'].get('hash_algorithm', 'sha1')}", f"- GPU: {config['experiment'].get('gpu_name', 'не указан')}", f"- Hashcat mode: {config['hashcat'].get('hash_mode', 100)}", "", "## Исходные данные", f"- Записей: {stats.get('total_records', 'нет данных')}", f"- Уникальных значений: {stats.get('unique_passwords', 'нет данных')}", f"- Размер топ-100: {stats.get('top_100_count', 'нет данных')}", "", "## Маски и пространство поиска", "| Маска | Комбинации | Статус |", "|---|---:|---|"]
    for row in counts.get("masks", []): lines.append(f"| `{row.get('mask')}` | {row.get('combinations', 'не определено')} | {row.get('status')} |")
    lines += ["", "## Результаты Hashcat", "| Маска | Новые находки | Накоплено | Время, с | Статус |", "|---|---:|---:|---:|---|"]
    for row in results.get("runs", []): lines.append(f"| {row.get('mask_name')} | {row.get('newly_cracked', 0)} | {row.get('cumulative_cracked', 0)} | {row.get('duration_seconds', '')} | {row.get('status')} |")
    lines += ["", "## Ограничения", "Эксперимент использует SHA-1 и одну модель GPU. Маска ограничивает пространство поиска; ненайденное значение не означает невозможность восстановления другими методами. Фактическое время не следует автоматически трактовать как время полного перебора пространства.", "", "В публичный отчёт не включаются исходные пароли и восстановленные значения."]
    (p["reports"] / "final_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8"); return 0
if __name__ == "__main__": raise SystemExit(main())
