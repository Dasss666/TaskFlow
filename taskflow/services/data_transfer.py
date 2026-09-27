import json
from pathlib import Path

def export_tasks(database, path: str) -> None:
    tasks = [dict(row) for row in database.list_tasks()]
    Path(path).write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

def import_tasks(database, path: str) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    count = 0
    for item in data:
        if not item.get("title"):
            continue
        fields = {key: item.get(key) for key in
                  ("description", "due_date", "start_time", "end_time", "priority", "category", "tags", "recurrence")}
        database.add_task(item["title"], **fields)
        count += 1
    return count
