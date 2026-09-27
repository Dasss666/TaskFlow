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
- Customizable themes: Midnight, Light, Cyberpunk and Ocean
- Persistent theme preference
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
pyinstaller --noconfirm --clean --onefile --windowed --name TaskFlow taskflow/__main__.py
```

The standalone executable is generated at `dist/TaskFlow.exe`.

## Build the Windows installer
The repository includes an Inno Setup configuration in `installer/TaskFlow.iss`.

GitHub Actions automatically builds the standalone executable, creates `TaskFlow-Setup.exe`, and uploads both files as workflow artifacts.

For a local installer build, install Inno Setup and run:
```powershell
iscc installer/TaskFlow.iss
```

## Roadmap
- Productivity history and charts
- Saved filter presets
- Optional cloud synchronization
