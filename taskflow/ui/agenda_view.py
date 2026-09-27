from datetime import date, timedelta

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QScrollArea


class AgendaTimeline(QWidget):
    taskActivated = Signal(int)

    START_HOUR = 7
    END_HOUR = 23
    HOUR_HEIGHT = 76
    LEFT_LABEL = 72
    TASK_X = 118
    ALL_DAY_HEIGHT = 74

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_day_height = self.ALL_DAY_HEIGHT
        self.setMinimumHeight(
            self._all_day_height + (self.END_HOUR - self.START_HOUR) * self.HOUR_HEIGHT
        )
        self.setMouseTracking(True)
        self._tasks = []
        self._rects = {}

    def set_tasks(self, tasks):
        self._tasks = list(tasks)
        self._rebuild_rects()
        self.update()

    @staticmethod
    def _minutes(value):
        hours, minutes = map(int, value.split(":"))
        return hours * 60 + minutes

    def _rebuild_rects(self):
        self._rects = {}
        width = max(420, self.width() - self.TASK_X - 34)
        for task in self._tasks:
            if not task["start_time"] or not task["end_time"]:
                continue
            try:
                start = self._minutes(task["start_time"])
                end = max(start + 30, self._minutes(task["end_time"]))
            except (TypeError, ValueError):
                continue
            y = self.ALL_DAY_HEIGHT + (start - self.START_HOUR * 60) * self.HOUR_HEIGHT / 60
            h = max(42, (end - start) * self.HOUR_HEIGHT / 60 - 8)
            self._rects[task["id"]] = QRectF(self.TASK_X, y + 4, width, h)

    def resizeEvent(self, event):
        self._rebuild_rects()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background = self.palette().window().color()
        text = self.palette().windowText().color()
        muted = QColor(text)
        muted.setAlpha(110)
        grid = QColor(text)
        grid.setAlpha(22)
        grid_strong = QColor(text)
        grid_strong.setAlpha(35)
        accent = QColor("#ff8585")

        painter.fillRect(self.rect(), background)

        # All-day area
        painter.setPen(QPen(grid_strong, 1))
        painter.drawLine(self.TASK_X, self.ALL_DAY_HEIGHT, self.width(), self.ALL_DAY_HEIGHT)
        painter.setPen(QPen(muted, 1))
        painter.drawText(20, 31, "ALL DAY")

        all_day = [t for t in self._tasks if not t["start_time"] or not t["end_time"]]
        self._all_day_height = max(self.ALL_DAY_HEIGHT, 16 + len(all_day) * 48)
        self.setMinimumHeight(
            self._all_day_height + (self.END_HOUR - self.START_HOUR) * self.HOUR_HEIGHT
        )
        painter.setPen(QPen(grid_strong, 1))
        painter.drawLine(self.TASK_X, self._all_day_height, self.width(), self._all_day_height)
        y = 10
        for task in all_day:
            rect = QRectF(self.TASK_X, y, max(260, self.width() - self.TASK_X - 34), 42)
            self._rects[task["id"]] = rect
            painter.setBrush(QBrush(QColor("#272b35")))
            painter.setPen(QPen(QColor("#454b58"), 1))
            painter.drawRoundedRect(rect, 10, 10)
            painter.setPen(QPen(text, 1))
            painter.drawText(int(rect.x() + 14), int(rect.y() + 27), task["title"])
            y += 48

        # Hour grid
        for hour in range(self.START_HOUR, self.END_HOUR + 1):
            y = self._all_day_height + (hour - self.START_HOUR) * self.HOUR_HEIGHT
            painter.setPen(QPen(grid_strong, 1))
            painter.drawLine(self.LEFT_LABEL, int(y), self.width(), int(y))
            painter.setPen(QPen(muted, 1))
            painter.drawText(20, int(y + 5), f"{hour:02d}:00")
            if hour < self.END_HOUR:
                half = y + self.HOUR_HEIGHT / 2
                painter.setPen(QPen(grid, 1))
                painter.drawLine(self.LEFT_LABEL, int(half), self.width(), int(half))

        # Task blocks
        for task in self._tasks:
            if task["id"] not in self._rects or not task["start_time"] or not task["end_time"]:
                continue
            rect = self._rects[task["id"]]
            completed = bool(task["completed"])
            priority = task["priority"]
            if completed:
                fill = QColor("#343841")
                border = QColor("#555b66")
            elif priority == "high":
                fill = QColor("#5b2f3f")
                border = QColor("#ff8585")
            elif priority == "medium":
                fill = QColor("#353b55")
                border = QColor("#7e8dff")
            else:
                fill = QColor("#303e45")
                border = QColor("#62c4b2")

            painter.setBrush(QBrush(fill))
            painter.setPen(QPen(border, 1.5))
            painter.drawRoundedRect(rect, 12, 12)

            painter.setPen(QPen(text if not completed else muted, 1))
            title = task["title"]
            if rect.height() > 62:
                title += f"\n{task['start_time']} – {task['end_time']}"
            painter.drawText(
                int(rect.x() + 14),
                int(rect.y() + 14),
                int(rect.width() - 28),
                int(rect.height() - 18),
                Qt.TextFlag.TextWordWrap,
                title,
            )

            if task["category"] and rect.height() > 82:
                painter.setPen(QPen(muted, 1))
                painter.drawText(
                    int(rect.x() + 14),
                    int(rect.bottom() - 13),
                    int(rect.width() - 28),
                    16,
                    Qt.TextFlag.TextSingleLine,
                    task["category"],
                )

    def mouseDoubleClickEvent(self, event):
        pos = event.position()
        for task_id, rect in self._rects.items():
            if rect.contains(pos):
                self.taskActivated.emit(task_id)
                return
        super().mouseDoubleClickEvent(event)


class AgendaView(QWidget):
    taskActivated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_date = date.today()
        self._tasks = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setObjectName("pageTitle")
        header.addWidget(self.month_label)
        header.addStretch()

        previous = QPushButton("‹")
        previous.setObjectName("iconButton")
        previous.clicked.connect(lambda: self._shift_date(-1))
        next_button = QPushButton("›")
        next_button.setObjectName("iconButton")
        next_button.clicked.connect(lambda: self._shift_date(1))
        today = QPushButton("Today")
        today.clicked.connect(self._go_today)
        header.addWidget(previous)
        header.addWidget(today)
        header.addWidget(next_button)
        root.addLayout(header)

        self.day_strip = QHBoxLayout()
        self.day_strip.setSpacing(8)
        root.addLayout(self.day_strip)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.timeline = AgendaTimeline()
        self.timeline.taskActivated.connect(self.taskActivated)
        self.scroll.setWidget(self.timeline)
        root.addWidget(self.scroll, 1)

        self._rebuild_day_strip()
        self._update_header()

    def set_date(self, value: date):
        self.selected_date = value
        self._update_header()
        self._rebuild_day_strip()

    def set_tasks(self, tasks):
        self._tasks = list(tasks)
        self.timeline.set_tasks(self._tasks)

    def _shift_date(self, days):
        self.set_date(self.selected_date + timedelta(days=days))

    def _go_today(self):
        self.set_date(date.today())

    def _update_header(self):
        self.month_label.setText(self.selected_date.strftime("%B %Y"))

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _rebuild_day_strip(self):
        self._clear_layout(self.day_strip)
        monday = self.selected_date - timedelta(days=(self.selected_date.weekday() + 1) % 7)
        for offset in range(7):
            current = monday + timedelta(days=offset)
            button = QPushButton()
            button.setCheckable(True)
            button.setChecked(current == self.selected_date)
            button.setObjectName("dayButton")
            button.setText(f"{current.strftime('%a')}\n{current.day}")
            button.clicked.connect(lambda checked, value=current: self.set_date(value))
            self.day_strip.addWidget(button, 1)
