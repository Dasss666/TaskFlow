import sys
from PySide6.QtWidgets import QApplication
from taskflow.database import Database
from taskflow.ui.main_window import MainWindow

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    app.setOrganizationName("Dasss666")
    database = Database()
    database.initialize()
    window = MainWindow(database)
    window.show()
    sys.exit(app.exec())
