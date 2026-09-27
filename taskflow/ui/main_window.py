from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QVBoxLayout, QWidget
from taskflow.database import Database

class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("TaskFlow")
        self.resize(1000, 650)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        input_row = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("What needs to be done?")
        self.priority = QComboBox()
        self.priority.addItems(["low", "medium", "high"])
        add_button = QPushButton("Add task")
        add_button.clicked.connect(self.add_task)
        input_row.addWidget(self.title_input, 1)
        input_row.addWidget(self.priority)
        input_row.addWidget(add_button)
        layout.addLayout(input_row)
        self.task_list = QListWidget()
        self.task_list.itemChanged.connect(self.task_changed)
        layout.addWidget(self.task_list, 1)
        self.refresh_tasks()

    def add_task(self) -> None:
        title = self.title_input.text().strip()
        if not title:
            return
        self.database.add_task(title, priority=self.priority.currentText())
        self.title_input.clear()
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for task in self.database.list_tasks():
            item = QListWidgetItem(task["title"])
            item.setData(Qt.ItemDataRole.UserRole, task["id"])
            item.setCheckState(Qt.CheckState.Checked if task["completed"] else Qt.CheckState.Unchecked)
            item.setToolTip(f"Priority: {task['priority']}")
            self.task_list.addItem(item)
        self.task_list.blockSignals(False)

    def task_changed(self, item: QListWidgetItem) -> None:
        task_id = item.data(Qt.ItemDataRole.UserRole)
        completed = item.checkState() == Qt.CheckState.Checked
        self.database.set_completed(task_id, completed)
        self.refresh_tasks()
