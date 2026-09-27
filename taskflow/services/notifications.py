from datetime import datetime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QSystemTrayIcon

class NotificationService:
    def __init__(self, window, database):
        self.window = window
        self.database = database
        self.tray = QSystemTrayIcon(window)
        self.tray.setIcon(window.windowIcon())
        self.tray.setToolTip("TaskFlow")
        self.tray.show()
        self.timer = QTimer(window)
        self.timer.timeout.connect(self.check)
        self.timer.start(30000)
        self._shown = set()

    def check(self):
        now = datetime.now()
        key = now.strftime("%Y-%m-%d %H:%M")
        for task in self.database.tasks_for_date(now.date()):
            if task["completed"] or not task["start_time"]:
                continue
            if task["start_time"] == now.strftime("%H:%M") and (task["id"], key) not in self._shown:
                self._shown.add((task["id"], key))
                self.tray.showMessage("TaskFlow", task["title"], QSystemTrayIcon.MessageIcon.Information, 10000)
