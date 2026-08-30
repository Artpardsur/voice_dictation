"""
Главное окно приложения с CustomTkinter
"""

import customtkinter as ctk
import threading
import time
import os
import sys

# Добавляем путь к src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import models, textproc
from src.clipboard import ClipboardManager
from src.database import Database
from src.hotkey import HotkeyListener
from src.recognizer import VoiceRecognizer


class VoiceDictationApp:
    """Главное приложение голосового ввода с современным дизайном"""
    
    def __init__(self):
        # Настройка темы CustomTkinter
        ctk.set_appearance_mode("dark")  # dark / light / system
        ctk.set_default_color_theme("blue")  # blue / green / dark-blue
        
        self.root = ctk.CTk()
        self.root.title("Voice Dictation Pro")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Компоненты. on_level получает настоящую громкость с микрофона —
        # полоска уровня больше не рисуется случайными числами.
        self.recognizer = VoiceRecognizer(on_level=self._level_from_microphone)
        self.clipboard = ClipboardManager()
        self.history = Database()
        self.hotkey_listener = None
        
        # Настройки записи
        self.record_duration = 3  # секунд (будем менять)
        self.is_recording = False
        self.last_text = ""
        
        # Звуковые уровни
        self.audio_levels = []
        
        self.setup_ui()
        self.setup_hotkeys()
        self.check_model()

    def check_model(self):
        """Сказать сразу, если модели нет, а не молчать до первой записи."""
        if self.recognizer.ready:
            info = models.get(self.recognizer.language)
            self.update_status(f"Готов к работе · модель «{info.title}»")
            return
        self.update_status("⚠️ Модель не установлена")
        self.text_area.insert("end", self.recognizer.model_hint() + "\n")

    def setup_ui(self):
        """Создаёт современный интерфейс"""
        
        # Основной фрейм с отступами
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        title = ctk.CTkLabel(
            self.main_frame,
            text="🎙️ VOICE DICTATION PRO",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#89b4fa"
        )
        title.pack(pady=(20, 5))
        
        subtitle = ctk.CTkLabel(
            self.main_frame,
            text="Оффлайн голосовой ввод | Без сбора данных",
            font=ctk.CTkFont(size=12),
            text_color="#a6adc8"
        )
        subtitle.pack(pady=(0, 20))
        
        # Статус с анимацией
        self.status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.status_frame.pack(pady=10)
        
        self.status_circle = ctk.CTkLabel(
            self.status_frame,
            text="⚪",
            font=ctk.CTkFont(size=24),
            text_color="#a6adc8"
        )
        self.status_circle.pack(side="left", padx=5)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=14),
            text_color="#a6adc8"
        )
        self.status_label.pack(side="left", padx=5)
        
        # Индикатор звука (визуализация)
        self.level_frame = ctk.CTkFrame(self.main_frame, height=60, corner_radius=10)
        self.level_frame.pack(fill="x", padx=30, pady=10)
        self.level_frame.pack_propagate(False)
        
        self.level_canvas = ctk.CTkCanvas(
            self.level_frame,
            height=40,
            bg="#2e2e3e",
            highlightthickness=0
        )
        self.level_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Кнопка записи с анимацией
        self.record_btn = ctk.CTkButton(
            self.main_frame,
            text="🎤 НАЧАТЬ ЗАПИСЬ",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=25,
            fg_color="#89b4fa",
            hover_color="#74a7e6",
            command=self.manual_record
        )
        self.record_btn.pack(pady=15, padx=50, fill="x")
        
        # Настройки длительности
        settings_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        settings_frame.pack(pady=10, padx=30, fill="x")
        
        duration_label = ctk.CTkLabel(
            settings_frame,
            text="⏱️ Длительность записи",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        duration_label.pack(pady=(10, 5))
        
        self.duration_slider = ctk.CTkSlider(
            settings_frame,
            from_=1,
            to=300,
            number_of_steps=299,
            command=self.update_duration
        )
        self.duration_slider.set(3)
        self.duration_slider.pack(pady=5, padx=20, fill="x")
        
        self.duration_value = ctk.CTkLabel(
            settings_frame,
            text="3 секунды",
            font=ctk.CTkFont(size=12)
        )
        self.duration_value.pack(pady=(0, 10))
        
        # Языковая модель
        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.pack(pady=5)
        
        ctk.CTkLabel(lang_frame, text="🌍 Язык:", font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
        
        self.lang_var = ctk.StringVar(value="Русский")
        lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["Русский", "English"],
            variable=self.lang_var,
            command=self.change_language,
            width=120
        )
        lang_menu.pack(side="left", padx=5)
        
        # Область текста
        text_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        text_header = ctk.CTkLabel(
            text_frame,
            text="📝 РАСПОЗНАННЫЙ ТЕКСТ",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        text_header.pack(pady=(10, 5))
        
        self.text_area = ctk.CTkTextbox(
            text_frame,
            font=ctk.CTkFont(size=12),
            corner_radius=10,
            border_width=1,
            border_color="#3b3b4b"
        )
        self.text_area.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Кнопки действий
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.pack(pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="📋 ВСТАВИТЬ",
            width=100,
            command=self.paste_to_active_window
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_frame,
            text="📄 КОПИРОВАТЬ",
            width=100,
            fg_color="#cba6f7",
            hover_color="#b89ae3",
            command=self.copy_text
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_frame,
            text="🗑️ ОЧИСТИТЬ",
            width=100,
            fg_color="#f38ba8",
            hover_color="#e27a97",
            command=self.clear_text
        ).pack(side="left", padx=5)
        
        # Футер с горячими клавишами
        footer = ctk.CTkLabel(
            self.main_frame,
            text="⌨️ Горячая клавиша: Ctrl + Alt + Пробел | ESC для выхода",
            font=ctk.CTkFont(size=10),
            text_color="#6c7086"
        )
        footer.pack(pady=10)
    
    def update_duration(self, value):
        """Обновить длительность записи"""
        self.record_duration = int(value)
        if self.record_duration < 60:
            self.duration_value.configure(text=f"{self.record_duration} секунд")
        else:
            minutes = self.record_duration // 60
            seconds = self.record_duration % 60
            self.duration_value.configure(text=f"{minutes} мин {seconds} сек")
    
    def _level_from_microphone(self, level):
        """Уровень приходит из звукового потока — рисовать можно только
        в главном потоке, поэтому передаём через root.after."""
        try:
            self.root.after(0, self.update_audio_level, level * 100)
        except RuntimeError:
            pass                      # окно уже закрыто

    def update_audio_level(self, level):
        """Обновить визуализацию звука. level — от 0 до 100."""
        if not self.level_canvas.winfo_exists():
            return
        self.level_canvas.delete("all")
        width = self.level_canvas.winfo_width()
        height = self.level_canvas.winfo_height()
        
        # Нормализуем уровень (0-100 -> 0-height)
        bar_height = int((level / 100) * height)
        
        # Цвет в зависимости от уровня
        if level < 30:
            color = "#a6e3a1"
        elif level < 70:
            color = "#f9e2af"
        else:
            color = "#f38ba8"
        
        # Рисуем полосу
        self.level_canvas.create_rectangle(
            0, height - bar_height,
            width, height,
            fill=color,
            outline=""
        )
    
    def update_status(self, message, is_recording=False):
        """Обновить статус с анимацией"""
        if is_recording:
            self.status_circle.configure(text="🔴", text_color="#f38ba8")
        else:
            self.status_circle.configure(text="⚪", text_color="#a6adc8")
        
        self.status_label.configure(text=message)
        self.root.update_idletasks()
    
    def start_recording_animation(self):
        """Вид окна во время записи.

        Полоску уровня рисует _level_from_microphone по данным звукового
        потока. Раньше здесь крутился цикл со случайными числами, и полоска
        дёргалась даже в полной тишине.
        """
        if not self.is_recording:
            return
        self.record_btn.configure(fg_color="#f38ba8", text="🔴 ЗАПИСЬ — нажмите, чтобы остановить")
        self.update_status("Идёт запись…", is_recording=True)
    
    def setup_hotkeys(self):
        """Настройка глобальных горячих клавиш"""
        def on_start():
            if not self.is_recording:
                self.root.after(0, self.manual_record)

        def on_stop():
            # Отпустили клавиши — заканчиваем запись. Раньше здесь было
            # пусто, и запись всегда длилась ровно заданное число секунд,
            # сколько бы ни говорили.
            if self.is_recording:
                self.root.after(0, self.recognizer.stop_recording)
        
        self.hotkey_listener = HotkeyListener(
            on_record_start=on_start,
            on_record_stop=on_stop
        )
        self.hotkey_listener.start()
    
    def manual_record(self):
        """Ручной запуск записи"""
        if self.is_recording:
            # Если уже записываем — останавливаем
            self.is_recording = False
            self.record_btn.configure(
                fg_color="#89b4fa",
                text="🎤 НАЧАТЬ ЗАПИСЬ"
            )
            return
        
        self.is_recording = True
        self.record_btn.configure(state="disabled")
        
        # Запускаем анимацию в отдельном потоке
        threading.Thread(target=self.start_recording_animation, daemon=True).start()
        
        # Запускаем запись и распознавание
        threading.Thread(target=self._record_and_recognize, daemon=True).start()
    
    def _record_and_recognize(self):
        """Записать и распознать"""
        text = self.recognizer.record_and_recognize(self.record_duration)
        
        # Обновляем UI в основном потоке
        self.root.after(0, lambda: self._on_recognition_complete(text))
    
    def _on_recognition_complete(self, text):
        """Обработка завершения распознавания"""
        self.is_recording = False
        self.record_btn.configure(state="normal", fg_color="#89b4fa", text="🎤 НАЧАТЬ ЗАПИСЬ")
        
        if text:
            self.last_text = text
            self.text_area.insert("end", text + "\n")
            self.text_area.see("end")
            self.clipboard.set_text(text)
            self.update_status(f"✅ Распознано и скопировано")
        else:
            self.update_status("❌ Ничего не распознано")
        
        # Очищаем визуализацию
        self.update_audio_level(0)
    
    def copy_text(self):
        """Копировать текст из поля"""
        text = self.text_area.get("0.0", "end-1c")
        if text:
            self.clipboard.set_text(text)
            self.update_status("📋 Текст скопирован")
        else:
            self.update_status("⚠️ Нет текста для копирования")
    
    def paste_to_active_window(self):
        """Вставить текст в активное окно"""
        text = self.text_area.get("0.0", "end-1c")
        if not text:
            self.update_status("⚠️ Нет текста для вставки")
            return
        
        self.clipboard.set_text(text)
        import pyautogui
        pyautogui.hotkey('ctrl', 'v')
        self.update_status("📝 Текст вставлен")
    
    def clear_text(self):
        """Очистить текстовое поле"""
        self.text_area.delete("0.0", "end")
        self.update_status("🗑️ Текст очищен")
    
    def change_language(self, choice):
        """Сменить язык модели"""
        if choice == "Русский":
            self.recognizer.change_model("ru")
            self.update_status("🌍 Язык изменён на русский")
        else:
            self.recognizer.change_model("en")
            self.update_status("🌍 Language changed to English")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    VoiceDictationApp().run()