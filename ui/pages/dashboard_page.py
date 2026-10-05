"""
GTZ ID Studio - Dashboard Page
Overview and quick actions.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatCard(QWidget):
    def __init__(self, icon: str, value: str, label: str, color: str):
        super().__init__()
        self.setFixedSize(200, 110)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #FFFFFF;
                border-radius: 10px;
                border: 1px solid #E5E7EB;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 22px; background: none; border: none;")
        val_lbl = QLabel(value)
        val_lbl.setObjectName("StatValue")
        val_lbl.setStyleSheet(f"font-size: 26pt; font-weight: bold; color: {color}; background: none; border: none;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(icon_lbl)
        top.addStretch()
        top.addWidget(val_lbl)

        name_lbl = QLabel(label)
        name_lbl.setStyleSheet("color: #6B7280; font-size: 9pt; background: none; border: none;")

        layout.addLayout(top)
        layout.addWidget(name_lbl)
        self.val_lbl = val_lbl

    def update_value(self, val: str):
        self.val_lbl.setText(val)


class QuickActionBtn(QPushButton):
    def __init__(self, icon: str, label: str):
        super().__init__(f"  {icon}  {label}")
        self.setFixedHeight(42)
        self.setObjectName("SecondaryBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #374151;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 0px 16px;
                font-size: 9.5pt;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F0F4FF;
                border-color: #2E5BFF;
                color: #2E5BFF;
            }
        """)


class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        header = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        sub = QLabel("Welcome to GTZ ID Studio — your staff card management hub.")
        sub.setStyleSheet("font-size: 9.5pt; color: #6B7280;")
        header.addWidget(title)
        header.addWidget(sub)
        layout.addLayout(header)

        # Stat cards row
        self.stat_row = QHBoxLayout()
        self.stat_row.setSpacing(14)

        self.card_total = StatCard("👥", "0", "Total Staff", "#2E5BFF")
        self.card_templates = StatCard("🎨", "0", "Templates", "#10B981")
        self.card_qr = StatCard("📱", "0", "QR Codes Linked", "#F59E0B")
        self.card_printed = StatCard("🖨", "0", "Cards Printed", "#8B5CF6")

        for c in [self.card_total, self.card_templates, self.card_qr, self.card_printed]:
            self.stat_row.addWidget(c)
        self.stat_row.addStretch()
        layout.addLayout(self.stat_row)

        # Main content: quick actions + recent activity
        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Quick actions panel
        qa_panel = QFrame()
        qa_panel.setObjectName("Card")
        qa_panel.setStyleSheet("QFrame#Card { background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E7EB; }")
        qa_layout = QVBoxLayout(qa_panel)
        qa_layout.setContentsMargins(20, 16, 20, 20)
        qa_layout.setSpacing(10)

        qa_title = QLabel("Quick Actions")
        qa_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1A1F36; margin-bottom: 6px;")
        qa_layout.addWidget(qa_title)

        actions = [
            ("👥", "Add New Staff", lambda: self.main.navigate_to(1)),
            ("📂", "Import Database", lambda: self.main.navigate_to(1)),
            ("🎨", "Load Template", lambda: self.main.navigate_to(2)),
            ("📱", "Set QR Folder", lambda: self.main.navigate_to(3)),
            ("👁", "Preview Cards", lambda: self.main.navigate_to(4)),
            ("🖨", "Print Cards", lambda: self.main.navigate_to(5)),
        ]

        for icon, label, callback in actions:
            btn = QuickActionBtn(icon, label)
            btn.clicked.connect(callback)
            qa_layout.addWidget(btn)

        qa_layout.addStretch()
        content_row.addWidget(qa_panel)

        # Status / info panel
        info_panel = QFrame()
        info_panel.setObjectName("Card")
        info_panel.setStyleSheet("QFrame#Card { background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E7EB; }")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(20, 16, 20, 20)

        info_title = QLabel("System Status")
        info_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1A1F36; margin-bottom: 12px;")
        info_layout.addWidget(info_title)

        self.status_items = {}
        items = [
            ("database", "🗄", "Database", "Not connected"),
            ("template", "🎨", "Active Template", "None loaded"),
            ("qr_folder", "📁", "QR Folder", "Not set"),
            ("printer", "🖨", "Default Printer", "Detecting..."),
        ]
        for key, icon, label, default in items:
            row = QHBoxLayout()
            lbl = QLabel(f"{icon}  {label}")
            lbl.setStyleSheet("color: #374151; font-size: 9.5pt; min-width: 140px;")
            val = QLabel(default)
            val.setStyleSheet("color: #6B7280; font-size: 9pt;")
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, stretch=1)
            info_layout.addLayout(row)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("background-color: #F3F4F6; max-height: 1px; margin: 6px 0px;")
            info_layout.addWidget(sep)

            self.status_items[key] = val

        info_layout.addStretch()

        # Getting started
        gs_title = QLabel("Getting Started")
        gs_title.setStyleSheet("font-size: 10pt; font-weight: bold; color: #374151; margin-top: 12px;")
        info_layout.addWidget(gs_title)

        steps = [
            "1. Import or create your staff database",
            "2. Load a card template (PNG/SVG)",
            "3. Set the QR codes folder",
            "4. Preview cards for each staff member",
            "5. Print single or batch cards",
        ]
        for step in steps:
            s = QLabel(step)
            s.setStyleSheet("color: #6B7280; font-size: 8.5pt; padding: 2px 0px;")
            info_layout.addWidget(s)

        content_row.addWidget(info_panel, stretch=1)
        layout.addLayout(content_row, stretch=1)

    def on_activate(self):
        """Refresh stats when page is shown."""
        staff = self.main.db.get_all_staff()
        templates = self.main.db.get_all_templates()

        self.card_total.update_value(str(len(staff)))
        self.card_templates.update_value(str(len(templates)))

        # Count QR matches
        qr_folder = self.main.db.settings.get("last_qr_folder", "")
        qr_count = 0
        if qr_folder:
            import os
            for s in staff:
                if self.main.renderer.find_qr_for_staff(s):
                    qr_count += 1
        self.card_qr.update_value(str(qr_count))

        # Status items
        db_path = self.main.db.current_db_path
        self.status_items["database"].setText(self._shorten(db_path))
        self.status_items["database"].setStyleSheet("color: #10B981; font-size: 9pt;")

        tmpl = self.main.active_template
        if tmpl:
            self.status_items["template"].setText(tmpl.get("name", "Unknown"))
            self.status_items["template"].setStyleSheet("color: #10B981; font-size: 9pt;")
        else:
            self.status_items["template"].setText("None loaded")
            self.status_items["template"].setStyleSheet("color: #F59E0B; font-size: 9pt;")

        if qr_folder:
            self.status_items["qr_folder"].setText(self._shorten(qr_folder))
            self.status_items["qr_folder"].setStyleSheet("color: #10B981; font-size: 9pt;")
        else:
            self.status_items["qr_folder"].setText("Not set")
            self.status_items["qr_folder"].setStyleSheet("color: #F59E0B; font-size: 9pt;")

        printer = self.main.print_manager.get_default_printer()
        self.status_items["printer"].setText(printer or "No printer found")
        self.status_items["printer"].setStyleSheet(
            "color: #10B981; font-size: 9pt;" if printer else "color: #EF4444; font-size: 9pt;"
        )

    def _shorten(self, path: str) -> str:
        import os
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        if len(path) > 40:
            path = "..." + path[-37:]
        return path
