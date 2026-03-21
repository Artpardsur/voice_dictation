\"\"\"
Работа с базой данных
\"\"\"

class Database:
    \"\"\"Управление БД\"\"\"
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
    
    def connect(self):
        \"\"\"Подключение к БД\"\"\"
        pass
    
    def close(self):
        \"\"\"Закрытие соединения\"\"\"
        pass
