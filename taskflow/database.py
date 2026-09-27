from pathlib import Path
import sqlite3

APP_DIR = Path.home() / "AppData" / "Local" / "TaskFlow"
DB_PATH = APP_DIR / "taskflow.db"

class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def add_task(self, title: str, due_date: str | None = None, priority: str = "medium") -> int:
        assert self.connection is not None
        cursor = self.connection.execute(
            "INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
            (title, due_date, priority),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_tasks(self) -> list[sqlite3.Row]:
        assert self.connection is not None
        return list(self.connection.execute("""
            SELECT * FROM tasks
            ORDER BY completed ASC,
                CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                due_date IS NULL, due_date ASC, id DESC
        """))

    def set_completed(self, task_id: int, completed: bool) -> None:
        assert self.connection is not None
        self.connection.execute("UPDATE tasks SET completed = ? WHERE id = ?", (int(completed), task_id))
        self.connection.commit()
