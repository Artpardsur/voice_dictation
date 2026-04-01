import vosk
import sys
import json
import sounddevice as sd
import numpy as np
import queue
import time

import os

# Получаем путь к корневой папке проекта
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(root_path, "models/vosk-model-small-ru-0.22")

print("Загрузка модели...")
try:
    model = vosk.Model(model_path)
    rec = vosk.KaldiRecognizer(model, 16000)
    print("✅ Модель загружена")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)

print("\nГоворите что-нибудь... (5 секунд)")

# Запись
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
    time.sleep(5)

print("\nРаспознаю...")

# Распознавание
rec.Reset()
result_text = ""

while not q.empty():
    data = q.get()
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        if 'text' in result:
            result_text += " " + result['text']

final = json.loads(rec.FinalResult())
if 'text' in final:
    result_text += " " + final['text']

if result_text.strip():
    print(f"\n✅ РАСПОЗНАНО: {result_text.strip()}")
else:
    print("\n❌ НИЧЕГО НЕ РАСПОЗНАНО")
    print("Проверьте:")
    print("  - Громкость микрофона")
    print("  - Фоновый шум")
    print("  - Говорите чётче")