from PySide6.QtCore import QSettings

THEMES = {
    "Midnight": """
        QWidget { font-size: 14px; }
        QMainWindow { background: #10131a; }
        QLabel { color: #e7eaf0; }
        #appTitle { font-size: 28px; font-weight: 700; color: #9d7cff; }
        #pageTitle { font-size: 22px; font-weight: 700; color: #e7eaf0; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget {
            background:#181c25;color:#e7eaf0;border:1px solid #303746;border-radius:8px;padding:8px;
        }
        QPushButton { background:#252b38;color:#e7eaf0;border:1px solid #394152;border-radius:8px;padding:9px 14px; }
        QPushButton:hover { background:#303746; }
        QCalendarWidget QWidget { background:#181c25;color:#e7eaf0; }
        QCalendarWidget QAbstractItemView { selection-background-color:#6d4aff; }
        QMenuBar,QMenu { background:#141820;color:#e7eaf0; }
        QProgressBar { background:#181c25;color:#e7eaf0;border:1px solid #303746;border-radius:7px;text-align:center; }
        QProgressBar::chunk { background:#6d4aff;border-radius:6px; }
        #statCard { background:#181c25;border:1px solid #303746;border-radius:12px; padding:8px; }
        #statValue { font-size:28px;font-weight:700;color:#9d7cff; }
        #statSubtitle { color:#9aa3b2; }
        QScrollArea { border:1px solid #303746;border-radius:8px;background:#11151d; }
    """,
    "Light": """
        QWidget { font-size: 14px; }
        QMainWindow { background:#f3f5f8; }
        QLabel { color:#20242b; }
        #appTitle { font-size:28px;font-weight:700;color:#5b3cc4; }
        #pageTitle { font-size:22px;font-weight:700;color:#20242b; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget { background:#ffffff;color:#20242b;border:1px solid #cbd1da;border-radius:8px;padding:8px; }
        QPushButton { background:#e7eaf0;color:#20242b;border:1px solid #c1c7d0;border-radius:8px;padding:9px 14px; }
        QPushButton:hover { background:#d9dee7; }
        QCalendarWidget QWidget { background:#ffffff;color:#20242b; }
        QCalendarWidget QAbstractItemView { selection-background-color:#6d4aff; selection-color:#ffffff; }
        QMenuBar,QMenu { background:#ffffff;color:#20242b; }
        QProgressBar { background:#ffffff;color:#20242b;border:1px solid #cbd1da;border-radius:7px;text-align:center; }
        QProgressBar::chunk { background:#6d4aff;border-radius:6px; }
        #statCard { background:#ffffff;border:1px solid #d5d9e0;border-radius:12px;padding:8px; }
        #statValue { font-size:28px;font-weight:700;color:#5b3cc4; }
        #statSubtitle { color:#697281; }
        QScrollArea { border:1px solid #cbd1da;border-radius:8px;background:#eef1f5; }
    """,
    "Cyberpunk": """
        QWidget { font-size:14px; }
        QMainWindow { background:#0b0712; }
        QLabel { color:#f4edff; }
        #appTitle { font-size:28px;font-weight:700;color:#ff4fd8; }
        #pageTitle { font-size:22px;font-weight:700;color:#f4edff; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget { background:#130d1f;color:#f4edff;border:1px solid #7b2cff;border-radius:8px;padding:8px; }
        QPushButton { background:#1b1030;color:#f4edff;border:1px solid #b52cff;border-radius:8px;padding:9px 14px; }
        QPushButton:hover { background:#2a1547; }
        QCalendarWidget QWidget { background:#130d1f;color:#f4edff; }
        QCalendarWidget QAbstractItemView { selection-background-color:#ff2fcf;selection-color:#ffffff; }
        QMenuBar,QMenu { background:#100a18;color:#f4edff; }
        QProgressBar { background:#130d1f;color:#f4edff;border:1px solid #7b2cff;border-radius:7px;text-align:center; }
        QProgressBar::chunk { background:#ff2fcf;border-radius:6px; }
        #statCard { background:#130d1f;border:1px solid #7b2cff;border-radius:12px;padding:8px; }
        #statValue { font-size:28px;font-weight:700;color:#ff4fd8; }
        #statSubtitle { color:#bfa9d5; }
        QScrollArea { border:1px solid #7b2cff;border-radius:8px;background:#0f0918; }
    """,
    "Ocean": """
        QWidget { font-size:14px; }
        QMainWindow { background:#07131c; }
        QLabel { color:#e8f7ff; }
        #appTitle { font-size:28px;font-weight:700;color:#45d7ff; }
        #pageTitle { font-size:22px;font-weight:700;color:#e8f7ff; }
        QLineEdit,QPlainTextEdit,QComboBox,QTimeEdit,QListWidget { background:#0d202b;color:#e8f7ff;border:1px solid #185a70;border-radius:8px;padding:8px; }
        QPushButton { background:#123040;color:#e8f7ff;border:1px solid #237c99;border-radius:8px;padding:9px 14px; }
        QPushButton:hover { background:#194457; }
        QCalendarWidget QWidget { background:#0d202b;color:#e8f7ff; }
        QCalendarWidget QAbstractItemView { selection-background-color:#16a8d4;selection-color:#ffffff; }
        QMenuBar,QMenu { background:#091923;color:#e8f7ff; }
        QProgressBar { background:#0d202b;color:#e8f7ff;border:1px solid #185a70;border-radius:7px;text-align:center; }
        QProgressBar::chunk { background:#16a8d4;border-radius:6px; }
        #statCard { background:#0d202b;border:1px solid #185a70;border-radius:12px;padding:8px; }
        #statValue { font-size:28px;font-weight:700;color:#45d7ff; }
        #statSubtitle { color:#9bc6d6; }
        QScrollArea { border:1px solid #185a70;border-radius:8px;background:#081720; }
    """,
}

DEFAULT_THEME = "Midnight"


def load_theme(settings: QSettings) -> str:
    value = settings.value("theme", DEFAULT_THEME)
    return value if value in THEMES else DEFAULT_THEME


def save_theme(settings: QSettings, theme_name: str) -> None:
    settings.setValue("theme", theme_name)
    settings.sync()


def stylesheet(theme_name: str) -> str:
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])
