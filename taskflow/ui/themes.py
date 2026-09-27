from PySide6.QtCore import QSettings

THEMES = {
    "Midnight": """
        #appRoot { background:#10131a; }
        #sidebar { background:#141820; border-right:1px solid #303746; }
        #sidebarToggle,#iconButton { min-width:40px; max-width:40px; padding:8px; font-size:18px; }
        #sidebarBrand { font-size:22px; font-weight:700; color:#9d7cff; padding:4px 8px; }
        #sidebarHint { color:#7f8898; padding:8px; }
        #navButton { text-align:left; min-height:44px; padding:10px 12px; background:transparent; border:0; }
        #navButton:hover { background:#1d2330; }
        #navButton:checked { background:#27203f; color:#b7a2ff; border:1px solid #4d3a78; }
        #appSubtitle,#taskCardMeta,#taskCardTags,#dayCount,#emptyHint { color:#7f8898; }
        #primaryButton { background:#6d4aff; color:#ffffff; border:0; font-weight:700; }
        #primaryButton:hover { background:#7d5cff; }
        #taskCard { background:#181c25; border:1px solid #303746; border-radius:14px; }
        #taskCard:hover { border-color:#5b4b83; background:#1b202b; }
        #taskCard[completed="true"] { opacity:0.72; }
        #taskCardTitle { font-size:15px; font-weight:650; }
        #taskCardTags { font-size:12px; }
        #cardMoreButton { min-width:28px; max-width:28px; padding:3px; border:0; background:transparent; font-size:18px; }
        #priority_high { color:#ff8f8f; font-size:11px; font-weight:700; }
        #priority_medium { color:#9ca9ff; font-size:11px; font-weight:700; }
        #priority_low { color:#67cdb8; font-size:11px; font-weight:700; }
        #dayTitle { font-size:18px; font-weight:700; }
        #sectionLine { color:#303746; }
        #emptyTitle { font-size:20px; font-weight:700; color:#e7eaf0; }
        #dayButton { min-height:58px; background:#181c25; border:1px solid #303746; border-radius:12px; padding:7px; font-weight:600; }
        #dayButton:hover { background:#222836; }
        #dayButton:checked { background:#6d4aff; color:#ffffff; border-color:#6d4aff; }
        QMenu { padding:6px; }

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
        #appRoot { background:#f3f5f8; }
        #sidebar { background:#ffffff; border-right:1px solid #d5d9e0; }
        #sidebarToggle,#iconButton { min-width:40px; max-width:40px; padding:8px; font-size:18px; }
        #sidebarBrand { font-size:22px; font-weight:700; color:#5b3cc4; padding:4px 8px; }
        #sidebarHint { color:#697281; padding:8px; }
        #navButton { text-align:left; min-height:44px; padding:10px 12px; background:transparent; border:0; }
        #navButton:hover { background:#eef0f4; }
        #navButton:checked { background:#eee9ff; color:#5b3cc4; border:1px solid #d7cbff; }
        #appSubtitle,#taskCardMeta,#taskCardTags,#dayCount,#emptyHint { color:#697281; }
        #primaryButton { background:#6d4aff; color:#ffffff; border:0; font-weight:700; }
        #primaryButton:hover { background:#5b3cc4; }
        #taskCard { background:#ffffff; border:1px solid #d5d9e0; border-radius:14px; }
        #taskCard:hover { border-color:#b9aae8; }
        #taskCard[completed="true"] { opacity:0.72; }
        #taskCardTitle { font-size:15px; font-weight:650; }
        #taskCardTags { font-size:12px; }
        #priority_high { color:#c03d48; font-size:11px; font-weight:700; }
        #priority_medium { color:#5b5fd6; font-size:11px; font-weight:700; }
        #priority_low { color:#19866f; font-size:11px; font-weight:700; }
        #dayTitle { font-size:18px; font-weight:700; }
        #sectionLine { color:#d5d9e0; }
        #emptyTitle { font-size:20px; font-weight:700; color:#20242b; }
        #dayButton { min-height:58px; background:#ffffff; border:1px solid #cbd1da; border-radius:12px; padding:7px; font-weight:600; }
        #dayButton:hover { background:#eef1f5; }
        #dayButton:checked { background:#6d4aff; color:#ffffff; border-color:#6d4aff; }

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
        #appRoot { background:#0b0712; }
        #sidebar { background:#100a18; border-right:1px solid #7b2cff; }
        #sidebarToggle,#iconButton { min-width:40px; max-width:40px; padding:8px; font-size:18px; }
        #sidebarBrand { font-size:22px; font-weight:700; color:#ff4fd8; padding:4px 8px; }
        #sidebarHint { color:#bfa9d5; padding:8px; }
        #navButton { text-align:left; min-height:44px; padding:10px 12px; background:transparent; border:0; }
        #navButton:hover { background:#1b1030; }
        #navButton:checked { background:#2a1547; color:#ff4fd8; border:1px solid #7b2cff; }
        #appSubtitle,#taskCardMeta,#taskCardTags,#dayCount,#emptyHint { color:#bfa9d5; }
        #primaryButton { background:#ff2fcf; color:#ffffff; border:0; font-weight:700; }
        #primaryButton:hover { background:#ff4fd8; }
        #taskCard { background:#130d1f; border:1px solid #7b2cff; border-radius:14px; }
        #taskCard:hover { border-color:#ff2fcf; }
        #taskCard[completed="true"] { opacity:0.72; }
        #taskCardTitle { font-size:15px; font-weight:650; }
        #taskCardTags { font-size:12px; }
        #priority_high { color:#ff6b9b; font-size:11px; font-weight:700; }
        #priority_medium { color:#8b7cff; font-size:11px; font-weight:700; }
        #priority_low { color:#48e0c1; font-size:11px; font-weight:700; }
        #dayTitle { font-size:18px; font-weight:700; }
        #sectionLine { color:#7b2cff; }
        #emptyTitle { font-size:20px; font-weight:700; color:#f4edff; }
        #dayButton { min-height:58px; background:#130d1f; border:1px solid #7b2cff; border-radius:12px; padding:7px; font-weight:600; }
        #dayButton:hover { background:#1b1030; }
        #dayButton:checked { background:#ff2fcf; color:#ffffff; border-color:#ff2fcf; }

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
        #appRoot { background:#07131c; }
        #sidebar { background:#091923; border-right:1px solid #185a70; }
        #sidebarToggle,#iconButton { min-width:40px; max-width:40px; padding:8px; font-size:18px; }
        #sidebarBrand { font-size:22px; font-weight:700; color:#45d7ff; padding:4px 8px; }
        #sidebarHint { color:#9bc6d6; padding:8px; }
        #navButton { text-align:left; min-height:44px; padding:10px 12px; background:transparent; border:0; }
        #navButton:hover { background:#123040; }
        #navButton:checked { background:#123c4d; color:#45d7ff; border:1px solid #237c99; }
        #appSubtitle,#taskCardMeta,#taskCardTags,#dayCount,#emptyHint { color:#9bc6d6; }
        #primaryButton { background:#16a8d4; color:#ffffff; border:0; font-weight:700; }
        #primaryButton:hover { background:#45d7ff; }
        #taskCard { background:#0d202b; border:1px solid #185a70; border-radius:14px; }
        #taskCard:hover { border-color:#237c99; }
        #taskCard[completed="true"] { opacity:0.72; }
        #taskCardTitle { font-size:15px; font-weight:650; }
        #taskCardTags { font-size:12px; }
        #priority_high { color:#ff8b8b; font-size:11px; font-weight:700; }
        #priority_medium { color:#77b9ff; font-size:11px; font-weight:700; }
        #priority_low { color:#62c4b2; font-size:11px; font-weight:700; }
        #dayTitle { font-size:18px; font-weight:700; }
        #sectionLine { color:#185a70; }
        #emptyTitle { font-size:20px; font-weight:700; color:#e8f7ff; }
        #dayButton { min-height:58px; background:#0d202b; border:1px solid #185a70; border-radius:12px; padding:7px; font-weight:600; }
        #dayButton:hover { background:#123040; }
        #dayButton:checked { background:#16a8d4; color:#ffffff; border-color:#16a8d4; }

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
