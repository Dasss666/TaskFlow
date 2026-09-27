from datetime import date
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QCalendarWidget, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
    QStackedWidget, QTimeEdit, QVBoxLayout, QWidget
)

from taskflow.database import Database

CATEGORIES = ["Personal", "University", "Work", "Health", "Projects"]
PRIORITIES = ["low", "medium", "high"]

class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("Edit task" if task else "New task")
        self.setMinimumWidth(460)
        form = QFormLayout(self)

        self.title = QLineEdit()
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(90)
        self.date = QCalendarWidget()
        self.date.setSelectedDate(QDate.currentDate())
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

        form.addRow("Title *", self.title)
        form.addRow("Description", self.description)
        form.addRow("Date", self.date)
        form.addRow("Start", self.start)
        form.addRow("End", self.end)
        form.addRow("Priority", self.priority)
        form.addRow("Category", self.category)
        form.addRow("Tags", self.tags)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if task:
            self.title.setText(task["title"])
            self.description.setPlainText(task["description"] or "")
            if task["due_date"]:
                self.date.setSelectedDate(QDate.fromString(task["due_date"], "yyyy-MM-dd"))
            if task["start_time"]:
                self.start.setTime(self.start.time().fromString(task["start_time"], "HH:mm"))
            if task["end_time"]:
                self.end.setTime(self.end.time().fromString(task["end_time"], "HH:mm"))
            self.priority.setCurrentText(task["priority"])
            self.category.setCurrentText(task["category"] or "Personal")
            self.tags.setText(task["tags"] or "")

    def values(self) -> dict:
        selected = self.date.selectedDate()
        return {
            "title": self.title.text().strip(),
            "description": self.description.toPlainText().strip(),
            "due_date": selected.toString("yyyy-MM-dd"),
            "start_time": self.start.time().toString("HH:mm"),
            "end_time": self.end.time().toString("HH:mm"),
            "priority": self.priority.currentText(),
            "category": self.category.currentText().strip() or "Personal",
            "tags": self.tags.text().strip(),
        }

    def accept(self) -> None:
        if not self.title.text().strip():
            QMessageBox.warning(self, "TaskFlow", "A task title is required.")
            return
        super().accept()

class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("TaskFlow")
        self.resize(1180, 760)
        self._build_menu()
        self._build_ui()
        self._apply_theme()
        self.refresh()

    def _build_menu(self) -> None:
        new_action = QAction("New task", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_task)
        self.menuBar().addMenu("Task").addAction(new_action)

    def _build_ui(self) -> None:
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
        header.addWidget(self.search, 0)
        add = QPushButton("+ New task")
        add.clicked.connect(self.new_task)
        header.addWidget(add)
        outer.addLayout(header)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        tasks_page = QWidget()
        tasks_layout = QVBoxLayout(tasks_page)
        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(self.edit_item)
        tasks_layout.addWidget(QLabel("All tasks"))
        tasks_layout.addWidget(self.task_list)
        self.stack.addWidget(tasks_page)

        agenda_page = QWidget()
        agenda_layout = QVBoxLayout(agenda_page)
        self.agenda_date = QCalendarWidget()
        self.agenda_date.setMaximumHeight(220)
        self.agenda_date.selectionChanged.connect(self.refresh_agenda)
        agenda_layout.addWidget(QLabel("Agenda"))
        agenda_layout.addWidget(self.agenda_date)
        self.agenda_list = QListWidget()
        self.agenda_list.itemDoubleClicked.connect(self.edit_item)
        agenda_layout.addWidget(self.agenda_list)
        self.stack.addWidget(agenda_page)

        calendar_page = QWidget()
        calendar_layout = QVBoxLayout(calendar_page)
        calendar_layout.addWidget(QLabel("Calendar"))
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.calendar_selected)
        calendar_layout.addWidget(self.calendar)
        self.calendar_tasks = QListWidget()
        self.calendar_tasks.itemDoubleClicked.connect(self.edit_item)
        calendar_layout.addWidget(self.calendar_tasks)
        self.stack.addWidget(calendar_page)

        nav = QHBoxLayout()
        for label, index in [("📋 Tasks", 0), ("📅 Agenda", 1), ("🗓 Calendar", 2)]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, i=index: self.show_page(i))
            nav.addWidget(button)
            if index == 0:
                self.nav_tasks = button
        outer.addLayout(nav)

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QWidget { font-size: 14px; }
            QMainWindow { background: #10131a; }
            QLabel { color: #e7eaf0; }
            #appTitle { font-size: 28px; font-weight: 700; color: #9d7cff; }
            QLineEdit, QPlainTextEdit, QComboBox, QTimeEdit, QListWidget {
                background: #181c25; color: #e7eaf0; border: 1px solid #303746;
                border-radius: 8px; padding: 8px;
            }
            QPushButton {
                background: #252b38; color: #e7eaf0; border: 1px solid #394152;
                border-radius: 8px; padding: 9px 14px;
            }
            QPushButton:hover { background: #303746; }
            QCalendarWidget QWidget { background: #181c25; color: #e7eaf0; }
            QCalendarWidget QAbstractItemView { selection-background-color: #6d4aff; }
        """)

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.refresh_agenda()
        elif index == 2:
            self.refresh_calendar()

    def refresh(self) -> None:
        self.refresh_tasks()
        self.refresh_agenda()
        self.refresh_calendar()

    def make_item(self, task) -> QListWidgetItem:
        time = task["start_time"] or ""
        suffix = f"  {time}" if time else ""
        marker = "✓" if task["completed"] else "○"
        text = f"{marker}  {task['title']}{suffix}   [{task['category']}]"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, task["id"])
        item.setToolTip(
            f"Priority: {task['priority']}\n"
            f"Category: {task['category']}\n"
            f"Tags: {task['tags'] or '-'}\n"
            f"{task['description'] or ''}"
        )
        return item

    def refresh_tasks(self) -> None:
        tasks = self.database.search_tasks(self.search.text()) if self.search.text().strip() else self.database.list_tasks()
        self.task_list.clear()
        for task in tasks:
            self.task_list.addItem(self.make_item(task))

    def refresh_agenda(self) -> None:
        qdate = self.agenda_date.selectedDate()
        selected = date(qdate.year(), qdate.month(), qdate.day())
        self.agenda_list.clear()
        tasks = self.database.tasks_for_date(selected)
        if not tasks:
            self.agenda_list.addItem("No tasks scheduled for this day.")
        else:
            for task in tasks:
                self.agenda_list.addItem(self.make_item(task))

    def refresh_calendar(self) -> None:
        self.calendar_tasks.clear()
        qdate = self.calendar.selectedDate()
        selected = date(qdate.year(), qdate.month(), qdate.day())
        tasks = self.database.tasks_for_date(selected)
        for task in tasks:
            self.calendar_tasks.addItem(self.make_item(task))
        self._mark_calendar_dates()

    def _mark_calendar_dates(self) -> None:
        self.calendar.setDateTextFormat(QDate(), self.calendar.dateTextFormat(QDate()))
        # A full custom delegate can be added later; the selected-day task list is already live.

    def calendar_selected(self) -> None:
        self.refresh_calendar()

    def search_changed(self) -> None:
        self.refresh_tasks()

    def new_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_task(**dialog.values())
            self.refresh()

    def edit_item(self, item: QListWidgetItem) -> None:
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.database.get_task(task_id)
        if not task:
            return
        dialog = TaskDialog(self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.update_task(task_id, **dialog.values())
            self.refresh()

    def closeEvent(self, event) -> None:
        self.database.close()
        event.accept()
