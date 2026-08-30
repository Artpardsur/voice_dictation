"""Где лежат модели Vosk и как их получить.

Модели весят десятки мегабайт (русская — около 45 МБ в архиве), поэтому в
репозитории им не место: раньше они лежали прямо в нём и клонирование
тянуло больше 150 МБ. Теперь модель скачивается один раз при первом запуске.
"""

from __future__ import annotations

import logging
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
BASE_URL = "https://alphacephei.com/vosk/models"


@dataclass(frozen=True)
class ModelInfo:
    """Одна языковая модель."""

    language: str
    title: str
    folder: str
    size_mb: int

    @property
    def path(self) -> Path:
        return MODELS_DIR / self.folder

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.folder}.zip"

    @property
    def installed(self) -> bool:
        # Признак настоящей модели, а не пустой папки.
        return (self.path / "am" / "final.mdl").is_file()


MODELS: Dict[str, ModelInfo] = {
    "ru": ModelInfo("ru", "Русский", "vosk-model-small-ru-0.22", 45),
    "en": ModelInfo("en", "English", "vosk-model-small-en-us-0.15", 40),
}

DEFAULT_LANGUAGE = "ru"


def get(language: str = DEFAULT_LANGUAGE) -> ModelInfo:
    return MODELS.get(language, MODELS[DEFAULT_LANGUAGE])


def missing() -> list:
    """Модели, которых ещё нет на диске."""
    return [model for model in MODELS.values() if not model.installed]


def download(
    language: str = DEFAULT_LANGUAGE,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Скачать и распаковать модель. Возвращает путь к папке модели."""
    model = get(language)
    if model.installed:
        return model.path

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    archive = MODELS_DIR / f"{model.folder}.zip"

    logger.info("Скачиваю модель %s (%s МБ)…", model.title, model.size_mb)
    try:
        with urllib.request.urlopen(model.url, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            with open(archive, "wb") as target:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)

        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(MODELS_DIR)
    finally:
        # Недокачанный архив не должен остаться и мешать следующей попытке.
        if archive.exists():
            archive.unlink()

    if not model.installed:
        raise RuntimeError(
            f"Архив распаковался, но модели в {model.path} нет. "
            "Возможно, изменилась структура архива на сайте Vosk."
        )

    logger.info("Модель готова: %s", model.path)
    return model.path


def remove(language: str) -> bool:
    """Удалить установленную модель — освободить место."""
    model = get(language)
    if not model.path.exists():
        return False
    shutil.rmtree(model.path, ignore_errors=True)
    return not model.path.exists()


def describe() -> str:
    """Строка о состоянии моделей — для интерфейса и командной строки."""
    lines = []
    for model in MODELS.values():
        mark = "есть" if model.installed else f"нет ({model.size_mb} МБ)"
        lines.append(f"  {model.language}  {model.title:<10} {mark}")
    return "\n".join(lines)
