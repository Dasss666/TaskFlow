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
- Structured-style agenda cards with proportional duration, category rail, icon, metadata, tags and completion control
- Agenda header with month selector, week navigation, selected-day highlight and today indicator
- Smooth agenda transitions, week navigation gestures and animated auto-scroll to the current time
- Manage section for categories with CRUD operations plus custom color and icon settings
- Manage section for tags with CRUD operations
- Category styling automatically applied to Task Cards, Smart Task Icons and Agenda cards
- Category-dependent predefined task titles with CRUD management and task-dialog selection
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
- AI Assistant with Gemini Free Tier integration
- Voice commands from the 🎙 microphone button
- AI CRUD operations limited to tasks, categories, tags and title presets
- AI context uses the current TaskFlow data snapshot for resolving existing items
- Destructive AI operations require explicit confirmation
- Gemini API key stored in the Windows credential store via keyring

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

## AI Assistant

TaskFlow 0.11.0 includes an optional Gemini-powered assistant. Configure a Gemini API key from the **AI settings** button in the assistant window. The assistant can create, modify and delete tasks, categories, tags and category-specific title presets. It cannot access arbitrary files, execute code, browse the web or change other application settings.

The microphone button records a short command locally and sends the audio to Gemini for interpretation. Gemini supports common audio formats including M4A, WAV and MP3. The API's current Free Tier includes free usage for supported models, subject to Google's quotas and pricing rules.

## Roadmap
- Productivity history and charts
- Saved filter presets
- Optional cloud synchronization
