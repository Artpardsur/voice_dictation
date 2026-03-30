"""
Работа с буфером обмена
"""

import pyperclip
import logging

logger = logging.getLogger(__name__)


class ClipboardManager:
    """Управление буфером обмена"""
    
    @staticmethod
    def get_text():
        """Получить текст из буфера обмена"""
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Ошибка чтения буфера: {e}")
            return ""
    
    @staticmethod
    def set_text(text):
        """Записать текст в буфер обмена"""
        try:
            pyperclip.copy(text)
            logger.info(f"Текст скопирован: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи в буфер: {e}")
            return False
