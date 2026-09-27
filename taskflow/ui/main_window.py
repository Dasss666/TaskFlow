from datetime import date, timedelta
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget,
    QTimeEdit, QVBoxLayout, QWidget
)
from taskflow.database import Database
from taskflow.services.data_transfer import export_tasks, import_tasks
from taskflow.services.notifications import NotificationService
from taskflow.ui.week_view import WeekView

CATEGORIES = ["Personal", "University", "Work", "Health", "Projects"]
PRIORITIES = ["low", "medium", "high"]
RECURRENCES = ["none", "daily", "weekly", "monthly"]


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("Edit task" if task else "New task")
        self.setMinimumWidth(470)

        form = QFormLayout(self)
        self.title = QLineEdit()
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(80)
        self.date = QCalendarWidget()
        self.date.setSelectedDate(QDate.currentDate())

        self.all_day = QCheckBox("All day")
        self.all_day.toggled.connect(self._toggle_time_fields)

        self.start = QTimeEdit()
        self.start.setDisplayFormat("HH:mm")
        self.end = QTimeEdit()
        self.end.setDisplayFormat("HH:mm")

        self.priority = QComboBox()
        self.priority.addItems(PRIORITIES)
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(CATEGORIES)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("study, exam, urgent")
        self.recurrence = QComboBox()
        self.recurrence.addItems(RECURRENCES)

        form.addRow("Title *", self.title)
        form.addRow("Description", self.description)
        form.addRow("Date", self.date)
        form.addRow("Schedule", self.all_day)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Start"))
        time_row.addWidget(self.start)
        time_row.addWidget(QLabel("End"))
        time_row.addWidget(self.end)
        form.addRow("", time_row)

        form.addRow("Priority", self.priority)
        form.addRow("Category", self.category)
        form.addRow("Tags", self.tags)
        form.addRow("Repeat", self.recurrence)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if task:
            self.title.setText(task["title"])
            self.description.setPlainText(task["description"] or "")
            if task["due_date"]:
                self.date.setSelectedDate(QDate.fromString(task["due_date"], "yyyy-MM-dd"))

            start = task["start_time"] or ""
            end = task["end_time"] or ""
            self.all_day.setChecked(not start or not end or (start == "00:00" and end == "00:00"))
            if start and start != "00:00":
                self.start.setTime(QTime.fromString(start, "HH:mm"))
            if end and end != "00:00":
                self.end.setTime(QTime.fromString(end, "HH:mm"))

            self.priority.setCurrentText(task["priority"])
            self.category.setCurrentText(task["category"] or "Personal")
            self.tags.setText(task["tags"] or "")
            self.recurrence.setCurrentText(task["recurrence"] or "none")

    def _toggle_time_fields(self, checked):
        self.start.setEnabled(not checked)
        self.end.setEnabled(not checked)

    def values(self):
        return {
            "title": self.title.text().strip(),
            "description": self.description.toPlainText().strip(),
            "due_date": self.date.selectedDate().toString("yyyy-MM-dd"),
            "start_time": None if self.all_day.isChecked() else self.start.time().toString("HH:mm"),
            "end_time": None if self.all_day.isChecked() else self.end.time().toString("HH:mm"),
            "priority": self.priority.currentText(),
            "category": self.category.currentText().strip() or "Personal",
            "tags": self.tags.text().strip(),
            "recurrence": self.recurrence.currentText(),
        }

    def accept(self):
        if not self.title.text().strip():
            QMessageBox.warning(self, "TaskFlow", "A task title is required.")
            return
        if not self.all_day.isChecked() and self.end.time() <= self.start.time():
            QMessageBox.warning(self, "TaskFlow", "End time must be after start time.")
            return
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        self.setWindowTitle("TaskFlow")
        self.resize(1200, 780)
        self._build_menu()
        self._build_ui()
        self._apply_theme()
        self.notifications = NotificationService(self, self.database)
        self.refresh()

    def _build_menu(self):
        task_menu = self.menuBar().addMenu("Task")
        new_action = QAction("New task", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_task)
        task_menu.addAction(new_action)

        data_menu = self.menuBar().addMenu("Data")
        export_action = QAction("Export JSON...", self)
        export_action.triggered.connect(self.export_data)
        import_action = QAction("Import JSON...", self)
        import_action.triggered.connect(self.import_data)
        data_menu.addAction(export_action)
        data_menu.addAction(import_action)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("TaskFlow")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tasks, tags, categories...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.search_changed)
        header.addWidget(self.search, 1)

        add = QPushButton("+ New task")
        add.clicked.connect(self.new_task)
        header.addWidget(add)
        outer.addLayout(header)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        tasks_page = QWidget()
        layout = QVBoxLayout(tasks_page)
        layout.addWidget(QLabel("All tasks"))
        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.task_list)

        actions = QHBoxLayout()
        done = QPushButton("✓ Toggle complete")
        done.clicked.connect(self.toggle_selected)
        actions.addWidget(done)
        edit = QPushButton("Edit")
        edit.clicked.connect(self.edit_selected)
        actions.addWidget(edit)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete_selected)
        actions.addWidget(delete)
        layout.addLayout(actions)
        self.stack.addWidget(tasks_page)

        agenda_page = QWidget()
        layout = QVBoxLayout(agenda_page)
        layout.addWidget(QLabel("Daily agenda"))
        self.agenda_date = QCalendarWidget()
        self.agenda_date.setMaximumHeight(210)
        self.agenda_date.selectionChanged.connect(self.refresh_agenda)
        layout.addWidget(self.agenda_date)
        self.agenda_list = QListWidget()
        self.agenda_list.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.agenda_list)
        self.stack.addWidget(agenda_page)

        week_page = QWidget()
        layout = QVBoxLayout(week_page)
        week_header = QHBoxLayout()
        self.week_title = QLabel()
        week_header.addWidget(self.week_title)
        week_header.addStretch()
        layout.addLayout(week_header)

        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.week_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.week_view = WeekView()
        self.week_view.setMinimumWidth(900)
        self.week_view.taskActivated.connect(self.edit_task_by_id)
        self.week_view.taskMoved.connect(self.move_task_from_calendar)
        self.week_view.taskResized.connect(self.resize_task_from_calendar)
        self.week_scroll.setWidget(self.week_view)
        layout.addWidget(self.week_scroll)
        self.stack.addWidget(week_page)

        calendar_page = QWidget()
        layout = QVBoxLayout(calendar_page)
        layout.addWidget(QLabel("Monthly calendar"))
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.refresh_calendar)
        layout.addWidget(self.calendar)
        self.calendar_tasks = QListWidget()
        self.calendar_tasks.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.calendar_tasks)
        self.stack.addWidget(calendar_page)

        nav = QHBoxLayout()
        for label, index in [
            ("📋 Tasks", 0),
            ("📅 Agenda", 1),
            ("🗓 Week", 2),
            ("📆 Calendar", 3),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked, i=index: self.show_page(i))
            nav.addWidget(button)
        outer.addLayout(nav)

    def _apply_theme(self):
        self.setStyleSheet("""
        QWidget { font-size: 14px; }
        QMainWindow { background: #10131a; }
        QLabel { color: #e7eaf0; }
        #appTitle { font-size: 28px; font-weight: 700; color: #9d7cff; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget {
            background:#181c25;color:#e7eaf0;border:1px solid #303746;border-radius:8px;padding:8px;
        }
        QPushButton {
            background:#252b38;color:#e7eaf0;border:1px solid #394152;border-radius:8px;padding:9px 14px;
        }
        QPushButton:hover { background:#303746; }
        QCalendarWidget QWidget { background:#181c25;color:#e7eaf0; }
        QCalendarWidget QAbstractItemView { selection-background-color:#6d4aff; }
        QMenuBar,QMenu { background:#141820;color:#e7eaf0; }
        QScrollArea { border: 1px solid #303746; border-radius: 8px; background: #11151d; }
        """)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.refresh_agenda()
        elif index == 2:
            self.refresh_week()
        elif index == 3:
            self.refresh_calendar()

    def make_item(self, task):
        marker = "✓" if task["completed"] else "○"
        if task["start_time"] and task["end_time"]:
            time_text = f"  {task['start_time']}–{task['end_time']}"
        else:
            time_text = "  All day"
        repeat = f" ↻{task['recurrence']}" if task["recurrence"] != "none" else ""
        item = QListWidgetItem(
            f"{marker}  {task['title']}{time_text}  [{task['category']}]{repeat}"
        )
        item.setData(Qt.ItemDataRole.UserRole, task["id"])
        item.setToolTip(
            f"Priority: {task['priority']}\n"
            f"Tags: {task['tags'] or '-'}\n"
            f"{task['description'] or ''}"
        )
        if task["completed"]:
            item.setForeground(Qt.GlobalColor.gray)
        return item

    def populate(self, list_widget, tasks):
        list_widget.clear()
        if not tasks:
            list_widget.addItem("Nothing scheduled.")
            return
        for task in tasks:
            list_widget.addItem(self.make_item(task))

    def refresh(self):
        self.refresh_tasks()
        self.refresh_agenda()
        self.refresh_week()
        self.refresh_calendar()

    def refresh_tasks(self):
        tasks = (
            self.database.search_tasks(self.search.text())
            if self.search.text().strip()
            else self.database.list_tasks()
        )
        self.populate(self.task_list, tasks)

    def refresh_agenda(self):
        q = self.agenda_date.selectedDate()
        self.populate(
            self.agenda_list,
            self.database.tasks_for_date(date(q.year(), q.month(), q.day())),
        )

    def refresh_week(self):
        q = self.agenda_date.selectedDate()
        selected = date(q.year(), q.month(), q.day())
        start = selected - timedelta(days=selected.weekday())
        end = start + timedelta(days=6)
        self.week_title.setText(
            f"Week of {start.strftime('%d %B %Y')}  •  Drag events to reschedule"
        )
        tasks = self.database.tasks_for_range(start, end)
        self.week_view.set_week(start, tasks)

    def refresh_calendar(self):
        q = self.calendar.selectedDate()
        self.populate(
            self.calendar_tasks,
            self.database.tasks_for_date(date(q.year(), q.month(), q.day())),
        )

    def search_changed(self):
        self.refresh_tasks()

    def new_task(self):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_task(**dialog.values())
            self.refresh()

    def selected_id(self):
        item = self.task_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def toggle_selected(self):
        task_id = self.selected_id()
        if task_id is not None:
            task = self.database.get_task(task_id)
            self.database.update_task(task_id, completed=not bool(task["completed"]))
            self.refresh()

    def edit_selected(self):
        item = self.task_list.currentItem()
        if item:
            self.edit_item(item)

    def edit_item(self, item):
        task_id = item.data(Qt.ItemDataRole.UserRole)
        self.edit_task_by_id(task_id)

    def edit_task_by_id(self, task_id):
        task = self.database.get_task(task_id)
        if not task:
            return
        dialog = TaskDialog(self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.update_task(task["id"], **dialog.values())
            self.refresh()

    def move_task_from_calendar(self, task_id, new_date, start_time, end_time):
        task = self.database.get_task(task_id)
        if not task:
            return
        self.database.update_task(
            task_id,
            due_date=new_date,
            start_time=start_time,
            end_time=end_time,
        )
        self.refresh()

    def resize_task_from_calendar(self, task_id, start_time, end_time):
        task = self.database.get_task(task_id)
        if not task:
            return
        self.database.update_task(task_id, start_time=start_time, end_time=end_time)
        self.refresh()

    def delete_selected(self):
        task_id = self.selected_id()
        if task_id is None:
            return
        task = self.database.get_task(task_id)
        if QMessageBox.question(
            self, "Delete task", f"Delete '{task['title']}'?"
        ) == QMessageBox.StandardButton.Yes:
            self.database.delete_task(task_id)
            self.refresh()

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export tasks", "taskflow-export.json", "JSON files (*.json)"
        )
        if path:
            export_tasks(self.database, path)

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import tasks", "", "JSON files (*.json)"
        )
        if path:
            try:
                count = import_tasks(self.database, path)
                self.refresh()
                QMessageBox.information(self, "TaskFlow", f"Imported {count} tasks.")
            except Exception as exc:
                QMessageBox.critical(self, "Import failed", str(exc))

    def closeEvent(self, event):
        self.database.close()
        event.accept()
