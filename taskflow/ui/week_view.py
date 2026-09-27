from datetime import date, datetime, time, timedelta

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget, QToolTip


class WeekView(QWidget):
    taskActivated = Signal(int)
    taskMoved = Signal(int, str, str, str)
    taskResized = Signal(int, str, str)

    HEADER_H = 42
    ALL_DAY_H = 34
    HOUR_H = 64
    LABEL_W = 58
    START_HOUR = 7
    END_HOUR = 23
    MINUTE_STEP = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(self.HEADER_H + self.ALL_DAY_H + (self.END_HOUR - self.START_HOUR) * self.HOUR_H)
        self.setMouseTracking(True)
        self._week_start = date.today()
        self._tasks = []
        self._rects = {}
        self._drag = None

    def set_week(self, week_start: date, tasks):
        self._week_start = week_start
        self._tasks = tasks
        self._rebuild_geometry()
        self.update()

    def _rebuild_geometry(self):
        self._rects = {}
        timed = [t for t in self._tasks if self._has_time(t)]
        col_w = max(80, (self.width() - self.LABEL_W) / 7)
        for task in timed:
            try:
                day = date.fromisoformat(task["due_date"])
                start = self._parse_minutes(task["start_time"])
                end = self._parse_minutes(task["end_time"])
                if end <= start:
                    end = start + 30
                if not (self._week_start <= day < self._week_start + timedelta(days=7)):
                    continue
                x = self.LABEL_W + day.weekday() * col_w + 3
                y = self.HEADER_H + self.ALL_DAY_H + (start - self.START_HOUR * 60) * self.HOUR_H / 60 + 2
                h = max(18, (end - start) * self.HOUR_H / 60 - 4)
                self._rects[task["id"]] = (x, y, col_w - 6, h)
            except (ValueError, TypeError):
                continue

    @staticmethod
    def _parse_minutes(value):
        hours, minutes = map(int, value.split(":"))
        return hours * 60 + minutes

    @staticmethod
    def _has_time(task):
        return bool(task["start_time"] and task["end_time"] and not (task["start_time"] == "00:00" and task["end_time"] == "00:00"))

    def _snap_minutes(self, y):
        raw = self.START_HOUR * 60 + int((y - self.HEADER_H - self.ALL_DAY_H) * 60 / self.HOUR_H)
        return max(self.START_HOUR * 60, min(self.END_HOUR * 60, round(raw / self.MINUTE_STEP) * self.MINUTE_STEP))

    def _time_text(self, minutes):
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _task_at(self, pos):
        for task_id, rect in self._rects.items():
            x, y, w, h = rect
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                return task_id, rect
        return None, None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QBrush("#11151d"))
        col_w = max(80, (self.width() - self.LABEL_W) / 7)
        total_h = self.HEADER_H + self.ALL_DAY_H + (self.END_HOUR - self.START_HOUR) * self.HOUR_H

        painter.setPen(QPen("#252b38", 1))
        for i in range(8):
            x = self.LABEL_W + i * col_w
            painter.drawLine(int(x), 0, int(x), total_h)
        for hour in range(self.START_HOUR, self.END_HOUR + 1):
            y = self.HEADER_H + self.ALL_DAY_H + (hour - self.START_HOUR) * self.HOUR_H
            painter.setPen(QPen("#303746", 1))
            painter.drawLine(self.LABEL_W, int(y), self.width(), int(y))
            if hour < self.END_HOUR:
                painter.setPen(QPen("#202630", 1))
                painter.drawLine(self.LABEL_W, int(y + self.HOUR_H / 2), self.width(), int(y + self.HOUR_H / 2))
            painter.setPen(QPen("#8991a3", 1))
            painter.drawText(8, int(y + 5), f"{hour:02d}:00")

        for i in range(7):
            day = self._week_start + timedelta(days=i)
            x = self.LABEL_W + i * col_w
            painter.setPen(QPen("#e7eaf0", 1))
            painter.drawText(int(x + 8), 26, day.strftime("%a %d"))
            painter.setPen(QPen("#394152", 1))
            painter.drawLine(int(x), self.HEADER_H, int(x + col_w), self.HEADER_H)
            painter.drawText(int(x + 8), self.HEADER_H + 22, "All day")

        for task in self._tasks:
            if task["id"] not in self._rects:
                continue
            x, y, w, h = self._rects[task["id"]]
            completed = bool(task["completed"])
            painter.setBrush(QBrush("#353b48" if completed else "#5b43b5"))
            painter.setPen(QPen("#8067e8" if not completed else "#555d6b", 1))
            painter.drawRoundedRect(int(x), int(y), int(w), int(h), 7, 7)
            painter.setPen(QPen("#ffffff" if not completed else "#b5bac5", 1))
            text = task["title"]
            if h >= 34:
                text += f"\n{task['start_time']}–{task['end_time']}"
            painter.drawText(int(x + 8), int(y + 16), int(w - 16), int(h - 8), Qt.TextFlag.TextWordWrap, text)

    def resizeEvent(self, event):
        self._rebuild_geometry()
        super().resizeEvent(event)

    def mouseDoubleClickEvent(self, event):
        task_id, _ = self._task_at(event.position().toPoint())
        if task_id is not None:
            self.taskActivated.emit(task_id)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        task_id, rect = self._task_at(pos)
        if task_id is None:
            return
        x, y, w, h = rect
        resize = pos.y() >= y + h - 10
        task = next((t for t in self._tasks if t["id"] == task_id), None)
        if task:
            self._drag = {
                "id": task_id,
                "day": date.fromisoformat(task["due_date"]),
                "start": self._parse_minutes(task["start_time"]),
                "end": self._parse_minutes(task["end_time"]),
                "press": pos,
                "resize": resize,
            }
            self.setCursor(Qt.CursorShape.SizeVerCursor if resize else Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self._drag:
            task_id, rect = self._task_at(event.position().toPoint())
            if task_id is not None and rect and event.position().y() >= rect[1] + rect[3] - 10:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif task_id is not None:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            return
        delta = event.position().toPoint() - self._drag["press"]
        col_w = max(80, (self.width() - self.LABEL_W) / 7)
        day_delta = int(round(delta.x() / col_w))
        minute_delta = int(round(delta.y() * 60 / self.HOUR_H / self.MINUTE_STEP)) * self.MINUTE_STEP
        if self._drag["resize"]:
            new_end = max(self._drag["start"] + self.MINUTE_STEP, self._drag["end"] + minute_delta)
            new_end = min(self.END_HOUR * 60, new_end)
            QToolTip.showText(event.globalPosition().toPoint(), f"Ends {self._time_text(new_end)}", self)
        else:
            new_start = max(self.START_HOUR * 60, min(self.END_HOUR * 60 - self.MINUTE_STEP, self._drag["start"] + minute_delta))
            QToolTip.showText(event.globalPosition().toPoint(), f"{self._time_text(new_start)}", self)
        self.update()

    def mouseReleaseEvent(self, event):
        if not self._drag or event.button() != Qt.MouseButton.LeftButton:
            return
        drag = self._drag
        self._drag = None
        self.unsetCursor()
        delta = event.position().toPoint() - drag["press"]
        col_w = max(80, (self.width() - self.LABEL_W) / 7)
        day_delta = int(round(delta.x() / col_w))
        minute_delta = int(round(delta.y() * 60 / self.HOUR_H / self.MINUTE_STEP)) * self.MINUTE_STEP
        old_day = drag["day"]
        new_day = old_day + timedelta(days=day_delta)
        if not (self._week_start <= new_day < self._week_start + timedelta(days=7)):
            new_day = old_day
        if drag["resize"]:
            new_end = max(drag["start"] + self.MINUTE_STEP, min(self.END_HOUR * 60, drag["end"] + minute_delta))
            self.taskResized.emit(drag["id"], self._time_text(drag["start"]), self._time_text(new_end))
        else:
            new_start = max(self.START_HOUR * 60, min(self.END_HOUR * 60 - (drag["end"] - drag["start"]), drag["start"] + minute_delta))
            duration = drag["end"] - drag["start"]
            self.taskMoved.emit(drag["id"], new_day.isoformat(), self._time_text(new_start), self._time_text(new_start + duration))
        self.update()
