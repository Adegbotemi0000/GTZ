"""
GTSmartCardprint - QR Code Bank
Primary job: show ALL QR files in the selected folder as a gallery.
Match status is shown as extra info only — not a requirement.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QScrollArea, QFrame,
    QGridLayout, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor

IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")


class QRTile(QFrame):
    """Single QR card — thumbnail + filename + optional match badge."""
    def __init__(self, filepath, match_name=None, parent=None):
        super().__init__(parent)
        self.filepath  = filepath
        self.setFixedSize(155, 195)
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 2px solid #2E5BFF;
                background: #F5F7FF;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(4)

        # Thumbnail
        thumb = QLabel()
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setFixedSize(128, 128)
        thumb.setStyleSheet("border: none; background: transparent;")
        pix = QPixmap(filepath)
        if not pix.isNull():
            thumb.setPixmap(
                pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            thumb.setText("📱")
            thumb.setStyleSheet("font-size: 32pt; border: none; color: #9CA3AF;")
        lay.addWidget(thumb, alignment=Qt.AlignCenter)

        # Filename (no extension)
        fname = os.path.splitext(os.path.basename(filepath))[0]
        name_lbl = QLabel(fname)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setFixedWidth(139)
        name_lbl.setStyleSheet("font-size: 7.5pt; color: #374151; border: none;")
        lay.addWidget(name_lbl)

        # Match badge (optional)
        if match_name:
            badge = QLabel("✅ " + match_name)
            badge.setAlignment(Qt.AlignCenter)
            badge.setWordWrap(True)
            badge.setFixedWidth(139)
            badge.setStyleSheet(
                "font-size: 7pt; color: #065F46; background: #D1FAE5; "
                "border-radius: 4px; padding: 2px 4px; border: none;"
            )
            lay.addWidget(badge)
        else:
            badge = QLabel("○ Unmatched")
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                "font-size: 7pt; color: #6B7280; background: #F3F4F6; "
                "border-radius: 4px; padding: 2px 4px; border: none;"
            )
            lay.addWidget(badge)


class QRPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._tiles = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("QR Code Bank")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        sub = QLabel(
            "All QR files in your folder are shown here. "
            "Match badges appear automatically if a staff name matches — "
            "but every QR is loaded regardless."
        )
        sub.setStyleSheet("font-size: 9pt; color: #6B7280;")
        sub.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()
        layout.addLayout(hdr)

        # ── Folder bar ───────────────────────────────────────────────
        folder_frame = QFrame()
        folder_frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border-radius:10px; border:1px solid #E5E7EB; }"
        )
        fl = QHBoxLayout(folder_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(8)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("No folder selected — click Browse...")
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setStyleSheet("""
            QLineEdit {
                background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px;
                padding:8px 12px; font-size:9pt; color:#374151;
            }
        """)
        saved = self.main.db.settings.get("last_qr_folder", "")
        if saved:
            self.folder_edit.setText(saved)

        fl.addWidget(self.folder_edit, stretch=1)

        for label, slot, obj in [
            ("📂  Browse",  self._browse_folder, "SecondaryBtn"),
            ("🔄  Reload",  self._load_folder,   "SecondaryBtn"),
            ("🗑  Clear",   self._clear,          "DangerBtn"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(90)
            btn.clicked.connect(slot)
            fl.addWidget(btn)

        layout.addWidget(folder_frame)

        # ── Stats + filter row ───────────────────────────────────────
        bar = QHBoxLayout()

        self.total_lbl = QLabel("0 QR codes in folder")
        self.total_lbl.setStyleSheet(
            "background:#EEF2FF; color:#3730A3; padding:6px 14px; "
            "border-radius:6px; font-size:9pt; font-weight:bold;"
        )
        self.matched_lbl = QLabel("0 matched to staff")
        self.matched_lbl.setStyleSheet(
            "background:#D1FAE5; color:#065F46; padding:6px 14px; "
            "border-radius:6px; font-size:9pt; font-weight:bold;"
        )
        self.unmatched_lbl = QLabel("0 unmatched")
        self.unmatched_lbl.setStyleSheet(
            "background:#F3F4F6; color:#6B7280; padding:6px 14px; "
            "border-radius:6px; font-size:9pt; font-weight:bold;"
        )
        bar.addWidget(self.total_lbl)
        bar.addWidget(self.matched_lbl)
        bar.addWidget(self.unmatched_lbl)
        bar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Filter by filename...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background:#FFFFFF; border:1px solid #E5E7EB; border-radius:20px;
                padding:6px 16px; font-size:9pt; min-width:220px;
            }
            QLineEdit:focus { border-color:#2E5BFF; }
        """)
        self.search_box.textChanged.connect(self._filter)
        bar.addWidget(self.search_box)
        layout.addLayout(bar)

        # ── Gallery ──────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border:1px solid #E5E7EB; border-radius:10px; background:#F9FAFB; }"
        )

        self.gallery_widget = QWidget()
        self.gallery_widget.setStyleSheet("background:#F9FAFB;")
        self.grid = QGridLayout(self.gallery_widget)
        self.grid.setContentsMargins(16, 16, 16, 16)
        self.grid.setSpacing(12)

        self.empty_lbl = QLabel(
            "No QR codes loaded.\n\nClick  📂 Browse  to open your QR folder."
        )
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet(
            "color:#9CA3AF; font-size:12pt; padding:80px;"
        )
        self.grid.addWidget(self.empty_lbl, 0, 0)

        self.scroll.setWidget(self.gallery_widget)
        layout.addWidget(self.scroll, stretch=1)

        # Auto-load happens in on_activate, not here

    def _safe_status(self, msg):
        try:
            self._safe_status(msg)
        except Exception:
            pass
    def on_activate(self):
        saved = self.main.db.settings.get("last_qr_folder", "")
        if saved and saved != self.folder_edit.text():
            self.folder_edit.setText(saved)
        if self.folder_edit.text():
            self._load_folder()

    # ── slots ────────────────────────────────────────────────────────
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select QR Codes Folder")
        if folder:
            self.folder_edit.setText(folder)
            self.main.renderer.set_qr_folder(folder)
            self.main.db.settings["last_qr_folder"] = folder
            self.main.db.save_settings()
            self._load_folder()

    def _load_folder(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "No Folder", "Please select a QR codes folder first.")
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Not Found", "Folder does not exist:\n{}".format(folder))
            return

        # ── Collect ALL image files ───────────────────────────────
        files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMG_EXTS
        ])

        if not files:
            self._clear_grid()
            self.empty_lbl.setText(
                "No image files found in this folder.\n"
                "Supported: PNG, JPG, JPEG, BMP, TIFF"
            )
            self.grid.addWidget(self.empty_lbl, 0, 0)
            self._update_stats(0, 0)
            self._safe_status("QR folder loaded — 0 files found.")
            return

        # ── Build match map from staff DB (best-effort, no errors) ──
        match_map = {}   # filepath -> staff name
        try:
            staff_list = self.main.db.get_all_staff()
            if staff_list:
                self.main.renderer.set_qr_folder(folder)
                for staff in staff_list:
                    qr_path = self.main.renderer.find_qr_for_staff(staff)
                    if qr_path and os.path.normpath(qr_path) not in match_map:
                        match_map[os.path.normpath(qr_path)] = staff.get("name", "")
        except Exception:
            pass   # DB empty or error — just skip matching silently

        # ── Render gallery ────────────────────────────────────────
        self._clear_grid()
        self._tiles = []

        COLS = 5
        matched = 0
        for i, fpath in enumerate(files):
            norm = os.path.normpath(fpath)
            staff_name = match_map.get(norm, None)
            if staff_name:
                matched += 1
            tile = QRTile(fpath, match_name=staff_name)
            row, col = divmod(i, COLS)
            self.grid.addWidget(tile, row, col)
            self._tiles.append((tile, os.path.splitext(os.path.basename(fpath))[0].lower()))

        self._update_stats(len(files), matched)
        self._safe_status(
            "QR Bank: {} files loaded, {} matched to staff".format(len(files), matched)
        )

    def _clear(self):
        self._clear_grid()
        self._tiles = []
        self.search_box.clear()
        self._update_stats(0, 0)
        self._safe_status("QR bank cleared.")

    def _filter(self, text):
        query = text.lower().strip()
        for tile, fname_lower in self._tiles:
            tile.setVisible(not query or query in fname_lower)

    # ── helpers ──────────────────────────────────────────────────────
    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _update_stats(self, total, matched):
        self.total_lbl.setText("{} QR codes in folder".format(total))
        self.matched_lbl.setText("{} matched to staff".format(matched))
        self.unmatched_lbl.setText("{} unmatched".format(total - matched))