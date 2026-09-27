from pathlib import Path
import sqlite3
from datetime import date

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
                recurrence_source_id INTEGER,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed);
            CREATE INDEX IF NOT EXISTS idx_tasks_recurrence_source ON tasks(recurrence_source_id);
        """)
        self._add_column_if_missing("tasks", "start_time", "TEXT")
        self._add_column_if_missing("tasks", "end_time", "TEXT")
        self._add_column_if_missing("tasks", "category", "TEXT NOT NULL DEFAULT 'Personal'")
        self._add_column_if_missing("tasks", "tags", "TEXT NOT NULL DEFAULT ''")
        self._add_column_if_missing("tasks", "recurrence", "TEXT NOT NULL DEFAULT 'none'")
        self._add_column_if_missing("tasks", "recurrence_source_id", "INTEGER")
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_recurrence_unique "
            "ON tasks(recurrence_source_id, due_date) WHERE recurrence_source_id IS NOT NULL"
        )
        self.connection.commit()

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        assert self.connection is not None
        columns = {row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_task(
        self, title, description="", due_date=None, start_time=None, end_time=None,
        priority="medium", category="Personal", tags="", recurrence="none",
        recurrence_source_id=None
    ) -> int:
        assert self.connection is not None
        cursor = self.connection.execute(
            """INSERT INTO tasks
            (title, description, due_date, start_time, end_time, priority, category, tags, recurrence, recurrence_source_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, due_date, start_time, end_time, priority, category, tags, recurrence, recurrence_source_id),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def update_task(self, task_id: int, **fields) -> None:
        assert self.connection is not None
        allowed = {
            "title", "description", "due_date", "start_time", "end_time",
            "priority", "category", "tags", "recurrence", "recurrence_source_id", "completed"
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        clause = ", ".join(f"{key} = ?" for key in updates)
        self.connection.execute(
            f"UPDATE tasks SET {clause} WHERE id = ?",
            (*updates.values(), task_id),
        )
        self.connection.commit()

    def delete_task(self, task_id: int) -> None:
        assert self.connection is not None
        row = self.get_task(task_id)
        if not row:
            return
        if row["recurrence_source_id"] is not None:
            self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        else:
            self.connection.execute(
                "DELETE FROM tasks WHERE recurrence_source_id = ? OR id = ?",
                (task_id, task_id),
            )
        self.connection.commit()

    def get_task(self, task_id: int):
        assert self.connection is not None
        return self.connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

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
            "SELECT * FROM tasks WHERE due_date = ? "
            "ORDER BY completed ASC, start_time IS NULL, start_time ASC, id DESC",
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

    def recurring_templates(self):
        assert self.connection is not None
        return list(self.connection.execute(
            "SELECT * FROM tasks WHERE recurrence != 'none' AND recurrence_source_id IS NULL "
            "AND due_date IS NOT NULL ORDER BY due_date, id"
        ))

    def occurrence_exists(self, source_id: int, due_date: str) -> bool:
        assert self.connection is not None
        return self.connection.execute(
            "SELECT 1 FROM tasks WHERE recurrence_source_id = ? AND due_date = ? LIMIT 1",
            (source_id, due_date),
        ).fetchone() is not None

    def filtered_tasks(self, query="", status="all", priority="all", category="all",
                       recurrence="all", date_from=None, date_to=None):
        assert self.connection is not None
        clauses = []
        params = []
        if query.strip():
            term = f"%{query.strip()}%"
            clauses.append("(title LIKE ? OR description LIKE ? OR category LIKE ? OR tags LIKE ?)")
            params.extend([term, term, term, term])
        if status == "open":
            clauses.append("completed = 0")
        elif status == "completed":
            clauses.append("completed = 1")
        if priority != "all":
            clauses.append("priority = ?")
            params.append(priority)
        if category != "all":
            clauses.append("category = ?")
            params.append(category)
        if recurrence != "all":
            clauses.append("recurrence = ?")
            params.append(recurrence)
        if date_from:
            clauses.append("due_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("due_date <= ?")
            params.append(date_to)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return list(self.connection.execute(
            f"""SELECT * FROM tasks{where}
            ORDER BY completed ASC, due_date IS NULL, due_date ASC,
                     start_time IS NULL, start_time ASC, id DESC""",
            params,
        ))

    def productivity_stats(self, date_from=None, date_to=None):
        assert self.connection is not None
        clauses = []
        params = []
        if date_from:
            clauses.append("due_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("due_date <= ?")
            params.append(date_to)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        row = self.connection.execute(
            f"""SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) AS open,
                SUM(CASE WHEN priority = 'high' AND completed = 0 THEN 1 ELSE 0 END) AS high_open
                FROM tasks{where}""",
            params,
        ).fetchone()
        category_rows = self.connection.execute(
            f"""SELECT category, COUNT(*) AS total,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed
                FROM tasks{where}
                GROUP BY category ORDER BY total DESC""",
            params,
        ).fetchall()
        return row, category_rows

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
