from datetime import date, timedelta

from PySide6.QtCore import QDate, QTime, Qt, QSettings, QPropertyAnimation, QEasingCurve, Signal, Property
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QColorDialog,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QListWidget, QListWidgetItem, QInputDialog, QCompleter, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QStackedWidget, QTabWidget,
    QTimeEdit, QToolButton, QVBoxLayout, QWidget
)

from taskflow.database import Database
from taskflow.services.data_transfer import export_tasks, import_tasks
from taskflow.services.notifications import NotificationService
from taskflow.services.recurrence import materialize_recurring_tasks
from taskflow.ui.agenda_view import AgendaView
from taskflow.ui.dashboard import DashboardView
from taskflow.ui.themes import load_theme, save_theme, stylesheet, THEMES
from taskflow.ui.task_icons import SmartTaskIcon, icon_color

CATEGORIES = ["Personal", "University", "Work", "Health", "Projects"]
PRIORITIES = ["low", "medium", "high"]
RECURRENCES = ["none", "daily", "weekly", "monthly"]


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None, database=None):
        super().__init__(parent)
        self.setWindowTitle("Edit task" if task else "New task")
        self.setMinimumWidth(500)
        self.database = database

        form = QFormLayout(self)
        self.title = QLineEdit()
        self.title_preset = QComboBox()
        self.title_preset.setPlaceholderText("Choose a predefined title...")
        self.title_preset.currentIndexChanged.connect(self._apply_title_preset)
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
        form.addRow("Preset title", self.title_preset)
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

        self._load_managed_values()
        self.category.currentTextChanged.connect(self._refresh_title_presets)

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

        self._refresh_title_presets(self.category.currentText())

    def _load_managed_values(self):
        if not self.database:
            return
        self.category.clear()
        self.category.addItems([row["name"] for row in self.database.list_categories()])
        tags = [row["name"] for row in self.database.list_tags()]
        if tags:
            completer = QCompleter(tags, self.tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.tags.setCompleter(completer)

    def _refresh_title_presets(self, category_name):
        self.title_preset.blockSignals(True)
        self.title_preset.clear()
        if self.database:
            category_id = next(
                (row["id"] for row in self.database.list_categories()
                 if row["name"] == category_name),
                None,
            )
            if category_id is not None:
                self.title_preset.addItem("Choose a predefined title...", None)
                for row in self.database.list_title_presets(category_id):
                    self.title_preset.addItem(row["title"], row["title"])
        self.title_preset.blockSignals(False)

    def _apply_title_preset(self, index):
        value = self.title_preset.itemData(index)
        if value:
            self.title.setText(value)
            self.title.setFocus()
            self.title.selectAll()

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

    def __init__(self, task, category_style=None, parent=None):
        super().__init__(parent)
        self.task_id = int(task["id"])
        category_style = category_style or {}
        task_view = dict(task)
        task_view["category_color"] = category_style.get("color", "")
        task_view["category_icon"] = category_style.get("icon", "")
        self.setObjectName("taskCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        self.smart_icon = SmartTaskIcon(task_view, 44)
        root.addWidget(self.smart_icon, 0, Qt.AlignmentFlag.AlignTop)

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
        category_color = category_style.get("color", "#9d7cff")
        category_icon = category_style.get("icon", "✓")
        category_label = QLabel(f"{category_icon}  {category}")
        category_label.setObjectName("categoryBadge")
        category_label.setStyleSheet(
            f"color:{category_color}; font-weight:600;"
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

        top_actions = QHBoxLayout()
        top_actions.setSpacing(6)
        priority = QLabel(task["priority"].upper())
        priority.setObjectName(f"priority_{task['priority']}")
        top_actions.addWidget(priority)
        top_actions.addStretch()

        more = QToolButton()
        more.setText("⋯")
        more.setObjectName("cardMoreButton")
        more.clicked.connect(self._show_menu)
        top_actions.addWidget(more)
        actions.addLayout(top_actions)

        self.check = AnimatedCheck(bool(task["completed"]))
        self.check.checkedChanged.connect(
            lambda checked: self.completionChanged.emit(self.task_id, checked)
        )
        actions.addWidget(self.check, 0, Qt.AlignmentFlag.AlignRight)
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
            ("Manage", "⚙", 3),
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
            [("Tasks", "✓", 0), ("Dashboard", "▦", 1), ("Agenda", "◷", 2), ("Manage", "⚙", 3)],
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
        self._build_manage_page()

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
        self.category_filter.addItems(["All categories"] + self.category_names())
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
        self.agenda.timeline.taskCompletionRequested.connect(self.set_task_completed)
        self.agenda.timeline.taskMoved.connect(self.move_agenda_task)
        self.agenda.timeline.taskResized.connect(self.resize_agenda_task)
        self.stack.addWidget(self.agenda)

    def category_names(self):
        return [row["name"] for row in self.database.list_categories()]

    def _build_manage_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Manage")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        subtitle = QLabel("Categories, tags and predefined task titles")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        self.category_list = QListWidget()
        tabs.addTab(
            self._manager_tab(
                self.category_list, self._add_category,
                self._edit_category, self._delete_category
            ),
            "Categories",
        )

        self.tag_list = QListWidget()
        tabs.addTab(
            self._manager_tab(
                self.tag_list, self._add_tag,
                self._edit_tag, self._delete_tag
            ),
            "Tags",
        )

        preset_page = QWidget()
        preset_layout = QVBoxLayout(preset_page)
        self.preset_category = QComboBox()
        self.preset_category.currentIndexChanged.connect(self.refresh_title_presets)
        self.preset_list = QListWidget()
        preset_layout.addWidget(QLabel("Predefined titles depend on the selected category."))
        preset_layout.addWidget(self.preset_category)
        preset_layout.addWidget(self.preset_list, 1)
        row = QHBoxLayout()
        for label, slot in (
            ("+ Add title", self._add_title_preset),
            ("Edit", self._edit_title_preset),
            ("Delete", self._delete_title_preset),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        preset_layout.addLayout(row)
        tabs.addTab(preset_page, "Title presets")

    def _manager_tab(self, widget, add_slot, edit_slot, delete_slot):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(widget, 1)
        row = QHBoxLayout()
        for label, slot in (("+ Add", add_slot), ("Edit", edit_slot), ("Delete", delete_slot)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        return page

    def refresh_manage(self):
        self.category_list.clear()
        for row in self.database.list_categories():
            item = QListWidgetItem(f"{row['icon']}  {row['name']}")
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setForeground(QColor(row["color"]))
            self.category_list.addItem(item)

        self.tag_list.clear()
        for row in self.database.list_tags():
            item = QListWidgetItem("#" + row["name"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.tag_list.addItem(item)

        current = self.preset_category.currentData() if self.preset_category.count() else None
        self.preset_category.blockSignals(True)
        self.preset_category.clear()
        for row in self.database.list_categories():
            self.preset_category.addItem(row["name"], row["id"])
        if current is not None:
            idx = self.preset_category.findData(current)
            if idx >= 0:
                self.preset_category.setCurrentIndex(idx)
        self.preset_category.blockSignals(False)
        self.refresh_title_presets()

        current_category = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories")
        self.category_filter.addItems(self.category_names())
        self.category_filter.setCurrentText(current_category if current_category else "All categories")
        self.category_filter.blockSignals(False)

    def _prompt_name(self, title, label, value=""):
        text, ok = QInputDialog.getText(self, title, label, text=value)
        return text.strip(), ok

    def _category_editor(self, title, name="", color="#9d7cff", icon="✓"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(420)
        form = QFormLayout(dialog)

        name_edit = QLineEdit(name)
        icon_edit = QLineEdit(icon)
        icon_edit.setMaxLength(4)
        icon_edit.setPlaceholderText("Emoji or symbol")

        color_button = QPushButton(color)
        color_button.setStyleSheet(
            f"background:{color}; color:#ffffff; font-weight:700; padding:8px;"
        )

        def choose_color():
            chosen = QColorDialog.getColor(
                QColor(color_button.text()), dialog, "Choose category color"
            )
            if chosen.isValid():
                value = chosen.name()
                color_button.setText(value)
                color_button.setStyleSheet(
                    f"background:{value}; color:#ffffff; font-weight:700; padding:8px;"
                )

        color_button.clicked.connect(choose_color)
        form.addRow("Name", name_edit)
        form.addRow("Icon", icon_edit)
        form.addRow("Color", color_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        name_value = name_edit.text().strip()
        icon_value = icon_edit.text().strip() or "✓"
        color_value = color_button.text().strip() or "#9d7cff"
        if not name_value:
            QMessageBox.warning(self, "TaskFlow", "Category name cannot be empty.")
            return None
        return name_value, color_value, icon_value

    def _add_category(self):
        result = self._category_editor("New category")
        if not result:
            return
        name, color, icon = result
        try:
            category_id = self.database.add_category(name)
            self.database.update_category_style(category_id, color, icon)
        except Exception as exc:
            QMessageBox.warning(self, "TaskFlow", f"Cannot create category: {exc}")
        self.refresh_manage()
        self.refresh_tasks()
        self.refresh_agenda()

    def _edit_category(self):
        item = self.category_list.currentItem()
        if not item:
            return
        category_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.database.get_category(category_id)
        if not row:
            return
        result = self._category_editor(
            "Edit category", row["name"], row["color"], row["icon"]
        )
        if not result:
            return
        name, color, icon = result
        try:
            self.database.update_category(category_id, name)
            self.database.update_category_style(category_id, color, icon)
        except Exception as exc:
            QMessageBox.warning(self, "TaskFlow", f"Cannot update category: {exc}")
        self.refresh_manage()
        self.refresh_tasks()
        self.refresh_agenda()

    def _delete_category(self):
        item = self.category_list.currentItem()
        if not item:
            return
        category_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.database.get_category(category_id)
        if not row:
            return
        name = row["name"]
        if name == "Personal":
            QMessageBox.information(
                self, "TaskFlow",
                "Personal is the fallback category and cannot be deleted."
            )
            return
        if QMessageBox.question(
            self, "Delete category",
            f"Delete '{name}'? Existing tasks will move to Personal."
        ) == QMessageBox.StandardButton.Yes:
            self.database.delete_category(category_id)
            self.refresh_manage()
            self.refresh_tasks()
            self.refresh_agenda()

    def _add_tag(self):
        name, ok = self._prompt_name("New tag", "Tag name:")
        if ok and name:
            try:
                self.database.add_tag(name)
            except Exception as exc:
                QMessageBox.warning(self, "TaskFlow", f"Cannot create tag: {exc}")
            self.refresh_manage()

    def _edit_tag(self):
        item = self.tag_list.currentItem()
        if not item:
            return
        name, ok = self._prompt_name("Edit tag", "Tag name:", item.text().lstrip("#"))
        if ok and name:
            try:
                self.database.update_tag(item.data(Qt.ItemDataRole.UserRole), name)
            except Exception as exc:
                QMessageBox.warning(self, "TaskFlow", f"Cannot update tag: {exc}")
            self.refresh_manage()
            self.refresh_tasks()

    def _delete_tag(self):
        item = self.tag_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "Delete tag", f"Delete {item.text()} from the tag library and existing tasks?") == QMessageBox.StandardButton.Yes:
            self.database.delete_tag(item.data(Qt.ItemDataRole.UserRole))
            self.refresh_manage()
            self.refresh_tasks()

    def refresh_title_presets(self):
        self.preset_list.clear()
        category_id = self.preset_category.currentData()
        if category_id is None:
            return
        for row in self.database.list_title_presets(category_id):
            item = QListWidgetItem(row["title"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.preset_list.addItem(item)

    def _add_title_preset(self):
        category_id = self.preset_category.currentData()
        if category_id is None:
            return
        title, ok = self._prompt_name("New predefined title", "Title:")
        if ok and title:
            try:
                self.database.add_title_preset(category_id, title)
            except Exception as exc:
                QMessageBox.warning(self, "TaskFlow", f"Cannot create title preset: {exc}")
            self.refresh_title_presets()

    def _edit_title_preset(self):
        item = self.preset_list.currentItem()
        category_id = self.preset_category.currentData()
        if not item or category_id is None:
            return
        title, ok = self._prompt_name("Edit predefined title", "Title:", item.text())
        if ok and title:
            try:
                self.database.update_title_preset(item.data(Qt.ItemDataRole.UserRole), category_id, title)
            except Exception as exc:
                QMessageBox.warning(self, "TaskFlow", f"Cannot update title preset: {exc}")
            self.refresh_title_presets()

    def _delete_title_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "Delete predefined title", f"Delete '{item.text()}'?") == QMessageBox.StandardButton.Yes:
            self.database.delete_title_preset(item.data(Qt.ItemDataRole.UserRole))
            self.refresh_title_presets()

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

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)
        if index == 0:
            self.refresh_tasks()
        elif index == 1:
            self.refresh_dashboard()
        elif index == 2:
            self.refresh_agenda()
        elif index == 3:
            self.refresh_manage()

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
                card = TaskCard(task, self.database.category_style(task["category"] or "Personal"))
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
        decorated = []
        for task in tasks:
            item = dict(task)
            style = self.database.category_style(task["category"] or "Personal")
            item["category_color"] = style["color"]
            item["category_icon"] = style["icon"]
            decorated.append(item)
        self.agenda.set_tasks(decorated)

    def search_changed(self):
        if self.stack.currentIndex() == 0:
            self.refresh_tasks()

    def new_task(self, preferred_date=None):
        dialog = TaskDialog(self, database=self.database)
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
        dialog = TaskDialog(self, task, self.database)
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
