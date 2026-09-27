import sys
from PySide6.QtWidgets import QApplication
from taskflow.database import Database
from taskflow.services.data_transfer import export_tasks, import_tasks
from taskflow.services.recurrence import materialize_recurring_tasks
from taskflow.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    app.setOrganizationName("Dasss666")

    database = Database()
    database.initialize()
    materialize_recurring_tasks(database)

    window = MainWindow(database)
    window.show()
    sys.exit(app.exec())
