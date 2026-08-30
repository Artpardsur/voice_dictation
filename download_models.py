#!/usr/bin/env python
"""Скачивание моделей Vosk.

    python download_models.py           обе модели
    python download_models.py ru        только русскую
    python download_models.py --list    что уже установлено

Модели весят десятки мегабайт, поэтому они не лежат в репозитории:
раньше клонирование тянуло больше 150 МБ.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import models  # noqa: E402


def make_output_safe() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def progress(done: int, total: int) -> None:
    if not total:
        print(f"  {done / 1048576:.1f} МБ", end="\r", flush=True)
        return
    share = done / total
    bar = "█" * int(share * 30) + "·" * (30 - int(share * 30))
    print(f"  {bar} {share * 100:5.1f} %  {done / 1048576:.1f} МБ", end="\r", flush=True)


def main(argv=None) -> int:
    make_output_safe()
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--list" in argv:
        print("\nМодели:\n")
        print(models.describe())
        print(f"\nПапка: {models.MODELS_DIR}\n")
        return 0

    wanted = [item for item in argv if item in models.MODELS] or list(models.MODELS)

    for language in wanted:
        info = models.get(language)
        if info.installed:
            print(f"  {info.title}: уже установлена")
            continue

        print(f"\n  {info.title} — примерно {info.size_mb} МБ")
        try:
            models.download(language, on_progress=progress)
        except Exception as error:  # noqa: BLE001 — сеть подводит по-разному
            print()
            print(f"  Не удалось скачать: {error}")
            print(f"  Можно вручную: {info.url}")
            print(f"  Распаковать в {models.MODELS_DIR}")
            return 1
        print()
        print(f"  Готово: {info.path}")

    print("\nМодели:\n")
    print(models.describe())
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
