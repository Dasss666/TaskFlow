from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


CATEGORY_COLORS = {
    "Personal": "#ff8585",
    "University": "#8f9cff",
    "Work": "#f0b35b",
    "Health": "#63d2b3",
    "Projects": "#c48cff",
}


ICON_RULES = [
    (("wake", "bed", "sleep", "morning", "night", "breakfast"), "☀"),
    (("study", "studiare", "exam", "esame", "lecture", "lezione", "university", "uni"), "📚"),
    (("code", "coding", "program", "programmare", "github", "software", "debug"), "⌨"),
    (("work", "meeting", "call", "office", "lavoro", "riunione"), "💼"),
    (("gym", "workout", "run", "running", "sport", "allenamento", "palestra"), "⚡"),
    (("doctor", "dentist", "medicine", "health", "doctor", "medico", "salute"), "♥"),
    (("shop", "shopping", "grocer", "spesa", "supermarket"), "🛒"),
    (("food", "lunch", "dinner", "meal", "pranzo", "cena", "mangiare"), "🍴"),
    (("travel", "trip", "flight", "vacation", "viaggio", "vacanza", "aereo"), "✈"),
    (("money", "pay", "bill", "finance", "pagamento", "bolletta"), "€"),
    (("home", "house", "clean", "casa", "pulire"), "⌂"),
    (("game", "gaming", "play", "gioco"), "🎮"),
    (("read", "book", "reading", "leggere", "libro"), "📖"),
    (("email", "mail", "message", "messaggio"), "✉"),
    (("call", "phone", "telefonata"), "☎"),
    (("focus", "deep work", "concentrate", "focus"), "◎"),
]


def _value(task, key, default=""):
    try:
        return task[key]
    except (KeyError, TypeError, IndexError):
        return default


def smart_icon(task) -> str:
    """Pick a lightweight icon from task title/category/tags/description."""
    custom_icon = str(_value(task, "category_icon") or "").strip()
    if custom_icon:
        return custom_icon
    title = str(_value(task, "title") or "").lower()
    category = str(_value(task, "category") or "").lower()
    tags = str(_value(task, "tags") or "").lower()
    description = str(_value(task, "description") or "").lower()
    text = " ".join((title, tags, description))

    for keywords, icon in ICON_RULES:
        if any(re.search(r"\b" + re.escape(keyword) + r"\b", text) for keyword in keywords):
            return icon

    if "university" in category:
        return "📚"
    if "work" in category:
        return "💼"
    if "health" in category:
        return "♥"
    if "project" in category:
        return "◇"
    return "✓"


def icon_color(task) -> QColor:
    custom_color = str(_value(task, "category_color") or "").strip()
    if custom_color:
        return QColor(custom_color)
    category = str(_value(task, "category") or "Personal")
    return QColor(CATEGORY_COLORS.get(category, "#9d7cff"))


class SmartTaskIcon(QWidget):
    """Small Structured-inspired circular smart icon for task cards."""

    def __init__(self, task, size=42, parent=None):
        super().__init__(parent)
        self.task = task
        self.size = size
        self.setFixedSize(size, size)
        self.setToolTip(f"Smart icon: {smart_icon(task)}")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = icon_color(self.task)
        background = QColor(color)
        background.setAlpha(38)

        center = self.rect().center()
        radius = self.size / 2 - 2

        painter.setBrush(QBrush(background))
        painter.setPen(QPen(color, 1.4))
        painter.drawEllipse(center, radius, radius)

        painter.setPen(QPen(color, 1))
        font = QFont("Segoe UI Emoji", max(12, int(self.size * 0.38)))
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, smart_icon(self.task))
