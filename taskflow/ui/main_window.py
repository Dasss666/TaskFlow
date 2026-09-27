from datetime import date, timedelta
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCalendarWidget, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QStackedWidget,
    QTimeEdit, QVBoxLayout, QWidget
)
from taskflow.database import Database
from taskflow.services.data_transfer import export_tasks, import_tasks
from taskflow.services.notifications import NotificationService

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
        self.start = QTimeEdit()
        self.start.setDisplayFormat("HH:mm")
        self.end = QTimeEdit()
        self.end.setDisplayFormat("HH:mm")
        self.priority = QComboBox(); self.priority.addItems(PRIORITIES)
        self.category = QComboBox(); self.category.setEditable(True); self.category.addItems(CATEGORIES)
        self.tags = QLineEdit(); self.tags.setPlaceholderText("study, exam, urgent")
        self.recurrence = QComboBox(); self.recurrence.addItems(RECURRENCES)
        form.addRow("Title *", self.title)
        form.addRow("Description", self.description)
        form.addRow("Date", self.date)
        form.addRow("Start", self.start)
        form.addRow("End", self.end)
        form.addRow("Priority", self.priority)
        form.addRow("Category", self.category)
        form.addRow("Tags", self.tags)
        form.addRow("Repeat", self.recurrence)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        if task:
            self.title.setText(task["title"])
            self.description.setPlainText(task["description"] or "")
            if task["due_date"]: self.date.setSelectedDate(QDate.fromString(task["due_date"], "yyyy-MM-dd"))
            if task["start_time"]: self.start.setTime(self.start.time().fromString(task["start_time"], "HH:mm"))
            if task["end_time"]: self.end.setTime(self.end.time().fromString(task["end_time"], "HH:mm"))
            self.priority.setCurrentText(task["priority"])
            self.category.setCurrentText(task["category"] or "Personal")
            self.tags.setText(task["tags"] or "")
            self.recurrence.setCurrentText(task["recurrence"] or "none")

    def values(self):
        return {
            "title": self.title.text().strip(),
            "description": self.description.toPlainText().strip(),
            "due_date": self.date.selectedDate().toString("yyyy-MM-dd"),
            "start_time": self.start.time().toString("HH:mm"),
            "end_time": self.end.time().toString("HH:mm"),
            "priority": self.priority.currentText(),
            "category": self.category.currentText().strip() or "Personal",
            "tags": self.tags.text().strip(),
            "recurrence": self.recurrence.currentText(),
        }

    def accept(self):
        if not self.title.text().strip():
            QMessageBox.warning(self, "TaskFlow", "A task title is required.")
            return
        if self.end.time() < self.start.time():
            QMessageBox.warning(self, "TaskFlow", "End time cannot be before start time.")
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
        new_action = QAction("New task", self); new_action.setShortcut("Ctrl+N"); new_action.triggered.connect(self.new_task)
        task_menu.addAction(new_action)
        data_menu = self.menuBar().addMenu("Data")
        export_action = QAction("Export JSON...", self); export_action.triggered.connect(self.export_data)
        import_action = QAction("Import JSON...", self); import_action.triggered.connect(self.import_data)
        data_menu.addAction(export_action); data_menu.addAction(import_action)

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root); outer = QVBoxLayout(root)
        header = QHBoxLayout()
        title = QLabel("TaskFlow"); title.setObjectName("appTitle"); header.addWidget(title); header.addStretch()
        self.search = QLineEdit(); self.search.setPlaceholderText("Search tasks, tags, categories..."); self.search.setClearButtonEnabled(True); self.search.textChanged.connect(self.search_changed)
        header.addWidget(self.search, 1)
        add = QPushButton("+ New task"); add.clicked.connect(self.new_task); header.addWidget(add)
        outer.addLayout(header)
        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)

        tasks_page = QWidget(); l = QVBoxLayout(tasks_page)
        l.addWidget(QLabel("All tasks"))
        self.task_list = QListWidget(); self.task_list.itemDoubleClicked.connect(self.edit_item); l.addWidget(self.task_list)
        actions = QHBoxLayout()
        done = QPushButton("✓ Toggle complete"); done.clicked.connect(self.toggle_selected); actions.addWidget(done)
        edit = QPushButton("Edit"); edit.clicked.connect(self.edit_selected); actions.addWidget(edit)
        delete = QPushButton("Delete"); delete.clicked.connect(self.delete_selected); actions.addWidget(delete)
        l.addLayout(actions); self.stack.addWidget(tasks_page)

        agenda_page = QWidget(); l = QVBoxLayout(agenda_page)
        l.addWidget(QLabel("Daily agenda")); self.agenda_date = QCalendarWidget(); self.agenda_date.setMaximumHeight(210); self.agenda_date.selectionChanged.connect(self.refresh_agenda); l.addWidget(self.agenda_date)
        self.agenda_list = QListWidget(); self.agenda_list.itemDoubleClicked.connect(self.edit_item); l.addWidget(self.agenda_list); self.stack.addWidget(agenda_page)

        week_page = QWidget(); l = QVBoxLayout(week_page)
        self.week_title = QLabel(); l.addWidget(self.week_title)
        self.week_list = QListWidget(); self.week_list.itemDoubleClicked.connect(self.edit_item); l.addWidget(self.week_list); self.stack.addWidget(week_page)

        calendar_page = QWidget(); l = QVBoxLayout(calendar_page)
        l.addWidget(QLabel("Monthly calendar")); self.calendar = QCalendarWidget(); self.calendar.selectionChanged.connect(self.refresh_calendar); l.addWidget(self.calendar)
        self.calendar_tasks = QListWidget(); self.calendar_tasks.itemDoubleClicked.connect(self.edit_item); l.addWidget(self.calendar_tasks); self.stack.addWidget(calendar_page)

        nav = QHBoxLayout()
        for label,index in [("📋 Tasks",0),("📅 Agenda",1),("🗓 Week",2),("📆 Calendar",3)]:
            b=QPushButton(label); b.clicked.connect(lambda checked,i=index:self.show_page(i)); nav.addWidget(b)
        outer.addLayout(nav)

    def _apply_theme(self):
        self.setStyleSheet("""
        QWidget { font-size: 14px; }
        QMainWindow { background: #10131a; }
        QLabel { color: #e7eaf0; }
        #appTitle { font-size: 28px; font-weight: 700; color: #9d7cff; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget { background:#181c25;color:#e7eaf0;border:1px solid #303746;border-radius:8px;padding:8px; }
        QPushButton { background:#252b38;color:#e7eaf0;border:1px solid #394152;border-radius:8px;padding:9px 14px; }
        QPushButton:hover { background:#303746; }
        QCalendarWidget QWidget { background:#181c25;color:#e7eaf0; }
        QCalendarWidget QAbstractItemView { selection-background-color:#6d4aff; }
        QMenuBar,QMenu { background:#141820;color:#e7eaf0; }
        """)

    def show_page(self,index):
        self.stack.setCurrentIndex(index)
        if index==1: self.refresh_agenda()
        elif index==2: self.refresh_week()
        elif index==3: self.refresh_calendar()

    def make_item(self,task):
        marker="✓" if task["completed"] else "○"
        time=f"  {task['start_time']}" if task["start_time"] else ""
        repeat=f" ↻{task['recurrence']}" if task["recurrence"]!="none" else ""
        item=QListWidgetItem(f"{marker}  {task['title']}{time}  [{task['category']}]{repeat}")
        item.setData(Qt.ItemDataRole.UserRole,task["id"])
        item.setToolTip(f"Priority: {task['priority']}\nTags: {task['tags'] or '-'}\n{task['description'] or ''}")
        if task["completed"]: item.setForeground(Qt.GlobalColor.gray)
        return item

    def populate(self,list_widget,tasks):
        list_widget.clear()
        if not tasks:
            list_widget.addItem("Nothing scheduled.")
            return
        for task in tasks: list_widget.addItem(self.make_item(task))

    def refresh(self):
        self.refresh_tasks(); self.refresh_agenda(); self.refresh_week(); self.refresh_calendar()

    def refresh_tasks(self):
        tasks=self.database.search_tasks(self.search.text()) if self.search.text().strip() else self.database.list_tasks()
        self.populate(self.task_list,tasks)

    def refresh_agenda(self):
        q=self.agenda_date.selectedDate(); self.populate(self.agenda_list,self.database.tasks_for_date(date(q.year(),q.month(),q.day())))

    def refresh_week(self):
        q=self.agenda_date.selectedDate(); selected=date(q.year(),q.month(),q.day())
        start=selected-timedelta(days=selected.weekday()); end=start+timedelta(days=6)
        self.week_title.setText(f"Week of {start.strftime('%d %B %Y')}")
        tasks=self.database.tasks_for_range(start,end)
        self.populate(self.week_list,tasks)

    def refresh_calendar(self):
        q=self.calendar.selectedDate(); self.populate(self.calendar_tasks,self.database.tasks_for_date(date(q.year(),q.month(),q.day())))

    def search_changed(self): self.refresh_tasks()

    def new_task(self):
        d=TaskDialog(self)
        if d.exec()==QDialog.DialogCode.Accepted:
            self.database.add_task(**d.values()); self.refresh()

    def selected_id(self):
        item=self.task_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def toggle_selected(self):
        task_id=self.selected_id()
        if task_id is not None:
            task=self.database.get_task(task_id); self.database.update_task(task_id,completed=not bool(task["completed"])); self.refresh()

    def edit_selected(self):
        item=self.task_list.currentItem()
        if item: self.edit_item(item)

    def edit_item(self,item):
        task=self.database.get_task(item.data(Qt.ItemDataRole.UserRole))
        if not task: return
        d=TaskDialog(self,task)
        if d.exec()==QDialog.DialogCode.Accepted:
            self.database.update_task(task["id"],**d.values()); self.refresh()

    def delete_selected(self):
        task_id=self.selected_id()
        if task_id is None: return
        task=self.database.get_task(task_id)
        if QMessageBox.question(self,"Delete task",f"Delete '{task['title']}'?")==QMessageBox.StandardButton.Yes:
            self.database.delete_task(task_id); self.refresh()

    def export_data(self):
        path,_=QFileDialog.getSaveFileName(self,"Export tasks","taskflow-export.json","JSON files (*.json)")
        if path: export_tasks(self.database,path)

    def import_data(self):
        path,_=QFileDialog.getOpenFileName(self,"Import tasks","","JSON files (*.json)")
        if path:
            try:
                count=import_tasks(self.database,path); self.refresh()
                QMessageBox.information(self,"TaskFlow",f"Imported {count} tasks.")
            except Exception as exc:
                QMessageBox.critical(self,"Import failed",str(exc))

    def closeEvent(self,event):
        self.database.close(); event.accept()
