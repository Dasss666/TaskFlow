from calendar import monthrange
from datetime import date, datetime, timedelta

from PySide6.QtCore import QDateTime, QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QPainter, QPen
from taskflow.ui.task_icons import smart_icon, icon_color

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class AgendaTimeline(QWidget):
    taskActivated = Signal(int)
    taskCompletionRequested = Signal(int, bool)
    taskMoved = Signal(int, str, str, str)
    taskResized = Signal(int, str, str)

    START_HOUR = 7
    END_HOUR = 23
    HOUR_HEIGHT = 76
    LEFT_LABEL = 72
    TASK_X = 118
    ALL_DAY_HEIGHT = 74
    SNAP_MINUTES = 15
    MIN_DURATION = 30

    CATEGORY_COLORS = {
        "Personal": "#ff8585",
        "University": "#8f9cff",
        "Work": "#f0b35b",
        "Health": "#63d2b3",
        "Projects": "#c48cff",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_day_height = self.ALL_DAY_HEIGHT
        self._tasks = []
        self._rects = {}
        self.selected_date = date.today()
        self._drag_task_id = None
        self._drag_mode = None
        self._drag_start_y = 0.0
        self._drag_original = None
        self._preview_times = {}
        self._overlap_columns = {}
        self._hover_task_id = None
        self._pressed_task_id = None

        self.setMouseTracking(True)
        self.setMinimumHeight(
            self._all_day_height
            + (self.END_HOUR - self.START_HOUR) * self.HOUR_HEIGHT
        )

        self.clock = QTimer(self)
        self.clock.setInterval(30_000)
        self.clock.timeout.connect(self.update)
        self.clock.start()

    @staticmethod
    def _minutes(value):
        hours, minutes = map(int, value.split(":"))
        return hours * 60 + minutes

    @staticmethod
    def _time_string(minutes):
        minutes = max(0, min(23 * 60 + 59, minutes))
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    @staticmethod
    def _snap(minutes):
        return round(minutes / AgendaTimeline.SNAP_MINUTES) * AgendaTimeline.SNAP_MINUTES

    def set_date(self, value):
        self.selected_date = value
        self.update()

    def set_tasks(self, tasks):
        self._tasks = list(tasks)
        self._preview_times.clear()
        all_day_count = sum(
            1 for task in self._tasks
            if not task["start_time"] or not task["end_time"]
        )
        self._all_day_height = max(self.ALL_DAY_HEIGHT, 16 + all_day_count * 48)
        self.setMinimumHeight(
            self._all_day_height
            + (self.END_HOUR - self.START_HOUR) * self.HOUR_HEIGHT
        )
        self._rebuild_rects()
        self.update()

    def _effective_times(self, task):
        preview = self._preview_times.get(task["id"])
        if preview:
            return preview
        return task["start_time"], task["end_time"]

    def _layout_overlaps(self, timed_tasks):
        intervals = []
        for task in timed_tasks:
            start, end = self._effective_times(task)
            try:
                start_m = self._minutes(start)
                end_m = max(start_m + self.MIN_DURATION, self._minutes(end))
            except (TypeError, ValueError):
                continue
            intervals.append((task, start_m, end_m))

        intervals.sort(key=lambda item: (item[1], item[2], item[0]["id"]))
        result = {}
        groups = []
        current = []
        current_end = None

        # Intervals are sorted by start time, so a connected overlap cluster
        # can be built by tracking the furthest ending task in the cluster.
        for item in intervals:
            _, start, end = item
            if not current or start < current_end:
                current.append(item)
                current_end = max(current_end or end, end)
            else:
                groups.append(current)
                current = [item]
                current_end = end
        if current:
            groups.append(current)

        for group in groups:
            columns = []
            for task, start, end in group:
                column = 0
                while column < len(columns) and columns[column] > start:
                    column += 1
                if column == len(columns):
                    columns.append(end)
                else:
                    columns[column] = end
                result[task["id"]] = [column, 1]

            max_columns = len(columns)
            for task, _, _ in group:
                result[task["id"]][1] = max_columns

        self._overlap_columns = result

    def _rebuild_rects(self):
        self._rects = {}
        self._layout_overlaps(
            [task for task in self._tasks if task["start_time"] and task["end_time"]]
        )

        available_width = max(360, self.width() - self.TASK_X - 34)
        gap = 8

        for task in self._tasks:
            start, end = self._effective_times(task)
            if not start or not end:
                continue

            if task["id"] in self._overlap_columns:
                column, count = self._overlap_columns[task["id"]]
            else:
                column, count = 0, 1

            try:
                start_m = self._minutes(start)
                end_m = max(start_m + self.MIN_DURATION, self._minutes(end))
            except (TypeError, ValueError):
                continue

            y = (
                self._all_day_height
                + (start_m - self.START_HOUR * 60) * self.HOUR_HEIGHT / 60
            )
            height = max(
                34,
                (end_m - start_m) * self.HOUR_HEIGHT / 60 - 8,
            )

            column_width = (
                available_width - gap * (count - 1)
            ) / max(1, count)
            x = self.TASK_X + column * (column_width + gap)

            self._rects[task["id"]] = (
                task,
                __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(
                    x, y + 4, column_width, height
                ),
            )

    def resizeEvent(self, event):
        self._rebuild_rects()
        super().resizeEvent(event)

    def _category_color(self, task):
        return QColor(self.CATEGORY_COLORS.get(task["category"], "#9d7cff"))

    def _task_tags(self, task):
        return [
            tag.strip()
            for tag in (task["tags"] or "").split(",")
            if tag.strip()
        ]

    def _paint_completion(self, painter, rect, task):
        center = QPointF(rect.right() - 22, rect.top() + 22)
        radius = 9
        category = self._category_color(task)
        completed = bool(task["completed"])
        track = QColor(self.palette().windowText().color())
        track.setAlpha(70)
        ring = category if completed else track
        painter.setBrush(QBrush(category if completed else QColor(0, 0, 0, 0)))
        painter.setPen(QPen(ring, 1.8))
        painter.drawEllipse(center, radius, radius)
        if completed:
            painter.setPen(QPen(Qt.GlobalColor.white, 1.8))
            painter.drawLine(center.x() - 4, center.y(), center.x() - 1, center.y() + 3)
            painter.drawLine(center.x() - 1, center.y() + 3, center.x() + 4, center.y() - 4)

    def _paint_tags(self, painter, rect, task, text_color):
        tags = self._task_tags(task)
        if not tags or rect.height() < 88:
            return
        x = int(rect.x() + 56)
        y = int(rect.bottom() - 24)
        for tag in tags[:3]:
            width = min(108, 16 + len(tag) * 7)
            badge = __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(x, y, width, 19)
            badge_fill = QColor(text_color)
            badge_fill.setAlpha(22)
            painter.setBrush(QBrush(badge_fill))
            painter.setPen(QPen(QColor(text_color), 1))
            painter.drawRoundedRect(badge, 9, 9)
            painter.setPen(QPen(text_color, 1))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(int(badge.x() + 7), int(badge.y() + 13), tag[:14])
            x += width + 5

    def _paint_task_card(self, painter, rect, task, text, muted):
        category = self._category_color(task)
        completed = bool(task["completed"])
        hovered = int(task["id"]) == self._hover_task_id
        pressed = int(task["id"]) == self._pressed_task_id

        fill = QColor(category)
        fill.setAlpha(52 if hovered else 38)
        if completed:
            fill.setAlpha(25)
        border = QColor(category)
        border.setAlpha(210 if hovered else 135)
        if completed:
            border.setAlpha(95)

        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, 1.8 if hovered else 1.4))
        painter.drawRoundedRect(rect, 13, 13)

        rail = __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(
            rect.x(), rect.y(), 5, rect.height()
        )
        painter.setBrush(QBrush(category))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rail, 3, 3)

        if pressed:
            painter.setBrush(QBrush(QColor(255, 255, 255, 16)))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 11, 11)

        compact = rect.height() < 62
        icon_radius = 14 if compact else 20
        icon_x = rect.x() + 26
        icon_y = rect.top() + (rect.height() / 2 if compact else 30)
        icon_center = QPointF(icon_x, icon_y)
        icon_bg = QColor(category)
        icon_bg.setAlpha(72 if not completed else 38)
        painter.setBrush(QBrush(icon_bg))
        painter.setPen(QPen(category, 1.2))
        painter.drawEllipse(icon_center, icon_radius, icon_radius)
        painter.setPen(QPen(category, 1))
        painter.setFont(QFont("Segoe UI Emoji", 11 if compact else 17))
        painter.drawText(
            int(icon_x - icon_radius), int(icon_y - icon_radius),
            int(icon_radius * 2), int(icon_radius * 2),
            Qt.AlignmentFlag.AlignCenter, smart_icon(task)
        )

        left = int(rect.x() + (48 if compact else 58))
        right = int(rect.right() - 42)
        start_time, end_time = self._effective_times(task)

        painter.setPen(QPen(muted, 1))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            left, int(rect.top() + (16 if compact else 18)),
            max(60, right - left), 18,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{start_time} – {end_time}"
        )

        title_color = QColor(text)
        if completed:
            title_color.setAlpha(125)
        painter.setPen(QPen(title_color, 1))
        title_font = QFont("Segoe UI", 10 if compact else 11)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        title_y = int(rect.top() + (31 if compact else 40))
        title_h = max(
            16,
            min(28 if not compact else 18, int(rect.height() - (34 if compact else 56))),
        )
        painter.drawText(
            left, title_y, max(70, right - left), title_h,
            Qt.TextFlag.TextWordWrap, task["title"]
        )

        if not compact and rect.height() >= 68:
            category_name = task["category"] or "Personal"
            painter.setPen(QPen(category, 1))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                left, int(rect.top() + 59), max(70, right - left), 17,
                Qt.AlignmentFlag.AlignLeft, f"● {category_name}"
            )

        self._paint_tags(painter, rect, task, title_color)
        self._paint_completion(painter, rect, task)

    def _paint_all_day_card(self, painter, rect, task, text):
        category = self._category_color(task)
        completed = bool(task["completed"])
        fill = QColor(category)
        fill.setAlpha(32 if completed else 48)
        border = QColor(category)
        border.setAlpha(100 if completed else 175)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, 1.4))
        painter.drawRoundedRect(rect, 12, 12)

        icon_center = QPointF(rect.x() + 28, rect.center().y())
        painter.setBrush(QBrush(category))
        painter.setPen(QPen(category, 1))
        painter.drawEllipse(icon_center, 17, 17)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.setFont(QFont("Segoe UI Emoji", 13))
        painter.drawText(
            int(rect.x() + 11), int(rect.y() + 10), 34, 34,
            Qt.AlignmentFlag.AlignCenter, smart_icon(task)
        )

        title_color = QColor(text)
        if completed:
            title_color.setAlpha(125)
        painter.setPen(QPen(title_color, 1))
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(
            int(rect.x() + 54), int(rect.y() + 8),
            int(rect.width() - 110), 24,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            task["title"]
        )
        category_name = task["category"] or "Personal"
        painter.setPen(QPen(category, 1))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            int(rect.x() + 54), int(rect.y() + 31),
            int(rect.width() - 110), 18,
            Qt.AlignmentFlag.AlignLeft, f"● {category_name}"
        )
        self._paint_completion(painter, rect, task)

    def _paint_current_time(self, painter):
        if self.selected_date != date.today():
            return

        now = datetime.now()
        minutes = now.hour * 60 + now.minute + now.second / 60
        if minutes < self.START_HOUR * 60 or minutes > self.END_HOUR * 60:
            return

        y = self._all_day_height + (
            minutes - self.START_HOUR * 60
        ) * self.HOUR_HEIGHT / 60

        accent = QColor("#ff8585")
        painter.setPen(QPen(accent, 2))
        painter.drawLine(self.LEFT_LABEL, int(y), self.width() - 10, int(y))
        painter.setBrush(QBrush(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(self.LEFT_LABEL, y), 4, 4)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background = self.palette().window().color()
        text = self.palette().windowText().color()
        muted = QColor(text)
        muted.setAlpha(115)
        grid = QColor(text)
        grid.setAlpha(20)
        grid_strong = QColor(text)
        grid_strong.setAlpha(35)

        painter.fillRect(self.rect(), background)

        all_day = [
            task for task in self._tasks
            if not task["start_time"] or not task["end_time"]
        ]

        painter.setPen(QPen(grid_strong, 1))
        painter.drawLine(
            self.TASK_X, self._all_day_height,
            self.width(), self._all_day_height
        )
        painter.setPen(QPen(muted, 1))
        painter.drawText(20, 31, "ALL DAY")

        y = 10
        for task in all_day:
            rect = __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(
                self.TASK_X, y, max(260, self.width() - self.TASK_X - 34), 42
            )
            self._rects[task["id"]] = (task, rect)

            self._paint_all_day_card(painter, rect, task, text)
            y += 48

        for hour in range(self.START_HOUR, self.END_HOUR + 1):
            y = self._all_day_height + (
                hour - self.START_HOUR
            ) * self.HOUR_HEIGHT

            painter.setPen(QPen(grid_strong, 1))
            painter.drawLine(self.LEFT_LABEL, int(y), self.width(), int(y))
            painter.setPen(QPen(muted, 1))
            painter.drawText(20, int(y + 5), f"{hour:02d}:00")

            if hour < self.END_HOUR:
                half = y + self.HOUR_HEIGHT / 2
                painter.setPen(QPen(grid, 1))
                painter.drawLine(
                    self.LEFT_LABEL, int(half), self.width(), int(half)
                )

        for task in self._tasks:
            if task["id"] not in self._rects:
                continue
            if not task["start_time"] or not task["end_time"]:
                continue

            _, rect = self._rects[task["id"]]
            self._paint_task_card(painter, rect, task, text, muted)

        self._paint_current_time(painter)

    def _hit_test(self, pos):
        for task_id, (task, rect) in reversed(list(self._rects.items())):
            if rect.contains(pos):
                return task, rect
        return None, None

    def _completion_hit(self, pos, rect):
        center = QPointF(rect.right() - 22, rect.top() + 22)
        return (pos - center).manhattanLength() <= 15

    def _drag_mode_for(self, pos, rect):
        edge = 9
        if abs(pos.y() - rect.bottom()) <= edge:
            return "resize_bottom"
        if abs(pos.y() - rect.top()) <= edge:
            return "resize_top"
        return "move"

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        task, rect = self._hit_test(event.position())
        if not task:
            return super().mousePressEvent(event)

        if self._completion_hit(event.position(), rect):
            self._pressed_task_id = int(task["id"])
            self.taskCompletionRequested.emit(
                int(task["id"]), not bool(task["completed"])
            )
            self.update()
            event.accept()
            return

        if not task["start_time"] or not task["end_time"]:
            return super().mousePressEvent(event)

        self._pressed_task_id = int(task["id"])
        self._drag_task_id = int(task["id"])
        self._drag_mode = self._drag_mode_for(event.position(), rect)
        self._drag_start_y = event.position().y()
        self._drag_original = (task["start_time"], task["end_time"])
        self._preview_times[self._drag_task_id] = self._drag_original
        self.setCursor(
            QCursor(Qt.CursorShape.SizeVerCursor)
            if self._drag_mode.startswith("resize")
            else QCursor(Qt.CursorShape.ClosedHandCursor)
        )
        event.accept()

    def mouseMoveEvent(self, event):
        if not self._drag_task_id:
            task, rect = self._hit_test(event.position())
            new_hover = int(task["id"]) if task else None
            if new_hover != self._hover_task_id:
                self._hover_task_id = new_hover
                self.update()
            if rect:
                mode = self._drag_mode_for(event.position(), rect)
                self.setCursor(
                    QCursor(Qt.CursorShape.SizeVerCursor)
                    if mode.startswith("resize")
                    else QCursor(Qt.CursorShape.OpenHandCursor)
                )
            else:
                self.unsetCursor()
            return

        delta_minutes = self._snap(
            (event.position().y() - self._drag_start_y)
            * 60 / self.HOUR_HEIGHT
        )
        original_start = self._minutes(self._drag_original[0])
        original_end = self._minutes(self._drag_original[1])

        if self._drag_mode == "move":
            duration = original_end - original_start
            new_start = self._snap(original_start + delta_minutes)
            new_start = max(self.START_HOUR * 60, new_start)
            new_start = min(self.END_HOUR * 60 - duration, new_start)
            new_end = new_start + duration
        elif self._drag_mode == "resize_bottom":
            new_start = original_start
            new_end = self._snap(original_end + delta_minutes)
            new_end = max(new_start + self.MIN_DURATION, new_end)
            new_end = min(self.END_HOUR * 60, new_end)
        else:
            new_end = original_end
            new_start = self._snap(original_start + delta_minutes)
            new_start = max(self.START_HOUR * 60, new_start)
            new_start = min(new_end - self.MIN_DURATION, new_start)

        self._preview_times[self._drag_task_id] = (
            self._time_string(new_start),
            self._time_string(new_end),
        )
        self._rebuild_rects()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)

        task_id = self._drag_task_id
        if task_id:
            original = self._drag_original
            new_start, new_end = self._preview_times.get(task_id, original)
            self._preview_times.pop(task_id, None)

            if self._drag_mode == "move":
                task = next(
                    (task for task in self._tasks if int(task["id"]) == task_id),
                    None,
                )
                if task and (new_start, new_end) != original:
                    self.taskMoved.emit(
                        task_id,
                        task["due_date"],
                        new_start,
                        new_end,
                    )
            elif (new_start, new_end) != original:
                self.taskResized.emit(task_id, new_start, new_end)

            self._drag_task_id = None
            self._drag_mode = None
            self._drag_original = None
            self._pressed_task_id = None
            self._rebuild_rects()
            self.update()
        else:
            self._pressed_task_id = None
            self.update()

        self.unsetCursor()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        task, rect = self._hit_test(event.position())
        if task and rect.contains(event.position()):
            self.taskActivated.emit(int(task["id"]))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class AgendaView(QWidget):
    taskActivated = Signal(int)
    dateChanged = Signal(object)
    newTaskRequested = Signal(object)

    MONTH_NAMES = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_date = date.today()
        self._tasks = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Structured-inspired header:
        # month selector on the left, compact week navigation in the center.
        header = QHBoxLayout()
        header.setSpacing(8)

        self.month_button = QPushButton()
        self.month_button.setObjectName("agendaMonthButton")
        self.month_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_button.clicked.connect(self._show_month_menu)
        header.addWidget(self.month_button)

        self.week_label = QLabel()
        self.week_label.setObjectName("agendaWeekLabel")
        header.addWidget(self.week_label)

        header.addStretch()

        previous = QPushButton("‹")
        previous.setObjectName("agendaNavButton")
        previous.setToolTip("Previous week")
        previous.clicked.connect(lambda: self._shift_week(-1))

        self.today_button = QPushButton("Today")
        self.today_button.setObjectName("agendaTodayButton")
        self.today_button.clicked.connect(self._go_today)

        next_button = QPushButton("›")
        next_button.setObjectName("agendaNavButton")
        next_button.setToolTip("Next week")
        next_button.clicked.connect(lambda: self._shift_week(1))

        header.addWidget(previous)
        header.addWidget(self.today_button)
        header.addWidget(next_button)
        root.addLayout(header)

        # Seven-day strip. The selected day stays visually anchored while
        # the left/right controls move by a complete week.
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

        self.add_button = QPushButton("+", self)
        self.add_button.setObjectName("floatingAddButton")
        self.add_button.setFixedSize(64, 64)
        self.add_button.setToolTip("Add task")
        self.add_button.clicked.connect(
            lambda: self.newTaskRequested.emit(self.selected_date)
        )

        self._rebuild_day_strip()
        self._update_header()
        self.timeline.set_date(self.selected_date)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 20
        self.add_button.move(
            self.width() - self.add_button.width() - margin,
            self.height() - self.add_button.height() - margin,
        )

    def set_date(self, value: date):
        if self.selected_date == value:
            self._update_header()
            self._rebuild_day_strip()
            self.timeline.set_date(value)
            return

        self.selected_date = value
        self._update_header()
        self._rebuild_day_strip()
        self.timeline.set_date(value)
        self.dateChanged.emit(value)

    def set_tasks(self, tasks):
        self._tasks = list(tasks)
        self.timeline.set_tasks(self._tasks)
        self._rebuild_day_strip()

    def _shift_week(self, weeks):
        self.set_date(self.selected_date + timedelta(days=7 * weeks))

    def _go_today(self):
        self.set_date(date.today())

    def _update_header(self):
        selected = self.selected_date
        self.month_button.setText(f"{self.MONTH_NAMES[selected.month - 1]} {selected.year}  ⌄")

        monday = selected - timedelta(days=selected.weekday())
        sunday = monday + timedelta(days=6)
        if monday.year == sunday.year:
            if monday.month == sunday.month:
                week_text = f"{monday.strftime('%b')} {monday.day} – {sunday.day}"
            else:
                week_text = f"{monday.strftime('%b')} {monday.day} – {sunday.strftime('%b')} {sunday.day}"
        else:
            week_text = (
                f"{monday.strftime('%b')} {monday.day}, {monday.year} – "
                f"{sunday.strftime('%b')} {sunday.day}, {sunday.year}"
            )
        self.week_label.setText(week_text)

        self.today_button.setEnabled(selected != date.today())
        self.today_button.setToolTip(
            "Go to today" if selected != date.today() else "Today is selected"
        )

    def _show_month_menu(self):
        menu = __import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu(self)
        menu.setObjectName("agendaMonthMenu")

        year = self.selected_date.year
        for month_index, month_name in enumerate(self.MONTH_NAMES, start=1):
            action = menu.addAction(month_name)
            action.setCheckable(True)
            action.setChecked(month_index == self.selected_date.month)
            action.triggered.connect(
                lambda checked, month=month_index, y=year: self._select_month(y, month)
            )

        menu.addSeparator()
        prev_year = menu.addAction(f"‹ {year - 1}")
        next_year = menu.addAction(f"{year + 1} ›")
        prev_year.triggered.connect(
            lambda: self._select_month(year - 1, self.selected_date.month)
        )
        next_year.triggered.connect(
            lambda: self._select_month(year + 1, self.selected_date.month)
        )

        menu.exec(
            self.month_button.mapToGlobal(
                self.month_button.rect().bottomLeft()
            )
        )

    def _select_month(self, year, month):
        day = min(self.selected_date.day, monthrange(year, month)[1])
        self.set_date(date(year, month, day))

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _rebuild_day_strip(self):
        self._clear_layout(self.day_strip)

        monday = self.selected_date - timedelta(days=self.selected_date.weekday())
        today = date.today()

        for offset in range(7):
            current = monday + timedelta(days=offset)
            button = QPushButton()
            button.setCheckable(True)
            button.setChecked(current == self.selected_date)
            button.setObjectName(
                "agendaDayToday" if current == today else "dayButton"
            )
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            weekday = current.strftime("%a").upper()
            if current == today:
                text = f"{weekday}\n{current.day}\n•"
            else:
                text = f"{weekday}\n{current.day}"

            button.setText(text)
            button.setToolTip(
                f"Open {current.strftime('%A, %d %B %Y')}"
            )
            button.clicked.connect(
                lambda checked, value=current: self.set_date(value)
            )
            self.day_strip.addWidget(button, 1)
