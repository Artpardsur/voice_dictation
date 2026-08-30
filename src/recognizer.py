"""Оффлайн распознавание речи через Vosk.

Ничего никуда не отправляется: модель работает на этом же компьютере.
"""

from __future__ import annotations

import json
import logging
import queue
import time
from pathlib import Path
from typing import Callable, Optional

from . import models

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
# Дольше этого запись не тянется, даже если клавишу зажали и забыли.
MAX_RECORD_SECONDS = 120


class RecognizerError(RuntimeError):
    """Не получилось подготовить распознавание."""


def _rms(chunk: bytes) -> float:
    """Громкость куска звука, 0..1 — для полоски уровня в интерфейсе.

    Считается по самим отсчётам, а не выдумывается: прежняя версия рисовала
    уровень случайными числами, и полоска дёргалась даже в тишине.
    """
    if not chunk:
        return 0.0
    import array

    samples = array.array("h")
    samples.frombytes(chunk[: len(chunk) - (len(chunk) % 2)])
    if not samples:
        return 0.0
    total = sum(value * value for value in samples)
    return min(1.0, ((total / len(samples)) ** 0.5) / 32768.0 * 4)


class VoiceRecognizer:
    """Запись с микрофона и распознавание."""

    def __init__(
        self,
        language: str = models.DEFAULT_LANGUAGE,
        model_path: Optional[str] = None,
        on_level: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.language = language
        self.record_duration = 3          # секунд, если запись не push-to-talk
        self.on_level = on_level

        self.model = None
        self.rec = None
        self.stream = None
        self.is_recording = False
        self.q: "queue.Queue[bytes]" = queue.Queue()

        self.load_model(model_path)

    # --- модель --------------------------------------------------------------

    @property
    def ready(self) -> bool:
        """Модель загружена и распознавание возможно."""
        return self.rec is not None

    def model_hint(self) -> str:
        """Что сказать пользователю, если модели нет."""
        info = models.get(self.language)
        return (
            f"Модель «{info.title}» не установлена ({info.size_mb} МБ).\n"
            f"Скачать: python download_models.py {info.language}\n"
            f"Или вручную: {info.url} — распаковать в папку models/"
        )

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Загрузить модель Vosk. Возвращает True, если получилось."""
        path = Path(model_path) if model_path else models.get(self.language).path

        if not (path / "am" / "final.mdl").is_file():
            logger.warning("Модель не найдена: %s", path)
            self.model = self.rec = None
            return False

        try:
            import vosk

            vosk.SetLogLevel(-1)          # иначе Vosk засыпает консоль отладкой
            self.model = vosk.Model(str(path))
            self.rec = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
            logger.info("Модель загружена: %s", path)
            return True
        except ImportError:
            logger.error("Не установлен vosk: pip install -r requirements.txt")
        except Exception as error:  # noqa: BLE001 — Vosk бросает разное
            logger.error("Ошибка загрузки модели: %s", error)
        self.model = self.rec = None
        return False

    def change_model(self, language: str) -> bool:
        if language == self.language and self.ready:
            return True
        self.language = language
        return self.load_model()

    # --- запись ---------------------------------------------------------------

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning("Звуковой поток: %s", status)
        chunk = bytes(indata)
        self.q.put(chunk)
        if self.on_level:
            self.on_level(_rms(chunk))

    def start_recording(self) -> bool:
        """Начать запись с микрофона."""
        if self.is_recording:
            return True

        try:
            import sounddevice as sd
        except ImportError:
            logger.error("Не установлен sounddevice: pip install -r requirements.txt")
            return False

        self.q = queue.Queue()
        try:
            self.stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                device=None,
                dtype="int16",
                channels=1,
                callback=self._callback,
            )
            self.stream.start()
        except Exception as error:  # noqa: BLE001 — sounddevice бросает своё
            logger.error("Не удалось открыть микрофон: %s", error)
            self.stream = None
            return False

        self.is_recording = True
        logger.info("Запись начата")
        return True

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:  # noqa: BLE001 — закрытие не должно ронять программу
                pass
            self.stream = None
        if self.on_level:
            self.on_level(0.0)
        logger.info("Запись остановлена")

    # --- распознавание ----------------------------------------------------------

    def recognize(self) -> str:
        """Разобрать накопленный звук и вернуть текст."""
        if not self.ready:
            logger.warning("Модель не загружена")
            return ""

        self.rec.Reset()
        pieces = []
        chunks = 0

        while not self.q.empty():
            data = self.q.get()
            chunks += 1
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                if result.get("text"):
                    pieces.append(result["text"])

        final = json.loads(self.rec.FinalResult())
        if final.get("text"):
            pieces.append(final["text"])

        text = " ".join(pieces).strip()
        logger.info("Кусков звука: %s, распознано: %r", chunks, text)
        return text

    def record_and_recognize(self, duration: Optional[float] = None) -> str:
        """Записать заданное время и распознать.

        ``duration=None`` — писать, пока не позовут :meth:`stop_recording`
        (режим «удерживай клавишу»).
        """
        if not self.start_recording():
            return ""

        limit = MAX_RECORD_SECONDS if duration is None else min(duration, MAX_RECORD_SECONDS)
        started = time.monotonic()
        while self.is_recording and time.monotonic() - started < limit:
            time.sleep(0.05)

        self.stop_recording()
        # Последний блок приходит из звукового потока с задержкой.
        time.sleep(0.3)
        return self.recognize()
