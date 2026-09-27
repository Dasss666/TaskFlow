# TaskFlow

Windows desktop task manager and agenda built with Python.

## Stack
- Python 3.12+
- PySide6
- SQLite

## Current MVP
- Persistent local task database
- Add tasks
- Task priority
- Complete/uncomplete tasks

## Run on Windows
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m taskflow
```

## Roadmap
- Modern task management UI
- Task editing, deletion, tags and notes
- Calendar day/week/month views
- Events with start/end times
- Reminders and Windows notifications
- Search and filters
- Dark theme and personalization
- Windows .exe packaging
