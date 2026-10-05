"""
GTZ ID Studio - Main Window
Central hub with sidebar navigation and page stacking.
"""
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QStatusBar,
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

from core.database import DatabaseManager
from core.renderer import CardRenderer
from core.printer import PrintManager

from ui.pages.dashboard_page import DashboardPage
from ui.pages.database_page import DatabasePage
from ui.pages.template_page import TemplatePage
from ui.pages.qr_page import QRPage
from ui.pages.preview_page import PreviewPage
from ui.pages.print_page import PrintPage
from ui.pages.settings_page import SettingsPage


NAV_ITEMS = [
    ("🏠", "Dashboard", 0),
    ("👥", "Staff Database", 1),
    ("🎨", "Templates", 2),
    ("📱", "QR Codes", 3),
    ("👁", "Preview", 4),
    ("🖨", "Print", 5),
    ("⚙", "Settings", 6),
]


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.renderer = CardRenderer(db.settings.get("last_qr_folder", ""))
        self.print_manager = PrintManager()
        self.active_template = None
        self.active_template_config = {}

        self.setWindowTitle("GTZ ID Studio — Staff ID Card Manager")
        self.setMinimumSize(1200, 780)
        self.resize(1360, 860)

        self._setup_ui()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.set_status("Ready  •  GTZ ID Studio v1.0")

        # Start on dashboard
        self.navigate_to(0)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")

        self.pages = {
            0: DashboardPage(self),
            1: DatabasePage(self),
            2: TemplatePage(self),
            3: QRPage(self),
            4: PreviewPage(self),
            5: PrintPage(self),
            6: SettingsPage(self),
        }
        for idx, page in self.pages.items():
            self.stack.addWidget(page)

        root_layout.addWidget(self.stack, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(260)
        sidebar.setStyleSheet("background-color: #1A2340;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand_widget = QWidget()
        brand_widget.setStyleSheet("background-color: #1A2340;")
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(16, 20, 16, 8)
        brand_layout.setSpacing(2)

        title = QLabel("GTZ ID Studio")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #FFD700; font-size: 12pt; font-weight: bold;")

        subtitle = QLabel("Staff ID Card Manager")
        subtitle.setStyleSheet("color: #7B88A8; font-size: 8pt;")

        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand_widget)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #2A3354; margin: 0px 16px;")
        layout.addWidget(div)
        layout.addSpacing(8)

        self.nav_buttons = {}
        for icon, label, idx in NAV_ITEMS:
            btn = QPushButton("  {}  {}".format(icon, label))
            btn.setFixedHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #A0ADCA;
                    border: none;
                    text-align: left;
                    padding: 0px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #253056;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(lambda checked, i=idx: self.navigate_to(i))
            self.nav_buttons[idx] = btn
            layout.addWidget(btn)

        layout.addStretch()

        db_label = QLabel("📁  Local Database")
        db_label.setStyleSheet("color: #4A5578; font-size: 8pt; padding: 12px 16px 4px 16px;")
        layout.addWidget(db_label)

        self.db_path_label = QLabel(self._short_path(self.db.current_db_path))
        self.db_path_label.setStyleSheet("color: #7B88A8; font-size: 7.5pt; padding: 0px 16px 16px 16px;")
        self.db_path_label.setWordWrap(True)
        layout.addWidget(self.db_path_label)

        return sidebar

    def _short_path(self, path: str) -> str:
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    def navigate_to(self, index: int):
        for idx, btn in self.nav_buttons.items():
            if idx == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2E5BFF;
                        color: #FFFFFF;
                        border: none;
                        text-align: left;
                        padding: 0px 16px;
                        font-size: 10pt;
                        font-weight: bold;
                        border-left: 3px solid #5B8DFF;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #A0ADCA;
                        border: none;
                        text-align: left;
                        padding: 0px 16px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #253056;
                        color: #FFFFFF;
                    }
                """)

        self.stack.setCurrentIndex(index)

        page = self.pages.get(index)
        if page and hasattr(page, "on_activate"):
            page.on_activate()

    def set_status(self, msg: str):
        self.status_bar.showMessage("  {}".format(msg))

    def update_db_label(self):
        self.db_path_label.setText(self._short_path(self.db.current_db_path))

    def get_active_template(self):
        return self.active_template, self.active_template_config

    def set_active_template(self, name: str, path: str, config: dict):
        self.active_template = {"name": name, "file_path": path}
        self.active_template_config = config
        self.set_status("Template: {}".format(name))