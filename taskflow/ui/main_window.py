from datetime import date, timedelta

from PySide6.QtCore import QDate, QTime, Qt, QSettings, QPropertyAnimation, QEasingCurve, Signal, Property
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget,
    QTimeEdit, QToolButton, QVBoxLayout, QWidget
)

from taskflow.database import Database
from taskflow.services.data_transfer import export_tasks, import_tasks
from taskflow.services.notifications import NotificationService
from taskflow.services.recurrence import materialize_recurring_tasks
from taskflow.ui.agenda_view import AgendaView
from taskflow.ui.dashboard import DashboardView
from taskflow.ui.themes import load_theme, save_theme, stylesheet, THEMES

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
            self.all_day.setChecked(not start or not end)
            if start:
                self.start.setTime(QTime.fromString(start, "HH:mm"))
            if end:
                self.end.setTime(QTime.fromString(end, "HH:mm"))

            self.priority.setCurrentText(task["priority"])
            self.category.setCurrentText(task["category"] or "Personal")
            self.tags.setText(task["tags"] or "")
            self.recurrence.setCurrentText(task["recurrence"] or "none")
        else:
            self._toggle_time_fields(False)

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



class AnimatedCheck(QWidget):
    checkedChanged = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._progress = 1.0 if self._checked else 0.0
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Mark as completed")

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = float(value)
        self.update()

    progress = Property(float, get_progress, set_progress)

    def setChecked(self, checked, animated=True):
        checked = bool(checked)
        self._checked = checked
        animation = QPropertyAnimation(self, b"progress", self)
        animation.setDuration(180)
        animation.setStartValue(self._progress)
        animation.setEndValue(1.0 if checked else 0.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation = animation
        animation.finished.connect(lambda: self.checkedChanged.emit(self._checked))
        animation.start()

    def isChecked(self):
        return self._checked

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        radius = 9.5
        accent = QColor("#ff8585")
        track = QColor(self.palette().mid().color())
        track.setAlpha(95)
        painter.setBrush(QBrush(track))
        painter.setPen(QPen(track, 1.5))
        painter.drawEllipse(center, radius, radius)
        if self._progress > 0:
            fill = QColor(accent)
            fill.setAlpha(int(255 * self._progress))
            painter.setBrush(QBrush(fill))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(Qt.GlobalColor.white, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(center.x() - 5, center.y(), center.x() - 1, center.y() + 4)
            painter.drawLine(center.x() - 1, center.y() + 4, center.x() + 6, center.y() - 5)

class TaskCard(QFrame):
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    completionChanged = Signal(int, bool)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task_id = int(task["id"])
        self.setObjectName("taskCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        self.check = AnimatedCheck(bool(task["completed"]))
        self.check.checkedChanged.connect(
            lambda checked: self.completionChanged.emit(self.task_id, checked)
        )
        root.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(4)

        title = QLabel(task["title"])
        title.setObjectName("taskCardTitle")
        title.setWordWrap(True)
        body.addWidget(title)

        meta = []
        if task["start_time"] and task["end_time"]:
            meta.append(f"{task['start_time']} – {task['end_time']}")
        else:
            meta.append("All day")
        if task["recurrence"] != "none":
            meta.append(f"↻ {task['recurrence']}")
        meta_label = QLabel("  •  ".join(meta))
        meta_label.setObjectName("taskCardMeta")
        body.addWidget(meta_label)

        category = task["category"] or "Personal"
        category_colors = {
            "Personal": "#ff8585",
            "University": "#8f9cff",
            "Work": "#f0b35b",
            "Health": "#63d2b3",
            "Projects": "#c48cff",
        }
        category_label = QLabel(f"●  {category}")
        category_label.setObjectName("categoryBadge")
        category_label.setStyleSheet(
            f"color:{category_colors.get(category, '#9d7cff')}; font-weight:600;"
        )
        body.addWidget(category_label)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        tags = [tag.strip() for tag in (task["tags"] or "").split(",") if tag.strip()]
        for tag in tags[:5]:
            badge = QLabel(f"#{tag}")
            badge.setObjectName("tagBadge")
            tags_row.addWidget(badge)
        if tags:
            tags_row.addStretch()
            body.addLayout(tags_row)

        root.addLayout(body, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        priority = QLabel(task["priority"].upper())
        priority.setObjectName(f"priority_{task['priority']}")
        actions.addWidget(priority, 0, Qt.AlignmentFlag.AlignRight)
        more = QToolButton()
        more.setText("⋯")
        more.setObjectName("cardMoreButton")
        more.clicked.connect(self._show_menu)
        actions.addWidget(more, 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(actions)

        if task["completed"]:
            title.setProperty("completed", True)
            self.setProperty("completed", True)

    def _show_menu(self):
        menu = QMenu(self)
        edit = menu.addAction("Edit")
        delete = menu.addAction("Delete")
        chosen = menu.exec(self.mapToGlobal(self.rect().topRight()))
        if chosen == edit:
            self.editRequested.emit(self.task_id)
        elif chosen == delete:
            self.deleteRequested.emit(self.task_id)

    def mouseDoubleClickEvent(self, event):
        self.editRequested.emit(self.task_id)
        super().mouseDoubleClickEvent(event)


class Sidebar(QWidget):
    pageRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = True
        self.setObjectName("sidebar")
        self.setMinimumWidth(228)
        self.setMaximumWidth(228)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(8)

        self.toggle = QToolButton()
        self.toggle.setText("☰")
        self.toggle.setToolTip("Collapse navigation")
        self.toggle.setObjectName("sidebarToggle")
        self.toggle.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignLeft)

        brand = QLabel("TaskFlow")
        brand.setObjectName("sidebarBrand")
        layout.addWidget(brand)
        self.brand = brand

        layout.addSpacing(12)

        self.buttons = []
        for label, icon, index in [
            ("Tasks", "✓", 0),
            ("Dashboard", "▦", 1),
            ("Agenda", "◷", 2),
        ]:
            button = QPushButton(f"{icon}   {label}")
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked, i=index: self._select(i))
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch()

        hint = QLabel("TaskFlow\nYour day, organized.")
        hint.setObjectName("sidebarHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.hint = hint

        self._select(0)

    def _select(self, index):
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)
        self.pageRequested.emit(index)

    def set_active(self, index):
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)

    def toggle_sidebar(self):
        self.expanded = not self.expanded
        start = self.width()
        end = 228 if self.expanded else 72

        animation = QPropertyAnimation(self, b"minimumWidth", self)
        animation.setDuration(180)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        max_animation = QPropertyAnimation(self, b"maximumWidth", self)
        max_animation.setDuration(180)
        max_animation.setStartValue(start)
        max_animation.setEndValue(end)
        max_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._animations = (animation, max_animation)
        animation.start()
        max_animation.start()

        self.toggle.setToolTip("Expand navigation" if not self.expanded else "Collapse navigation")
        self.brand.setVisible(self.expanded)
        self.hint.setVisible(self.expanded)

        for button, (label, icon, _) in zip(
            self.buttons,
            [("Tasks", "✓", 0), ("Dashboard", "▦", 1), ("Agenda", "◷", 2)],
        ):
            button.setText(f"{icon}   {label}" if self.expanded else icon)


class MainWindow(QMainWindow):
    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        self.settings = QSettings("Dasss666", "TaskFlow")
        self.current_theme = load_theme(self.settings)

        self.setWindowTitle("TaskFlow")
        self.resize(1280, 820)
        self.setMinimumSize(760, 520)

        self._build_ui()
        self._apply_theme(self.current_theme)

        self.notifications = NotificationService(self, self.database)
        self.refresh()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)

        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.pageRequested.connect(self.show_page)
        main.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 20)
        content_layout.setSpacing(18)

        topbar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("TaskFlow")
        title.setObjectName("appTitle")
        subtitle = QLabel("Plan your tasks, keep your day in flow.")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        topbar.addLayout(title_box)
        topbar.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tasks, tags, categories...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(250)
        self.search.textChanged.connect(self.search_changed)
        topbar.addWidget(self.search)

        add = QPushButton("+ New task")
        add.setObjectName("primaryButton")
        add.clicked.connect(self.new_task)
        topbar.addWidget(add)

        options = QToolButton()
        options.setText("⚙")
        options.setObjectName("iconButton")
        options.setToolTip("Settings and data")
        options.setMenu(self._build_options_menu(options))
        options.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        topbar.addWidget(options)

        content_layout.addLayout(topbar)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        main.addWidget(content, 1)

        self._build_tasks_page()
        self.dashboard = DashboardView()
        self.stack.addWidget(self.dashboard)
        self._build_agenda_page()

    def _build_options_menu(self, parent):
        menu = QMenu(parent)

        data_menu = menu.addMenu("Data")
        export_action = QAction("Export JSON...", self)
        export_action.triggered.connect(self.export_data)
        import_action = QAction("Import JSON...", self)
        import_action.triggered.connect(self.import_data)
        data_menu.addAction(export_action)
        data_menu.addAction(import_action)

        theme_menu = menu.addMenu("Theme")
        for theme_name in THEMES:
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, name=theme_name: self.set_theme(name))
            theme_menu.addAction(action)
            setattr(self, f"theme_action_{theme_name.lower()}", action)
        self._update_theme_actions()
        return menu

    def _build_tasks_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        self.tasks_title = QLabel("Tasks")
        self.tasks_title.setObjectName("pageTitle")
        heading.addWidget(self.tasks_title)
        heading.addStretch()

        self.filter_button = QPushButton("Filters")
        self.filter_button.setCheckable(True)
        self.filter_button.clicked.connect(self._toggle_filters)
        heading.addWidget(self.filter_button)
        layout.addLayout(heading)

        self.filters = QWidget()
        filter_layout = QHBoxLayout(self.filters)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All status", "Open", "Completed"])
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All priorities", "High", "Medium", "Low"])
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All categories"] + CATEGORIES)
        self.recurrence_filter = QComboBox()
        self.recurrence_filter.addItems(["All recurrence", "None", "Daily", "Weekly", "Monthly"])
        self.date_filter = QCheckBox("Date range")
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate().addDays(30))
        self.date_to.setCalendarPopup(True)

        for widget in (
            self.status_filter, self.priority_filter,
            self.category_filter, self.recurrence_filter
        ):
            widget.currentIndexChanged.connect(self.refresh_tasks)
            filter_layout.addWidget(widget)
        self.date_filter.toggled.connect(self.refresh_tasks)
        self.date_from.dateChanged.connect(self.refresh_tasks)
        self.date_to.dateChanged.connect(self.refresh_tasks)
        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(self.date_to)
        self.date_from.setVisible(False)
        self.date_to.setVisible(False)
        self.date_filter.toggled.connect(self.date_from.setVisible)
        self.date_filter.toggled.connect(self.date_to.setVisible)

        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset_filters)
        filter_layout.addWidget(reset)
        filter_layout.addStretch()
        self.filters.setVisible(False)
        layout.addWidget(self.filters)

        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(4, 4, 12, 8)
        self.task_layout.setSpacing(18)
        self.task_scroll.setWidget(self.task_container)
        layout.addWidget(self.task_scroll, 1)

        self.stack.addWidget(page)

    def _build_agenda_page(self):
        self.agenda = AgendaView()
        self.agenda.taskActivated.connect(self.edit_task_by_id)
        self.agenda.dateChanged.connect(lambda value: self.refresh_agenda())
        self.agenda.newTaskRequested.connect(self.new_task)
        self.agenda.timeline.taskMoved.connect(self.move_agenda_task)
        self.agenda.timeline.taskResized.connect(self.resize_agenda_task)
        self.stack.addWidget(self.agenda)

    def _apply_theme(self, theme_name):
        self.setStyleSheet(stylesheet(theme_name))

    def _update_theme_actions(self):
        for theme_name in THEMES:
            action = getattr(self, f"theme_action_{theme_name.lower()}", None)
            if action:
                action.setChecked(theme_name == self.current_theme)

    def set_theme(self, theme_name):
        if theme_name not in THEMES:
            return
        self.current_theme = theme_name
        save_theme(self.settings, theme_name)
        self._apply_theme(theme_name)
        self._update_theme_actions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            if self.width() < 980 and self.sidebar.expanded:
                self.sidebar.toggle_sidebar()
            elif self.width() >= 1120 and not self.sidebar.expanded:
                self.sidebar.toggle_sidebar()

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)
        if index == 0:
            self.refresh_tasks()
        elif index == 1:
            self.refresh_dashboard()
        elif index == 2:
            self.refresh_agenda()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _day_title(self, value):
        today = date.today()
        if value == today:
            return "Today"
        if value == today + timedelta(days=1):
            return "Tomorrow"
        return value.strftime("%A, %d %B")

    def _section(self, title, subtitle):
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(8)

        title_row = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("dayTitle")
        title_row.addWidget(label)
        title_row.addStretch()
        count = QLabel(subtitle)
        count.setObjectName("dayCount")
        title_row.addWidget(count)
        section_layout.addLayout(title_row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("sectionLine")
        section_layout.addWidget(line)
        return section, section_layout

    def _add_empty_state(self):
        empty = QWidget()
        box = QVBoxLayout(empty)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("No tasks here")
        label.setObjectName("emptyTitle")
        box.addWidget(label, 0, Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Create a task with + New task.")
        hint.setObjectName("emptyHint")
        box.addWidget(hint, 0, Qt.AlignmentFlag.AlignCenter)
        self.task_layout.addWidget(empty)

    def refresh(self):
        self.refresh_tasks()
        self.refresh_dashboard()
        self.refresh_agenda()

    def refresh_tasks(self):
        status = {
            "All status": "all", "Open": "open", "Completed": "completed"
        }[self.status_filter.currentText()]
        priority = {
            "All priorities": "all", "High": "high", "Medium": "medium", "Low": "low"
        }[self.priority_filter.currentText()]
        category = "all" if self.category_filter.currentIndex() == 0 else self.category_filter.currentText()
        recurrence = {
            "All recurrence": "all", "None": "none", "Daily": "daily",
            "Weekly": "weekly", "Monthly": "monthly"
        }[self.recurrence_filter.currentText()]

        start = date.today()
        end = start + timedelta(days=30)
        if self.date_filter.isChecked():
            start = self.date_from.date().toPython()
            end = self.date_to.date().toPython()
            if start > end:
                start, end = end, start
        tasks = self.database.filtered_tasks(
            self.search.text(), status, priority, category, recurrence,
            start.isoformat(), end.isoformat()
        )

        self._clear_layout(self.task_layout)
        groups = {}
        for task in tasks:
            if task["due_date"]:
                value = date.fromisoformat(task["due_date"])
                groups.setdefault(value, []).append(task)

        if not groups:
            self._add_empty_state()
            return

        for day in sorted(groups):
            section, section_layout = self._section(
                self._day_title(day),
                f"{len(groups[day])} task" + ("" if len(groups[day]) == 1 else "s"),
            )
            for task in groups[day]:
                card = TaskCard(task)
                card.editRequested.connect(self.edit_task_by_id)
                card.deleteRequested.connect(self.delete_task_by_id)
                card.completionChanged.connect(self.set_task_completed)
                section_layout.addWidget(card)
            self.task_layout.addWidget(section)

        self.task_layout.addStretch()

    def _toggle_filters(self, checked):
        self.filters.setVisible(checked)

    def reset_filters(self):
        for widget in (
            self.status_filter, self.priority_filter,
            self.category_filter, self.recurrence_filter
        ):
            widget.setCurrentIndex(0)
        self.search.clear()
        self.date_filter.setChecked(False)
        self.date_from.setDate(QDate.currentDate())
        self.date_to.setDate(QDate.currentDate().addDays(30))
        self.refresh_tasks()

    def refresh_dashboard(self):
        row, categories = self.database.productivity_stats()
        self.dashboard.update_stats(row, categories)

    def refresh_agenda(self):
        selected = self.agenda.selected_date
        tasks = self.database.tasks_for_date(selected)
        self.agenda.set_tasks(tasks)

    def search_changed(self):
        if self.stack.currentIndex() == 0:
            self.refresh_tasks()

    def new_task(self, preferred_date=None):
        dialog = TaskDialog(self)
        if preferred_date is not None:
            dialog.date.setSelectedDate(
                QDate(preferred_date.year, preferred_date.month, preferred_date.day)
            )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_task(**dialog.values())
            materialize_recurring_tasks(self.database)
            self.refresh()

    def move_agenda_task(self, task_id, due_date, start_time, end_time):
        task = self.database.get_task(task_id)
        if not task:
            return
        self.database.update_task(
            task_id,
            due_date=due_date,
            start_time=start_time,
            end_time=end_time,
        )
        self.refresh()

    def resize_agenda_task(self, task_id, start_time, end_time):
        task = self.database.get_task(task_id)
        if not task:
            return
        self.database.update_task(
            task_id,
            start_time=start_time,
            end_time=end_time,
        )
        self.refresh()

    def set_task_completed(self, task_id, completed):
        task = self.database.get_task(task_id)
        if not task:
            return
        self.database.update_task(task_id, completed=int(completed))
        self.refresh()

    def edit_task_by_id(self, task_id):
        task = self.database.get_task(task_id)
        if not task:
            return
        dialog = TaskDialog(self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.update_task(task["id"], **dialog.values())
            materialize_recurring_tasks(self.database)
            self.refresh()

    def delete_task_by_id(self, task_id):
        task = self.database.get_task(task_id)
        if not task:
            return
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
        if not path:
            return
        try:
            count = import_tasks(self.database, path)
            materialize_recurring_tasks(self.database)
            self.refresh()
            QMessageBox.information(self, "TaskFlow", f"Imported {count} tasks.")
        except Exception as exc:
            QMessageBox.critical(self, "TaskFlow", f"Import failed: {exc}")

    def closeEvent(self, event):
        self.database.close()
        super().closeEvent(event)
