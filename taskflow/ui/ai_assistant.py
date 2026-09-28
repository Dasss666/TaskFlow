from __future__ import annotations
import tempfile
from datetime import date
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, QDateTime
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout
from taskflow.services.ai.agent import TaskFlowAgent
from taskflow.services.ai.settings import get_api_key, set_api_key
from taskflow.services.ai.voice import VoiceRecorder
from taskflow.services.recurrence import materialize_recurring_tasks

class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)

class _AgentJob(QRunnable):
    def __init__(self, api_key, text, context, audio_path=None):
        super().__init__()
        self.api_key, self.text, self.context, self.audio_path = api_key, text, context, audio_path
        self.signals = _Signals()
    @Slot()
    def run(self):
        try:
            audio = Path(self.audio_path).read_bytes() if self.audio_path else None
            result = TaskFlowAgent(self.api_key).plan(self.text, self.context, audio, "audio/m4a")
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            if self.audio_path:
                try:
                    Path(self.audio_path).unlink(missing_ok=True)
                except OSError:
                    pass

class AIAssistantDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window, self.database = main_window, main_window.database
        self.setWindowTitle("TaskFlow AI Assistant")
        self.resize(760, 620)
        self.pool = QThreadPool.globalInstance()
        self.recorder = VoiceRecorder(self)
        self.recorder.started.connect(self._recording_started)
        self.recorder.stopped.connect(self._recording_stopped)
        self.recorder.error.connect(self._recording_error)
        self._recording_path, self._busy = None, False

        layout = QVBoxLayout(self)
        intro = QLabel("🎙 Speak or type a command. The assistant is restricted to TaskFlow tasks, categories, tags and title presets.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.status = QLabel("Ready")
        self.status.setObjectName("appSubtitle")
        layout.addWidget(self.status)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Es. Crea Analisi Matematica domani alle 15 per due ore...")
        self.input.returnPressed.connect(self.send_text)
        row.addWidget(self.input, 1)
        self.mic = QPushButton("🎙")
        self.mic.setMinimumWidth(54)
        self.mic.setToolTip("Start/stop voice command")
        self.mic.clicked.connect(self.toggle_recording)
        row.addWidget(self.mic)
        send = QPushButton("Send")
        send.clicked.connect(self.send_text)
        row.addWidget(send)
        settings = QPushButton("AI settings")
        settings.clicked.connect(self.configure_key)
        row.addWidget(settings)
        layout.addLayout(row)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        if not get_api_key():
            self.configure_key()

    def configure_key(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Gemini API key")
        form = QFormLayout(dialog)
        edit = QLineEdit(get_api_key())
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setPlaceholderText("Paste your Gemini API key")
        form.addRow("API key", edit)
        note = QLabel("The key is stored through the Windows credential store using keyring and is never written to the repository.")
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            set_api_key(edit.text())
            self.status.setText("Gemini API key saved securely.")

    def send_text(self):
        if not self._busy:
            text = self.input.text().strip()
            if text:
                self.input.clear()
                self._submit(text)

    def toggle_recording(self):
        if self._busy:
            return
        if self._recording_path:
            self.recorder.stop()
            return
        path = Path(tempfile.gettempdir()) / f"taskflow_ai_{QDateTime.currentDateTime().toMSecsSinceEpoch()}.m4a"
        self._recording_path = str(path)
        self.recorder.start(path)

    def _recording_started(self):
        self.mic.setText("⏹")
        self.status.setText("Listening… press the microphone again to stop.")
        self.input.setEnabled(False)

    def _recording_stopped(self, path):
        self._recording_path = None
        self.mic.setText("🎙")
        self.input.setEnabled(True)
        file = Path(path)
        if not file.exists() or file.stat().st_size == 0:
            self._recording_error("The microphone recording is empty or was not created.")
            return
        self.status.setText("Processing voice command…")
        self._submit("", path)

    def _recording_error(self, message):
        self._recording_path = None
        self.mic.setText("🎙")
        self.input.setEnabled(True)
        self._busy = False
        QMessageBox.warning(self, "TaskFlow AI", message)

    def _context(self):
        return {
            "today": date.today().isoformat(),
            "tasks": [dict(x) for x in self.database.list_tasks(True)[:100]],
            "categories": [dict(x) for x in self.database.list_categories()],
            "tags": [dict(x) for x in self.database.list_tags()],
            "title_presets": [dict(x) for x in self.database.list_title_presets()],
        }

    def _submit(self, text, audio_path=None):
        key = get_api_key()
        if not key:
            self.configure_key()
            key = get_api_key()
        if not key:
            self.status.setText("Gemini API key not configured.")
            return
        self._busy = True
        self.input.setEnabled(False)
        self.mic.setEnabled(False)
        self.status.setText("Thinking…")
        job = _AgentJob(key, text, self._context(), audio_path)
        job.signals.finished.connect(self._result)
        job.signals.failed.connect(self._failed)
        self.pool.start(job)

    def _result(self, result):
        self._busy = False
        self.input.setEnabled(True)
        self.mic.setEnabled(True)
        self.history.appendPlainText("AI: " + (result.get("text") or "I prepared the requested operation."))
        actions = result.get("actions", [])
        if not actions:
            self.status.setText("No TaskFlow operation was requested.")
            return
        safe = [a for a in actions if not a["name"].startswith("delete_")]
        destructive = [a for a in actions if a["name"].startswith("delete_")]
        for action in safe:
            try:
                self.history.appendPlainText("TaskFlow: " + self._execute_action(action))
            except Exception as exc:
                self.history.appendPlainText("TaskFlow error: " + str(exc))
        if destructive:
            answer = QMessageBox.question(
                self, "Confirm AI operation",
                "The assistant wants to perform:\n\n" + "\n".join(self._describe_action(a) for a in destructive)
                + "\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                for action in destructive:
                    try:
                        self.history.appendPlainText("TaskFlow: " + self._execute_action(action))
                    except Exception as exc:
                        self.history.appendPlainText("TaskFlow error: " + str(exc))
            else:
                self.history.appendPlainText("TaskFlow: destructive operation cancelled.")
        materialize_recurring_tasks(self.database)
        self.main_window.refresh()
        self.status.setText("Done.")

    def _describe_action(self, action):
        name, args = action["name"], action["args"]
        if name == "delete_task":
            row = self.database.get_task(int(args["task_id"]))
            return f"Delete task: {row['title'] if row else 'unknown task'}"
        if name == "delete_category":
            row = self.database.get_category(int(args["category_id"]))
            return f"Delete category: {row['name'] if row else 'unknown category'}"
        if name == "delete_tag":
            row = next((r for r in self.database.list_tags() if r["id"] == int(args["tag_id"])), None)
            return f"Delete tag: #{row['name'] if row else 'unknown tag'}"
        if name == "delete_title_preset":
            row = next((r for r in self.database.list_title_presets() if r["id"] == int(args["preset_id"])), None)
            return f"Delete title preset: {row['title'] if row else 'unknown title'}"
        return name

    def _execute_action(self, action):
        name, args = action["name"], dict(action["args"])
        if name == "create_task":
            category = args.get("category") or "Personal"
            if not any(r["name"] == category for r in self.database.list_categories()):
                raise ValueError(f"Category '{category}' does not exist. Create it first.")
            task_id = self.database.add_task(title=args["title"].strip(), description=args.get("description",""), due_date=args.get("due_date") or None, start_time=args.get("start_time") or None, end_time=args.get("end_time") or None, priority=args.get("priority") or "medium", category=category, tags=args.get("tags",""), recurrence=args.get("recurrence") or "none")
            return f"Created task #{task_id}: {args['title']}"
        if name == "update_task":
            task_id = int(args.pop("task_id"))
            if not self.database.get_task(task_id):
                raise ValueError(f"Task #{task_id} not found.")
            if "category" in args and not any(r["name"] == args["category"] for r in self.database.list_categories()):
                raise ValueError(f"Category '{args['category']}' does not exist.")
            self.database.update_task(task_id, **args)
            return f"Updated task #{task_id}"
        if name == "delete_task":
            task_id = int(args["task_id"])
            if not self.database.get_task(task_id):
                raise ValueError(f"Task #{task_id} not found.")
            self.database.delete_task(task_id)
            return f"Deleted task #{task_id}"
        if name == "create_category":
            category_id = self.database.add_category(args["name"])
            self.database.update_category_style(category_id, args.get("color") or "#9d7cff", args.get("icon") or "✓")
            return f"Created category: {args['name']}"
        if name == "update_category":
            category_id = int(args["category_id"])
            row = self.database.get_category(category_id)
            if not row:
                raise ValueError(f"Category #{category_id} not found.")
            if args.get("name"):
                self.database.update_category(category_id, args["name"])
            row = self.database.get_category(category_id)
            self.database.update_category_style(category_id, args.get("color", row["color"]), args.get("icon", row["icon"]))
            return f"Updated category: {row['name']}"
        if name == "delete_category":
            category_id = int(args["category_id"])
            row = self.database.get_category(category_id)
            if not row:
                raise ValueError(f"Category #{category_id} not found.")
            if row["name"] == "Personal":
                raise ValueError("Personal is the fallback category and cannot be deleted.")
            self.database.delete_category(category_id)
            return f"Deleted category: {row['name']}"
        if name == "create_tag":
            tag_id = self.database.add_tag(args["name"])
            return f"Created tag #{tag_id}: #{args['name'].lstrip('#')}"
        if name == "update_tag":
            self.database.update_tag(int(args["tag_id"]), args["name"])
            return f"Updated tag #{args['tag_id']}"
        if name == "delete_tag":
            self.database.delete_tag(int(args["tag_id"]))
            return f"Deleted tag #{args['tag_id']}"
        if name == "create_title_preset":
            category_id = int(args["category_id"])
            if not self.database.get_category(category_id):
                raise ValueError(f"Category #{category_id} not found.")
            preset_id = self.database.add_title_preset(category_id, args["title"])
            return f"Created title preset #{preset_id}: {args['title']}"
        if name == "update_title_preset":
            self.database.update_title_preset(int(args["preset_id"]), int(args["category_id"]), args["title"])
            return f"Updated title preset #{args['preset_id']}"
        if name == "delete_title_preset":
            self.database.delete_title_preset(int(args["preset_id"]))
            return f"Deleted title preset #{args['preset_id']}"
        raise ValueError(f"Unsupported AI operation: {name}")

    def _failed(self, message):
        self._busy = False
        self.input.setEnabled(True)
        self.mic.setEnabled(True)
        self.status.setText("Error.")
        self.history.appendPlainText("TaskFlow AI error: " + message)
