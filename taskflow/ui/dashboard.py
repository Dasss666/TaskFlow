from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class StatCard(QFrame):
    def __init__(self, title, value="0", subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("statSubtitle")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.subtitle)

    def set_value(self, value, subtitle=""):
        self.value.setText(str(value))
        self.subtitle.setText(subtitle)


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        title = QLabel("Productivity dashboard")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        self.range_label = QLabel()
        root.addWidget(self.range_label)

        cards = QGridLayout()
        self.total = StatCard("Total tasks")
        self.completed = StatCard("Completed")
        self.open = StatCard("Open")
        self.high = StatCard("High priority open")
        cards.addWidget(self.total, 0, 0)
        cards.addWidget(self.completed, 0, 1)
        cards.addWidget(self.open, 0, 2)
        cards.addWidget(self.high, 0, 3)
        root.addLayout(cards)

        progress_box = QVBoxLayout()
        progress_title = QLabel("Completion rate")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("%p%")
        progress_box.addWidget(progress_title)
        progress_box.addWidget(self.progress)
        root.addLayout(progress_box)

        root.addWidget(QLabel("Tasks by category"))
        self.categories = QVBoxLayout()
        root.addLayout(self.categories)
        root.addStretch()

    def clear_categories(self):
        while self.categories.count():
            item = self.categories.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_stats(self, row, category_rows, date_from=None, date_to=None):
        total = int(row["total"] or 0)
        completed = int(row["completed"] or 0)
        open_count = int(row["open"] or 0)
        high = int(row["high_open"] or 0)
        rate = round((completed / total) * 100) if total else 0

        self.total.set_value(total, "tasks in selected range")
        self.completed.set_value(completed, f"{rate}% of total")
        self.open.set_value(open_count, "not completed")
        self.high.set_value(high, "need attention")
        self.progress.setValue(rate)
        self.range_label.setText(
            f"Range: {date_from or 'All dates'} → {date_to or 'All dates'}"
        )

        self.clear_categories()
        if not category_rows:
            self.categories.addWidget(QLabel("No data for this range."))
            return

        for category in category_rows:
            name = category["category"] or "Uncategorized"
            total_cat = int(category["total"] or 0)
            completed_cat = int(category["completed"] or 0)
            rate_cat = round((completed_cat / total_cat) * 100) if total_cat else 0
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            label = QLabel(f"{name}  •  {completed_cat}/{total_cat}")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(rate_cat)
            bar.setFormat(f"{rate_cat}%")
            row_layout.addWidget(label, 1)
            row_layout.addWidget(bar, 2)
            self.categories.addWidget(row_widget)
