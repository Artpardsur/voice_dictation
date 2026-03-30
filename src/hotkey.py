"""
Глобальные горячие клавиши
"""

import threading
import logging
from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Слушатель глобальных горячих клавиш"""
    
    def __init__(self, on_record_start=None, on_record_stop=None):
        """
        Args:
            on_record_start: callback при нажатии клавиши для старта
            on_record_stop: callback при отпускании клавиши
        """
        self.on_record_start = on_record_start
        self.on_record_stop = on_record_stop
        self.recording = False
        self.listener = None
        self.ctrl_pressed = False
        self.alt_pressed = False
        
    def on_press(self, key):
        """Обработчик нажатия клавиши"""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.alt_pressed = True
            elif key == keyboard.Key.space:
                if self.ctrl_pressed and self.alt_pressed:
                    if not self.recording:
                        self.recording = True
                        if self.on_record_start:
                            self.on_record_start()
                        logger.info("Начало записи (Ctrl+Alt+Space)")
        except AttributeError:
            pass
    
    def on_release(self, key):
        """Обработчик отпускания клавиши"""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.alt_pressed = False
            elif key == keyboard.Key.space:
                if self.recording:
                    self.recording = False
                    if self.on_record_stop:
                        self.on_record_stop()
                    logger.info("Остановка записи")
        except AttributeError:
            pass
        
        # Выход по Esc
        if key == keyboard.Key.esc:
            return False
    
    def start(self):
        """Запустить слушатель в фоновом потоке"""
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.daemon = True
        self.listener.start()
        logger.info("Слушатель горячих клавиш запущен (Ctrl+Alt+Space)")
    
    def stop(self):
        """Остановить слушатель"""
        if self.listener:
            self.listener.stop()