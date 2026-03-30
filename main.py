#!/usr/bin/env python
"""
Voice Dictation - Оффлайн голосовой ввод
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import VoiceDictationApp

if __name__ == "__main__":
    app = VoiceDictationApp()
    app.run()