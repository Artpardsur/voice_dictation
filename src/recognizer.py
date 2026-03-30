"""
Оффлайн распознавание речи через Vosk
"""

import json
import queue
import sys
import sounddevice as sd
import vosk
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceRecognizer:
    """Распознавание речи оффлайн"""
    
    MODELS = {
        "ru": "models/vosk-model-small-ru-0.22",
        "en": "models/vosk-model-small-en-us-0.15"
    }
    
    def __init__(self, language="ru", model_path=None):
        """
        Инициализация распознавателя
        
        Args:
            language: язык ('ru' или 'en')
            model_path: путь к папке с моделью Vosk
        """
        self.language = language
        self.record_duration = 3  # секунд по умолчанию
        
        if model_path is None:
            model_path = self.MODELS.get(language, self.MODELS["ru"])
        
        self.load_model(model_path)
        
        self.q = queue.Queue()
        self.is_recording = False
        
    def load_model(self, model_path):
        """Загрузить модель Vosk"""
        try:
            if not os.path.exists(model_path):
                logger.error(f"Модель не найдена: {model_path}")
                logger.info("Создаю заглушку для тестирования интерфейса...")
                # Заглушка для тестирования GUI
                self.model = None
                self.rec = None
                return
            
            self.model = vosk.Model(model_path)
            self.rec = vosk.KaldiRecognizer(self.model, 16000)
            logger.info(f"Модель загружена: {model_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            logger.info("Работа в режиме заглушки (распознавание недоступно)")
            self.model = None
            self.rec = None
    
    def change_model(self, language):
        """Сменить языковую модель"""
        if language == self.language:
            return
        
        self.language = language
        model_path = self.MODELS.get(language, self.MODELS["ru"])
        self.load_model(model_path)
        logger.info(f"Язык изменён на {language}")
    
    def callback(self, indata, frames, time, status):
        """Callback для звукового потока"""
        if status:
            logger.warning(f"Audio error: {status}")
        self.q.put(bytes(indata))
    
    def start_recording(self):
        """Начать запись с микрофона"""
        self.is_recording = True
        self.q = queue.Queue()
        
        try:
            self.stream = sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                device=None,
                dtype='int16',
                channels=1,
                callback=self.callback
            )
            self.stream.start()
            logger.info("Запись начата")
            return True
        except Exception as e:
            logger.error(f"Ошибка при старте записи: {e}")
            return False
    
    def stop_recording(self):
        """Остановить запись"""
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        logger.info("Запись остановлена")
    
    def recognize(self):
        """
        Распознать записанный текст
        
        Returns:
            str: распознанный текст или пустая строка
        """
        if not self.rec:
            logger.warning("Модель не загружена, распознавание недоступно")
            return ""
        
        self.rec.Reset()
        result_text = ""
        
        # Обрабатываем все накопленные аудиоданные
        audio_chunks = 0
        while not self.q.empty():
            data = self.q.get()
            audio_chunks += 1
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                if 'text' in result:
                    result_text += " " + result['text']
                    logger.info(f"Промежуточный результат: {result['text']}")
        
        # Финальный результат
        final = json.loads(self.rec.FinalResult())
        if 'text' in final:
            result_text += " " + final['text']
            logger.info(f"Финальный результат: {final['text']}")
        
        logger.info(f"Обработано аудио-чанков: {audio_chunks}")
        
        if result_text.strip():
            logger.info(f"✅ Распознано: {result_text.strip()}")
        else:
            logger.warning("❌ Ничего не распознано")
        
        return result_text.strip()
    
    def record_and_recognize(self):
        """
        Записать и распознать
        
        Returns:
            str: распознанный текст
        """
        if not self.start_recording():
            return ""
        
        # Записываем заданное количество секунд
        import time
        logger.info(f"Запись {self.record_duration} секунд...")
        for i in range(self.record_duration):
            if not self.is_recording:
                break
            time.sleep(1)
            logger.debug(f"Запись... {i+1}/{self.record_duration} сек")
        
        self.stop_recording()
        
        # Добавляем задержку перед распознаванием
        time.sleep(0.5)
        
        # Вызываем распознавание
        logger.info("Начинаю распознавание...")
        text = self.recognize()
        logger.info(f"Результат распознавания: '{text}'")
        
        return text