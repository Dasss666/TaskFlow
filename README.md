# TaskFlow

A Windows desktop task manager and personal agenda built with Python, PySide6 and SQLite.

## Implemented
- Task creation/editing/deletion
- Completion state
- Priority, category and tags
- Date and start/end time
- Daily agenda
- Weekly view
- Monthly calendar
- Search
- Dark desktop theme
- Recurring task metadata (none/daily/weekly/monthly)
- Windows tray notifications for scheduled tasks
- JSON import/export
- Local SQLite persistence

## Run
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m taskflow
```

## Build Windows executable
```powershell
pyinstaller --noconfirm --windowed --name TaskFlow taskflow/__main__.py
```

The executable will be generated under `dist/TaskFlow/`.

## Roadmap
- Drag-and-drop scheduling
- Rich recurring-event generation
- Productivity statistics
- Advanced filters
- Custom themes
- Installer/release automation
- Optional cloud synchronization
