import sounddevice as sd
import numpy as np
import time

print("=" * 50)
print("ДОСТУПНЫЕ УСТРОЙСТВА ВВОДА")
print("=" * 50)

devices = sd.query_devices()
print(devices)

print("\n" + "=" * 50)
print("ПРОВЕРКА МИКРОФОНА")
print("=" * 50)

# Находим устройства ввода
input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        input_devices.append((i, dev['name']))
        print(f"  [{i}] {dev['name']}")

if not input_devices:
    print("❌ Нет доступных микрофонов!")
    exit()

print(f"\n✅ Найдено микрофонов: {len(input_devices)}")
print("\nГоворите что-нибудь... (3 секунды)")

# Записываем 3 секунды
duration = 3
recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype='int16')
sd.wait()

# Анализируем уровень звука
max_volume = np.max(np.abs(recording))
avg_volume = np.mean(np.abs(recording))

print(f"\nМаксимальный уровень: {max_volume}")
print(f"Средний уровень: {avg_volume:.0f}")

if max_volume < 500:
    print("❌ Уровень очень низкий! Проверьте микрофон:")
    print("   - Убедитесь, что микрофон подключен")
    print("   - Проверьте настройки звука в Windows")
    print("   - Увеличьте громкость микрофона")
else:
    print("✅ Микрофон работает!")
    print("   Звук записан, всё в порядке")