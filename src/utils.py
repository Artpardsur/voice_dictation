\"\"\"
Вспомогательные функции
\"\"\"

import json
import os

def load_json(file_path: str) -> dict:
    \"\"\"Загрузить JSON файл\"\"\"
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
