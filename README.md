# TaskFlow

A Windows desktop task manager and personal agenda built with Python, PySide6 and SQLite.

## Implemented
- Task creation/editing/deletion
- Completion state
- Priority, category and tags
- Date and start/end time
- Responsive collapsible navigation: Tasks, Dashboard and Agenda
- Tasks grouped by Today, Tomorrow and following dates
- Interactive daily agenda with week date strip and time timeline
- Floating + action for quick task creation on the selected agenda day
- Animated circular completion controls, category colors and tag badges
- Structured-inspired Smart Task Icons selected automatically from task title, tags, description and category
- Agenda current-time indicator, overlap-aware task layout, drag-to-move and edge-resize
- Responsive sidebar and automatic compact layout on smaller windows
- Advanced task filters (status, priority, category, recurrence and date range)
- Search
- Customizable themes: Midnight, Light, Cyberpunk and Ocean
- Persistent theme preference
- Recurring tasks: daily, weekly and monthly with generated future occurrences
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

## Current UI direction
The 0.3.0 interface focuses the main workflow on Tasks, Dashboard and Agenda. The Dashboard remains the productivity overview, while Agenda provides a responsive day timeline inspired by modern calendar/task-planning applications.

## Roadmap
- Productivity history and charts
- Saved filter presets
- Optional cloud synchronization
