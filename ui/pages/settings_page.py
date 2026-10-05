"""
GTZ ID Studio - Settings Page
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox,
    QCheckBox, QGroupBox, QMessageBox, QSpinBox, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt


class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        layout.addWidget(title)

        # Database settings
        db_grp = QGroupBox("Database")
        db_form = QFormLayout(db_grp)

        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        self.db_path_edit.setText(self.main.db.current_db_path)
        db_btn = QPushButton("Change Database")
        db_btn.setObjectName("SecondaryBtn")
        db_btn.clicked.connect(self._change_db)
        db_row = QHBoxLayout()
        db_row.addWidget(self.db_path_edit)
        db_row.addWidget(db_btn)
        db_form.addRow("Current Database:", db_row)

        layout.addWidget(db_grp)

        # QR settings
        qr_grp = QGroupBox("QR Codes")
        qr_form = QFormLayout(qr_grp)

        self.qr_folder_edit = QLineEdit()
        self.qr_folder_edit.setReadOnly(True)
        self.qr_folder_edit.setText(self.main.db.settings.get("last_qr_folder", ""))
        qr_btn = QPushButton("Browse Folder")
        qr_btn.setObjectName("SecondaryBtn")
        qr_btn.clicked.connect(self._change_qr_folder)
        qr_row = QHBoxLayout()
        qr_row.addWidget(self.qr_folder_edit)
        qr_row.addWidget(qr_btn)
        qr_form.addRow("QR Codes Folder:", qr_row)

        layout.addWidget(qr_grp)

        # Print defaults
        print_grp = QGroupBox("Default Print Settings")
        print_form = QFormLayout(print_grp)

        self.default_width = QDoubleSpinBox()
        self.default_width.setRange(20, 300)
        self.default_width.setValue(self.main.db.settings.get("card_width_mm", 54.0))
        self.default_width.setSuffix(" mm")

        self.default_height = QDoubleSpinBox()
        self.default_height.setRange(20, 300)
        self.default_height.setValue(self.main.db.settings.get("card_height_mm", 84.5))
        self.default_height.setSuffix(" mm")

        wh_row = QHBoxLayout()
        wh_row.addWidget(QLabel("W:"))
        wh_row.addWidget(self.default_width)
        wh_row.addWidget(QLabel("H:"))
        wh_row.addWidget(self.default_height)
        print_form.addRow("Card Size:", wh_row)

        self.default_copies = QSpinBox()
        self.default_copies.setRange(1, 99)
        self.default_copies.setValue(self.main.db.settings.get("copies", 1))
        print_form.addRow("Default Copies:", self.default_copies)

        layout.addWidget(print_grp)

        # Save button
        save_btn = QPushButton("💾  Save Settings")
        save_btn.setFixedWidth(180)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        # About
        about_grp = QGroupBox("About GTZ ID Studio")
        about_layout = QVBoxLayout(about_grp)

        app_title = QLabel("GTZ ID Studio  v1.0")
        app_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #1A1F36; padding: 4px 0;"
        )
        about_layout.addWidget(app_title)

        app_sub = QLabel("Staff ID Card Management & Printing Application")
        app_sub.setStyleSheet("font-size: 9.5pt; color: #6B7280; padding-bottom: 8px;")
        about_layout.addWidget(app_sub)

        about_txt = QLabel(
            "Developed by:  GT-ZINO / Xtreme Cr8\n\n"
            "Built with Python · PyQt5 · Pillow\n\n"
            "Compatible with:\n"
            "   • Fargo DTC1250e ID Card Printer\n"
            "   • HP LaserJet\n"
            "   • Any Windows-installed printer driver"
        )
        about_txt.setStyleSheet(
            "color: #374151; font-size: 9.5pt; line-height: 1.8; padding: 4px;"
        )
        about_txt.setWordWrap(True)
        about_layout.addWidget(about_txt)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #E5E7EB; max-height: 1px; margin: 4px 0;")
        about_layout.addWidget(sep)

        footer = QLabel("© 2025 GT-ZINO / Xtreme Cr8. All rights reserved.")
        footer.setStyleSheet("color: #9CA3AF; font-size: 8pt; padding: 2px;")
        about_layout.addWidget(footer)

        layout.addWidget(about_grp)

        layout.addStretch()

    def on_activate(self):
        self.db_path_edit.setText(self.main.db.current_db_path)
        self.qr_folder_edit.setText(self.main.db.settings.get("last_qr_folder", ""))

    def _change_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Database", "",
            "SQLite Database (*.db);;All Files (*)"
        )
        if path:
            ok = self.main.db.connect(path)
            if ok:
                self.db_path_edit.setText(path)
                self.main.update_db_label()
                self.main.set_status(f"Database changed: {path}")

    def _change_qr_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select QR Codes Folder")
        if folder:
            self.qr_folder_edit.setText(folder)
            self.main.renderer.set_qr_folder(folder)
            self.main.db.settings["last_qr_folder"] = folder
            self.main.db.save_settings()
            self.main.set_status(f"QR folder set: {folder}")

    def _save_settings(self):
        self.main.db.settings["card_width_mm"] = self.default_width.value()
        self.main.db.settings["card_height_mm"] = self.default_height.value()
        self.main.db.settings["copies"] = self.default_copies.value()
        self.main.db.save_settings()
        QMessageBox.information(self, "Saved", "Settings saved successfully.")
        self.main.set_status("Settings saved.")
