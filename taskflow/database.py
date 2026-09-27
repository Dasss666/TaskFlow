from pathlib import Path
import sqlite3
from datetime import date, timedelta

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
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_date TEXT,
                start_time TEXT,
                end_time TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                category TEXT NOT NULL DEFAULT 'Personal',
                tags TEXT NOT NULL DEFAULT '',
                recurrence TEXT NOT NULL DEFAULT 'none',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);
        """)
        self._add_column_if_missing("tasks", "start_time", "TEXT")
        self._add_column_if_missing("tasks", "end_time", "TEXT")
        self._add_column_if_missing("tasks", "category", "TEXT NOT NULL DEFAULT 'Personal'")
        self._add_column_if_missing("tasks", "tags", "TEXT NOT NULL DEFAULT ''")
        self._add_column_if_missing("tasks", "recurrence", "TEXT NOT NULL DEFAULT 'none'")
        self.connection.commit()

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        assert self.connection is not None
        columns = {row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_task(self, title, description="", due_date=None, start_time=None, end_time=None,
                 priority="medium", category="Personal", tags="", recurrence="none") -> int:
        assert self.connection is not None
        cursor = self.connection.execute(
            """INSERT INTO tasks
            (title, description, due_date, start_time, end_time, priority, category, tags, recurrence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, due_date, start_time, end_time, priority, category, tags, recurrence),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def update_task(self, task_id: int, **fields) -> None:
        assert self.connection is not None
        allowed = {"title", "description", "due_date", "start_time", "end_time",
                   "priority", "category", "tags", "recurrence", "completed"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        clause = ", ".join(f"{key} = ?" for key in updates)
        self.connection.execute(f"UPDATE tasks SET {clause} WHERE id = ?", (*updates.values(), task_id))
        self.connection.commit()

    def delete_task(self, task_id: int) -> None:
        assert self.connection is not None
        self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()

    def get_task(self, task_id: int):
        assert self.connection is not None
        return self.connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    def list_tasks(self, include_completed=True) -> list[sqlite3.Row]:
        assert self.connection is not None
        where = "" if include_completed else "WHERE completed = 0"
        return list(self.connection.execute(
            f"""SELECT * FROM tasks {where}
            ORDER BY completed ASC,
                CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                due_date IS NULL, due_date ASC, start_time IS NULL, start_time ASC, id DESC"""
        ))

    def tasks_for_date(self, selected_date: date) -> list[sqlite3.Row]:
        assert self.connection is not None
        return list(self.connection.execute(
            "SELECT * FROM tasks WHERE due_date = ? ORDER BY completed ASC, start_time IS NULL, start_time ASC, id DESC",
            (selected_date.isoformat(),),
        ))

    def tasks_for_range(self, start: date, end: date) -> list[sqlite3.Row]:
        assert self.connection is not None
        return list(self.connection.execute(
            "SELECT * FROM tasks WHERE due_date BETWEEN ? AND ? ORDER BY due_date, start_time, id",
            (start.isoformat(), end.isoformat()),
        ))

    def search_tasks(self, query: str) -> list[sqlite3.Row]:
        assert self.connection is not None
        term = f"%{query.strip()}%"
        return list(self.connection.execute(
            """SELECT * FROM tasks
            WHERE title LIKE ? OR description LIKE ? OR category LIKE ? OR tags LIKE ?
            ORDER BY completed ASC, due_date IS NULL, due_date ASC""",
            (term, term, term, term),
        ))

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
