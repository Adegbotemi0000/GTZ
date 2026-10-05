"""
GTZ ID Studio - Database Page
Tabs: Staff Records | Staff Photos
"""
import os
import shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QFileDialog, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QAbstractItemView, QMenu, QAction,
    QComboBox, QScrollArea, QGridLayout, QTabWidget,
    QListWidget, QListWidgetItem, QSizePolicy, QProgressBar,
    QSplitter
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QIcon

IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")

COMBO_STYLE = """
    QComboBox {
        background: #FFFFFF; color: #1A1F36;
        border: 1px solid #D1D5DB; border-radius: 5px;
        padding: 4px 8px; min-width: 140px;
    }
    QComboBox QAbstractItemView {
        background: #FFFFFF; color: #1A1F36;
        selection-background-color: #EEF2FF;
    }
    QComboBox::drop-down { border: none; }
"""


# ────────────────────────────────────────────────────────────────────
class StaffDialog(QDialog):
    def __init__(self, parent=None, data: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Add Staff" if not data else "Edit Staff")
        self.setModal(True)
        self.setFixedWidth(440)
        self.data = data or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Staff Information")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #1A1F36;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.fields = {}
        field_defs = [
            ("name",        "Full Name"),
            ("first_name",  "First Name (optional)"),
            ("last_name",   "Last Name (optional)"),
            ("staff_id",    "Staff ID"),
            ("department",  "Department"),
            ("designation", "Designation / Title"),
            ("email",       "Email"),
            ("phone",       "Phone"),
            ("qr_filename", "QR Filename (optional)"),
        ]

        for key, label in field_defs:
            edit = QLineEdit()
            edit.setText(str(self.data.get(key, "") or ""))
            edit.setPlaceholderText("Enter {}".format(label))
            self.fields[key] = edit
            form.addRow("{}:".format(label), edit)

        layout.addLayout(form)

        photo_row = QHBoxLayout()
        self.photo_edit = QLineEdit()
        self.photo_edit.setPlaceholderText("Path to photo file...")
        self.photo_edit.setText(str(self.data.get("photo_path", "") or ""))
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryBtn")
        browse_btn.clicked.connect(self._browse_photo)
        photo_row.addWidget(self.photo_edit, stretch=1)
        photo_row.addWidget(browse_btn)
        form.addRow("Photo Path:", photo_row)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )
        if path:
            self.photo_edit.setText(path)

    def get_data(self) -> dict:
        d = {k: v.text().strip() for k, v in self.fields.items()}
        d["photo_path"] = self.photo_edit.text().strip()
        return d


# ────────────────────────────────────────────────────────────────────
class ColumnMapDialog(QDialog):
    APP_FIELDS = [
        ("first_name",  "First Name (if separate)"),
        ("last_name",   "Last Name (if separate)"),
        ("name",        "Full Name (if combined)"),
        ("staff_id",    "Staff ID"),
        ("department",  "Department"),
        ("designation", "Designation / Title"),
        ("email",       "Email"),
        ("phone",       "Phone"),
        ("photo_path",  "Photo Path"),
        ("qr_filename", "QR Filename"),
    ]

    def __init__(self, columns: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Map Your Columns")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.columns = columns
        self.combos = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Map your file columns to the app fields")
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #1A1F36;")
        layout.addWidget(title)

        hint = QLabel(
            "Only Name is required. Everything else is optional.\n"
            "If your sheet has First Name and Last Name separately, map both — they'll be merged."
        )
        hint.setStyleSheet("color: #6B7280; font-size: 8.5pt; background: #F9FAFB; border-radius: 6px; padding: 8px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        options = ["-- Skip --"] + self.columns

        for key, label in self.APP_FIELDS:
            combo = QComboBox()
            combo.setStyleSheet(COMBO_STYLE)
            combo.addItems(options)
            for i, col in enumerate(self.columns):
                col_clean = col.lower().strip().replace(" ", "_").replace("-", "_")
                key_clean = key.lower()
                if col_clean == key_clean or key_clean in col_clean or col_clean in key_clean:
                    combo.setCurrentIndex(i + 1)
                    break
            self.combos[key] = combo
            lbl = QLabel("{}:".format(label))
            lbl.setStyleSheet("color: #374151; font-size: 9pt; font-weight: 600;")
            form.addRow(lbl, combo)
            if key == "last_name":
                sep = QFrame(); sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("background: #E5E7EB; max-height: 1px; margin: 4px 0;")
                form.addRow(sep)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.setStyleSheet("QPushButton { min-width: 80px; }")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_mapping(self) -> dict:
        return {k: (c.currentText() if c.currentIndex() > 0 else None)
                for k, c in self.combos.items()}


# ────────────────────────────────────────────────────────────────────
class PhotoMatchRow(QWidget):
    """One row in the Staff Photos tab — shows thumbnail, name, match status, action."""
    assign_clicked = pyqtSignal(dict)   # staff dict
    clear_clicked  = pyqtSignal(dict)

    THUMB = 52

    def __init__(self, staff: dict, parent=None):
        super().__init__(parent)
        self.staff = staff
        self._build()
        self.refresh()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        self.thumb = QLabel()
        self.thumb.setFixedSize(self.THUMB, self.THUMB)
        self.thumb.setStyleSheet("border: 1px solid #E5E7EB; border-radius: 4px; background: #F3F4F6;")
        self.thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.thumb)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.name_lbl = QLabel()
        self.name_lbl.setStyleSheet("font-size: 9.5pt; font-weight: bold; color: #1A1F36;")
        self.id_lbl = QLabel()
        self.id_lbl.setStyleSheet("font-size: 8pt; color: #6B7280;")
        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet("font-size: 8pt;")
        info.addWidget(self.name_lbl)
        info.addWidget(self.id_lbl)
        info.addWidget(self.status_lbl)
        layout.addLayout(info, stretch=1)

        self.assign_btn = QPushButton("📂 Assign Photo")
        self.assign_btn.setObjectName("SecondaryBtn")
        self.assign_btn.setFixedHeight(28)
        self.assign_btn.clicked.connect(lambda: self.assign_clicked.emit(self.staff))
        layout.addWidget(self.assign_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setObjectName("DangerBtn")
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.clicked.connect(lambda: self.clear_clicked.emit(self.staff))
        layout.addWidget(self.clear_btn)

        self.setStyleSheet("QWidget { border-bottom: 1px solid #F3F4F6; }")

    def refresh(self):
        s = self.staff
        self.name_lbl.setText(s.get("name", ""))
        self.id_lbl.setText("ID: {}".format(s.get("staff_id", "—") or "—"))
        photo = s.get("photo_path", "")
        if photo and os.path.exists(photo):
            pix = QPixmap(photo).scaled(
                self.THUMB, self.THUMB,
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.thumb.setPixmap(pix)
            self.status_lbl.setText("✅ Photo assigned")
            self.status_lbl.setStyleSheet("font-size: 8pt; color: #059669;")
        else:
            self.thumb.setText("👤")
            self.thumb.setStyleSheet("border: 1px solid #E5E7EB; border-radius:4px; background:#F3F4F6; font-size:22pt;")
            self.status_lbl.setText("⚠ No photo")
            self.status_lbl.setStyleSheet("font-size: 8pt; color: #EF4444;")

    def update_staff(self, staff):
        self.staff = staff
        self.refresh()


# ────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────
class SQLServerDialog(QDialog):
    """Dialog to connect to SQL Server, pick table, map columns and sync."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main    = main_window
        self.sql_mgr = None
        self.mapping = {}
        self.table   = ""
        self.setWindowTitle("Connect to SQL Server")
        self.setModal(True)
        self.setMinimumWidth(540)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("SQL Server Connection")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #1A1F36;")
        layout.addWidget(title)

        hint = QLabel("Enter your SQL Server details. The app will read staff data and sync it locally.")
        hint.setStyleSheet("color: #6B7280; font-size: 8.5pt;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Connection form
        form = QFormLayout(); form.setSpacing(10)
        self.server_edit = QLineEdit(); self.server_edit.setPlaceholderText("e.g. 192.168.1.10 or server\\instance")
        self.db_edit     = QLineEdit(); self.db_edit.setPlaceholderText("Database name")
        self.user_edit   = QLineEdit(); self.user_edit.setPlaceholderText("Username")
        self.pass_edit   = QLineEdit(); self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)

        for label, widget in [
            ("Server:", self.server_edit),
            ("Database:", self.db_edit),
            ("Username:", self.user_edit),
            ("Password:", self.pass_edit),
        ]:
            lbl = QLabel(label); lbl.setStyleSheet("font-weight: 600; color: #374151;")
            form.addRow(lbl, widget)
        layout.addLayout(form)

        # Connect button
        self.connect_btn = QPushButton("🔌  Connect")
        self.connect_btn.setFixedHeight(36)
        self.connect_btn.clicked.connect(self._do_connect)
        layout.addWidget(self.connect_btn)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 8.5pt; padding: 4px;")
        self.status_lbl.setWordWrap(True)
        layout.addWidget(self.status_lbl)

        # Table selection (hidden until connected)
        self.table_grp = QWidget(); self.table_grp.setVisible(False)
        tg_layout = QVBoxLayout(self.table_grp); tg_layout.setContentsMargins(0,0,0,0); tg_layout.setSpacing(8)

        tbl_row = QHBoxLayout()
        tbl_lbl = QLabel("Table:"); tbl_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        self.table_combo = QComboBox(); self.table_combo.setMinimumWidth(200)
        self.table_combo.setStyleSheet(COMBO_STYLE)
        load_btn = QPushButton("Load Columns")
        load_btn.setObjectName("SecondaryBtn")
        load_btn.clicked.connect(self._load_columns)
        tbl_row.addWidget(tbl_lbl); tbl_row.addWidget(self.table_combo, stretch=1); tbl_row.addWidget(load_btn)
        tg_layout.addLayout(tbl_row)

        # Photo mode
        ph_row = QHBoxLayout()
        ph_lbl = QLabel("Photo stored as:"); ph_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        self.photo_combo = QComboBox()
        self.photo_combo.addItems(["BLOB (binary in database)", "File Path (path stored in database)"])
        self.photo_combo.setStyleSheet(COMBO_STYLE)
        ph_row.addWidget(ph_lbl); ph_row.addWidget(self.photo_combo, stretch=1)
        tg_layout.addLayout(ph_row)

        layout.addWidget(self.table_grp)

        # Mapping area (hidden until columns loaded)
        self.map_grp = QWidget(); self.map_grp.setVisible(False)
        mg_layout = QVBoxLayout(self.map_grp); mg_layout.setContentsMargins(0,0,0,0); mg_layout.setSpacing(8)

        map_title = QLabel("Column Mapping"); map_title.setStyleSheet("font-weight: bold; color: #1A1F36;")
        map_hint  = QLabel("Auto-matched where possible. Adjust if needed.")
        map_hint.setStyleSheet("color: #6B7280; font-size: 8pt;")
        mg_layout.addWidget(map_title); mg_layout.addWidget(map_hint)

        self.map_form  = QFormLayout(); self.map_form.setSpacing(8)
        self.map_combos = {}
        for app_field, variants in [
            ("name",        "Full Name"),
            ("first_name",  "First Name"),
            ("last_name",   "Last Name"),
            ("staff_id",    "Staff ID"),
            ("department",  "Department"),
            ("designation", "Designation"),
            ("email",       "Email"),
            ("phone",       "Phone"),
            ("photo",       "Photo"),
        ]:
            combo = QComboBox(); combo.setStyleSheet(COMBO_STYLE)
            self.map_combos[app_field] = combo
            lbl = QLabel("{}:".format(variants)); lbl.setStyleSheet("color: #374151; font-size: 9pt;")
            self.map_form.addRow(lbl, combo)
        mg_layout.addLayout(self.map_form)
        layout.addWidget(self.map_grp)

        # Buttons
        btn_row = QHBoxLayout()
        self.sync_btn = QPushButton("⬇  Import / Sync Now")
        self.sync_btn.setVisible(False)
        self.sync_btn.clicked.connect(self._do_sync)
        btn_row.addWidget(self.sync_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close"); close_btn.setObjectName("SecondaryBtn")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _do_connect(self):
        # Check pyodbc is installed
        try:
            import pyodbc
        except ImportError:
            QMessageBox.critical(self, "Missing Library",
                "pyodbc is not installed.\n\n"
                "Run this in your terminal:\n"
                "    pip install pyodbc\n\n"
                "Then restart the app.")
            return

        # Check ODBC Driver 17 is installed
        try:
            import pyodbc
            drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
            if not drivers:
                reply = QMessageBox.critical(self, "ODBC Driver Missing",
                    "Microsoft ODBC Driver for SQL Server is not installed on this PC.\n\n"
                    "Please install it from the extras folder included with this app:\n"
                    "    extras\\msodbcsql.msi\n\n"
                    "Double-click that file to install, then restart the app and try again.",
                    QMessageBox.Ok)
                return
        except Exception:
            pass

        from core.database import SQLServerManager
        server = self.server_edit.text().strip()
        db     = self.db_edit.text().strip()
        user   = self.user_edit.text().strip()
        pwd    = self.pass_edit.text()
        if not all([server, db, user]):
            self.status_lbl.setText("❌ Server, Database and Username are required.")
            self.status_lbl.setStyleSheet("color: #DC2626; font-size: 8.5pt;")
            return
        self.connect_btn.setText("Connecting...")
        self.connect_btn.setEnabled(False)
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        mgr = SQLServerManager()
        ok, msg = mgr.connect(server, db, user, pwd)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("🔌  Connect")
        if ok:
            self.sql_mgr = mgr
            self.status_lbl.setText("✅ " + msg)
            self.status_lbl.setStyleSheet("color: #16A34A; font-size: 8.5pt;")
            tables = mgr.get_tables()
            self.table_combo.clear()
            self.table_combo.addItems(tables)
            self.table_grp.setVisible(True)
        else:
            self.status_lbl.setText("❌ " + msg)
            self.status_lbl.setStyleSheet("color: #DC2626; font-size: 8.5pt;")

    def _load_columns(self):
        if not self.sql_mgr:
            return
        table   = self.table_combo.currentText()
        columns = self.sql_mgr.get_columns(table)
        if not columns:
            self.status_lbl.setText("❌ Could not read columns from table: {}".format(table))
            return
        self.table = table
        auto       = self.sql_mgr.auto_map(columns)
        options    = ["-- Skip --"] + columns
        for app_field, combo in self.map_combos.items():
            combo.clear(); combo.addItems(options)
            matched = auto.get(app_field)
            if matched and matched in columns:
                combo.setCurrentIndex(columns.index(matched) + 1)
        self.map_grp.setVisible(True)
        self.sync_btn.setVisible(True)
        confident = len(auto)
        self.status_lbl.setText("✅ {} columns auto-matched. Review and adjust if needed.".format(confident))
        self.status_lbl.setStyleSheet("color: #16A34A; font-size: 8.5pt;")

    def _do_sync(self):
        if not self.sql_mgr or not self.table:
            return
        mapping = {}
        for app_field, combo in self.map_combos.items():
            val = combo.currentText()
            if val and val != "-- Skip --":
                mapping[app_field] = val
        if not mapping.get("name") and not (mapping.get("first_name") or mapping.get("last_name")):
            QMessageBox.warning(self, "Mapping Error", "Please map at least Full Name or First/Last Name.")
            return
        photo_mode = "blob" if self.photo_combo.currentIndex() == 0 else "path"
        photos_dir = ""
        if photo_mode == "blob":
            db_dir     = os.path.dirname(self.main.db.current_db_path)
            photos_dir = os.path.join(db_dir, "staff_photos")
        self.sync_btn.setText("Syncing...")
        self.sync_btn.setEnabled(False)
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        try:
            added, updated, skipped, errors = self.sql_mgr.sync_to_local(
                self.main.db, self.table, mapping, photo_mode, photos_dir
            )
            msg = "Sync complete!\nAdded: {}  |  Updated: {}  |  Unchanged: {}".format(added, updated, skipped)
            if errors:
                msg += "\n\nWarnings:\n" + "\n".join(errors[:5])
            QMessageBox.information(self, "Sync Complete", msg)
            self.status_lbl.setText("✅ Sync done — Added: {}, Updated: {}, Skipped: {}".format(added, updated, skipped))
            # Save connection details for future sync
            self.main.db.settings["sqlserver"] = {
                "server": self.server_edit.text().strip(),
                "database": self.db_edit.text().strip(),
                "username": self.user_edit.text().strip(),
                "password": self.pass_edit.text(),
                "table": self.table,
                "mapping": mapping,
                "photo_mode": photo_mode,
            }
            self.main.db.save_settings()
        except Exception as e:
            QMessageBox.warning(self, "Sync Error", str(e))
        finally:
            self.sync_btn.setEnabled(True)
            self.sync_btn.setText("⬇  Import / Sync Now")

class DatabasePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._photo_rows = {}   # staff_id -> PhotoMatchRow
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # ── Page header ──────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Staff Database")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        sub = QLabel("Manage staff records, import data and assign staff photos.")
        sub.setStyleSheet("font-size: 9.5pt; color: #6B7280;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()

        db_row = QHBoxLayout(); db_row.setSpacing(8)
        for label, slot in [
            ("✚ New DB",         self._new_database),
            ("📂 Open DB",       self._open_database),
            ("⬆ Import Excel/CSV", self._import_file),
            ("⬇ Export",         self._export_file),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryBtn")
            btn.clicked.connect(slot)
            db_row.addWidget(btn)

        add_btn = QPushButton("✚  Add Staff")
        add_btn.clicked.connect(self._add_staff)
        db_row.addWidget(add_btn)

        # SQL Server buttons
        sql_btn = QPushButton("🔌 Connect SQL Server")
        sql_btn.setObjectName("SecondaryBtn")
        sql_btn.setToolTip("Connect to Microsoft SQL Server and import/sync staff data")
        sql_btn.clicked.connect(self._open_sql_server)
        db_row.addWidget(sql_btn)

        self.sync_btn = QPushButton("🔄 Sync SQL Server")
        self.sync_btn.setObjectName("SecondaryBtn")
        self.sync_btn.setToolTip("Re-sync staff data from last connected SQL Server")
        self.sync_btn.setVisible(False)
        self.sync_btn.clicked.connect(self._quick_sync)
        db_row.addWidget(self.sync_btn)

        hdr.addLayout(db_row)
        layout.addLayout(hdr)

        self.db_info_label = QLabel()
        self.db_info_label.setStyleSheet(
            "background: #EEF2FF; color: #3730A3; padding: 6px 12px; border-radius: 6px; font-size: 8.5pt;"
        )
        layout.addWidget(self.db_info_label)

        # ── Tabs ─────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E5E7EB; border-radius: 8px; background: #FFFFFF; }
            QTabBar::tab { background: #F3F4F6; color: #6B7280; padding: 8px 22px; border-radius: 6px 6px 0 0; font-size: 9.5pt; margin-right: 2px; }
            QTabBar::tab:selected { background: #FFFFFF; color: #1A1F36; font-weight: bold; border-bottom: 2px solid #2E5BFF; }
        """)
        layout.addWidget(self.tabs, stretch=1)

        self.tabs.addTab(self._build_records_tab(), "👥  Staff Records")
        self.tabs.addTab(self._build_photos_tab(),  "📷  Staff Photos")

    # ── Tab 1: Staff Records ─────────────────────────────────────────
    def _build_records_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Search
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search by name, ID, or department...")
        self.search_box.setStyleSheet("""
            QLineEdit { background:#FFF; border:1px solid #E5E7EB; border-radius:20px;
                        padding:6px 16px; font-size:9.5pt; min-width:300px; }
            QLineEdit:focus { border-color:#2E5BFF; }
        """)
        self.search_box.textChanged.connect(self._on_search)
        self.count_label = QLabel("0 records")
        self.count_label.setStyleSheet("color:#6B7280; font-size:9pt;")
        search_row.addWidget(self.search_box)
        search_row.addStretch()
        search_row.addWidget(self.count_label)
        layout.addLayout(search_row)

        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.doubleClicked.connect(self._edit_selected)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget { background:#FFF; border:none; border-radius:8px; }
            QTableWidget::item { padding:8px 10px; border-bottom:1px solid #F3F4F6; }
            QTableWidget::item:selected { background:#EEF2FF; color:#1A1F36; }
        """)
        columns = ["Name", "Staff ID", "Department", "Designation", "Email", "Phone", "Photo", "QR"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        hdr2 = self.table.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(columns)):
            hdr2.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hdr2.setStyleSheet("""
            QHeaderView::section { background:#F9FAFB; color:#6B7280; font-weight:600;
                font-size:8pt; padding:10px; border:none; border-bottom:2px solid #E5E7EB; }
        """)
        layout.addWidget(self.table, stretch=1)

        # Action bar
        act = QHBoxLayout()
        for label, obj, slot in [
            ("✏ Edit",          "SecondaryBtn", self._edit_selected),
            ("🗑 Delete",        "DangerBtn",    self._delete_selected),
            ("⚠ Clear All",     "DangerBtn",    self._clear_all_records),
        ]:
            btn = QPushButton(label); btn.setObjectName(obj); btn.clicked.connect(slot)
            act.addWidget(btn)
        act.addStretch()
        prev_btn = QPushButton("👁 Preview Card")
        prev_btn.clicked.connect(self._preview_selected)
        act.addWidget(prev_btn)
        layout.addLayout(act)
        return w

    # ── Tab 2: Staff Photos ──────────────────────────────────────────
    def _build_photos_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Toolbar
        tb = QHBoxLayout(); tb.setSpacing(8)

        info = QLabel("Assign photos to staff members individually or import a whole folder at once.")
        info.setStyleSheet("color:#6B7280; font-size:9pt;")
        info.setWordWrap(True)
        tb.addWidget(info, stretch=1)

        folder_btn = QPushButton("📁 Import from Folder")
        folder_btn.setObjectName("SecondaryBtn")
        folder_btn.setToolTip("Select a folder — the app will match image filenames to staff names automatically")
        folder_btn.clicked.connect(self._import_photos_folder)

        save_folder_btn = QPushButton("💾 Set Photos Folder")
        save_folder_btn.setObjectName("SecondaryBtn")
        save_folder_btn.setToolTip("Choose where imported photos will be saved")
        save_folder_btn.clicked.connect(self._set_photos_folder)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self._refresh_photos_tab)

        for btn in [save_folder_btn, folder_btn, refresh_btn]:
            tb.addWidget(btn)
        layout.addLayout(tb)

        # Photos folder indicator
        self.photos_folder_label = QLabel()
        self.photos_folder_label.setStyleSheet(
            "background:#F0F9FF; color:#0369A1; padding:6px 12px; border-radius:6px; font-size:8.5pt;"
        )
        layout.addWidget(self.photos_folder_label)

        # Progress bar (hidden normally)
        self.match_progress = QProgressBar()
        self.match_progress.setVisible(False)
        self.match_progress.setStyleSheet("QProgressBar { border:1px solid #E5E7EB; border-radius:4px; height:8px; } QProgressBar::chunk { background:#2E5BFF; border-radius:4px; }")
        layout.addWidget(self.match_progress)

        # Stats row
        self.photo_stats = QLabel()
        self.photo_stats.setStyleSheet("color:#374151; font-size:9pt; padding:4px 0;")
        layout.addWidget(self.photo_stats)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:1px solid #E5E7EB; border-radius:8px; background:#FFFFFF;")
        self._photo_list_widget = QWidget()
        self._photo_list_layout = QVBoxLayout(self._photo_list_widget)
        self._photo_list_layout.setContentsMargins(0, 0, 0, 0)
        self._photo_list_layout.setSpacing(0)
        self._photo_list_layout.addStretch()
        scroll.setWidget(self._photo_list_widget)
        layout.addWidget(scroll, stretch=1)

        return w

    # ── Photos tab logic ─────────────────────────────────────────────
    def _get_photos_folder(self):
        folder = self.main.settings.value("photos_folder", "") if hasattr(self.main, "settings") else ""
        if not folder:
            default = os.path.join(os.path.dirname(self.main.db.current_db_path), "staff_photos")
            return default
        return folder

    def _set_photos_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Photos Storage Folder")
        if folder:
            if hasattr(self.main, "settings"):
                self.main.settings.setValue("photos_folder", folder)
            self._refresh_photos_folder_label()
            self.main.set_status("Photos folder: {}".format(folder))

    def _refresh_photos_folder_label(self):
        folder = self._get_photos_folder()
        self.photos_folder_label.setText("📁  Photos stored in:  {}".format(folder))

    def _refresh_photos_tab(self):
        self._refresh_photos_folder_label()
        # Clear existing rows
        while self._photo_list_layout.count() > 1:
            item = self._photo_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._photo_rows.clear()

        staff_list = self.main.db.get_all_staff()
        has_photo  = sum(1 for s in staff_list if s.get("photo_path") and os.path.exists(s.get("photo_path","")))
        total      = len(staff_list)
        self.photo_stats.setText(
            "Total: {}  ·  With photo: {}  ·  Missing: {}".format(total, has_photo, total - has_photo)
        )

        for staff in staff_list:
            row = PhotoMatchRow(staff)
            row.assign_clicked.connect(self._assign_single_photo)
            row.clear_clicked.connect(self._clear_photo)
            self._photo_list_layout.insertWidget(self._photo_list_layout.count() - 1, row)
            self._photo_rows[staff.get("id")] = row

    def _update_stats(self):
        """Refresh just the stats bar without rebuilding all rows."""
        staff_list = self.main.db.get_all_staff()
        has_photo  = sum(1 for s in staff_list if s.get("photo_path") and os.path.exists(s.get("photo_path","")))
        total      = len(staff_list)
        self.photo_stats.setText(
            "Total: {}  ·  With photo: {}  ·  Missing: {}".format(total, has_photo, total - has_photo)
        )

    def _assign_single_photo(self, staff: dict):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo for {}".format(staff.get("name","")),
            "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )
        if not path:
            return
        saved = self._copy_photo_to_folder(path, staff)
        self.main.db.update_staff(staff["id"], {"photo_path": saved})
        # Fetch the fresh record from DB by row id and update the widget directly
        fresh = self.main.db.get_staff_by_row_id(staff["id"]) or staff
        fresh["photo_path"] = saved  # ensure it's set even if DB fetch lags
        if staff["id"] in self._photo_rows:
            self._photo_rows[staff["id"]].update_staff(fresh)
        else:
            self._refresh_photos_tab()
        self._update_stats()
        self.main.set_status("Photo assigned: {}".format(staff.get("name","")))

    def _clear_photo(self, staff: dict):
        self.main.db.update_staff(staff["id"], {"photo_path": ""})
        self._refresh_photos_tab()

    def _copy_photo_to_folder(self, src_path: str, staff: dict) -> str:
        """Copy photo to photos folder, rename to staff name."""
        folder = self._get_photos_folder()
        os.makedirs(folder, exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower()
        safe_name = (staff.get("name","unknown") or "unknown").replace(" ", "_").replace("/","_")
        dest = os.path.join(folder, "{}{}".format(safe_name, ext))
        try:
            shutil.copy2(src_path, dest)
            return dest
        except Exception:
            return src_path   # fallback: use original

    def _import_photos_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Staff Photos")
        if not folder:
            return

        staff_list = self.main.db.get_all_staff()
        if not staff_list:
            QMessageBox.information(self, "No Staff", "No staff records found. Please import staff data first.")
            return

        # Collect all image files
        img_files = [
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMG_EXTS
        ]
        if not img_files:
            QMessageBox.warning(self, "No Images", "No image files found in that folder.")
            return

        self.match_progress.setVisible(True)
        self.match_progress.setMaximum(len(img_files))
        self.match_progress.setValue(0)

        matched, skipped = 0, 0
        photos_folder = self._get_photos_folder()
        os.makedirs(photos_folder, exist_ok=True)

        for i, fname in enumerate(img_files):
            self.match_progress.setValue(i + 1)
            name_no_ext = os.path.splitext(fname)[0].lower().strip()
            norm        = name_no_ext.replace("_", " ").replace("-", " ")

            # Find matching staff
            best = None
            for s in staff_list:
                sname      = (s.get("name","") or "").lower().strip()
                sid        = (s.get("staff_id","") or "").lower().strip()
                sname_norm = sname.replace("_"," ").replace("-"," ")

                if name_no_ext in (sname, sid, sname.replace(" ","_")):
                    best = s; break
                if norm == sname_norm:
                    best = s; break
                # Partial: both first+last present
                parts = sname.split()
                if len(parts) >= 2:
                    if parts[0] in norm and parts[-1] in norm:
                        best = s; break

            if best:
                src = os.path.join(folder, fname)
                dest = self._copy_photo_to_folder(src, best)
                self.main.db.update_staff(best["id"], {"photo_path": dest})
                best["photo_path"] = dest
                # Update the row widget immediately if visible
                if best["id"] in self._photo_rows:
                    self._photo_rows[best["id"]].update_staff(best)
                matched += 1
            else:
                skipped += 1

        self.match_progress.setVisible(False)
        self._refresh_photos_tab()
        self._refresh_table()

        QMessageBox.information(
            self, "Import Complete",
            "✅  Matched & assigned: {}\n"
            "⚠  No match found:     {}\n\n"
            "Tip: Name image files as 'Firstname_Lastname.jpg' for best matching.".format(matched, skipped)
        )
        self.main.set_status("Photos imported: {} matched, {} skipped".format(matched, skipped))

    # ── Records tab logic ────────────────────────────────────────────
    def on_activate(self):
        self._refresh_table()
        self._refresh_photos_tab()
        self.db_info_label.setText("📁  Connected: {}".format(self.main.db.current_db_path))
        # Show sync button if previously connected to SQL Server
        if self.main.db.settings.get("sqlserver"):
            self.sync_btn.setVisible(True)

    def _open_sql_server(self):
        """Open SQL Server connection dialog."""
        dlg = SQLServerDialog(self.main, self)
        dlg.exec_()
        self._refresh_table()
        self._refresh_photos_tab()
        if self.main.db.settings.get("sqlserver"):
            self.sync_btn.setVisible(True)

    def _quick_sync(self):
        """Re-sync from last connected SQL Server without re-entering credentials."""
        cfg = self.main.db.settings.get("sqlserver")
        if not cfg:
            QMessageBox.warning(self, "No SQL Server", "No SQL Server connection saved. Use Connect SQL Server first.")
            return
        from core.database import SQLServerManager
        mgr = SQLServerManager()
        self.sync_btn.setText("Connecting...")
        self.sync_btn.setEnabled(False)
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        ok, msg = mgr.connect(cfg["server"], cfg["database"], cfg["username"], cfg["password"])
        if not ok:
            QMessageBox.warning(self, "Connection Failed", msg)
            self.sync_btn.setEnabled(True)
            self.sync_btn.setText("🔄 Sync SQL Server")
            return
        self.sync_btn.setText("Syncing...")
        QApplication.processEvents()
        try:
            db_dir     = os.path.dirname(self.main.db.current_db_path)
            photos_dir = os.path.join(db_dir, "staff_photos") if cfg.get("photo_mode") == "blob" else ""
            added, updated, skipped, errors = mgr.sync_to_local(
                self.main.db, cfg["table"], cfg["mapping"],
                cfg.get("photo_mode", "blob"), photos_dir
            )
            msg_text = "Sync complete!\nAdded: {}  |  Updated: {}  |  Unchanged: {}".format(added, updated, skipped)
            if errors:
                msg_text += "\n\nWarnings:\n" + "\n".join(errors[:5])
            QMessageBox.information(self, "Sync Complete", msg_text)
            self._refresh_table()
            self._refresh_photos_tab()
            self.main.set_status("SQL Sync: +{} added, {} updated".format(added, updated))
        except Exception as e:
            QMessageBox.warning(self, "Sync Error", str(e))
        finally:
            mgr.disconnect()
            self.sync_btn.setEnabled(True)
            self.sync_btn.setText("🔄 Sync SQL Server")

    def _refresh_table(self, records=None):
        if records is None:
            records = self.main.db.get_all_staff()
        self.table.setRowCount(0)
        self.table.setRowCount(len(records))

        for row, staff in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(staff.get("name","") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(staff.get("staff_id","") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(staff.get("department","") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(staff.get("designation","") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(staff.get("email","") or ""))
            self.table.setItem(row, 5, QTableWidgetItem(staff.get("phone","") or ""))

            photo_path = staff.get("photo_path","")
            photo_item = QTableWidgetItem("✅" if photo_path and os.path.exists(photo_path) else "—")
            photo_item.setTextAlignment(Qt.AlignCenter)
            if not (photo_path and os.path.exists(photo_path)):
                photo_item.setForeground(QColor("#EF4444"))
            self.table.setItem(row, 6, photo_item)

            qr = self.main.renderer.find_qr_for_staff(staff)
            qr_item = QTableWidgetItem("✅" if qr else "—")
            qr_item.setTextAlignment(Qt.AlignCenter)
            if not qr:
                qr_item.setForeground(QColor("#EF4444"))
            self.table.setItem(row, 7, qr_item)

            self.table.item(row, 0).setData(Qt.UserRole, staff.get("id"))

        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, 42)

        self.count_label.setText("{} record{}".format(len(records), "s" if len(records) != 1 else ""))
        self.db_info_label.setText("📁  Connected: {}".format(self.main.db.current_db_path))

    def _on_search(self, text):
        records = self.main.db.search_staff(text.strip()) if text.strip() else self.main.db.get_all_staff()
        self._refresh_table(records)

    def _get_selected_staff(self):
        row = self.table.currentRow()
        if row < 0: return None
        item = self.table.item(row, 0)
        if not item: return None
        rid = item.data(Qt.UserRole)
        for s in self.main.db.get_all_staff():
            if s.get("id") == rid: return s
        return None

    def _add_staff(self):
        dlg = StaffDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data.get("name"):
                QMessageBox.warning(self, "Validation", "Full Name is required.")
                return
            ok, msg = self.main.db.add_staff(data)
            if ok:
                self.main.set_status("Staff added: {}".format(data.get("name")))
                self._refresh_table()
                self._refresh_photos_tab()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _edit_selected(self):
        staff = self._get_selected_staff()
        if not staff:
            QMessageBox.information(self, "Select", "Please select a staff record.")
            return
        dlg = StaffDialog(self, staff)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data.get("name"):
                QMessageBox.warning(self, "Validation", "Full Name is required.")
                return
            ok, msg = self.main.db.update_staff(staff["id"], data)
            if ok:
                self._refresh_table()
                self._refresh_photos_tab()
                self.main.set_status("Updated: {}".format(staff["name"]))
            else:
                QMessageBox.warning(self, "Error", msg)

    def _delete_selected(self):
        staff = self._get_selected_staff()
        if not staff: return
        if QMessageBox.question(
            self, "Delete", "Delete '{}' ({})?\nThis cannot be undone.".format(
                staff["name"], staff["staff_id"]),
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            ok, msg = self.main.db.delete_staff(staff["id"])
            if ok:
                self._refresh_table(); self._refresh_photos_tab()
                self.main.set_status("Deleted: {}".format(staff["name"]))
            else:
                QMessageBox.warning(self, "Error", msg)

    def _clear_all_records(self):
        count = len(self.main.db.get_all_staff())
        if count == 0:
            QMessageBox.information(self, "Empty", "No records to delete.")
            return
        if QMessageBox.warning(
            self, "Clear All Records",
            "Permanently delete all {} staff records?\nThis cannot be undone.".format(count),
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            ok, msg = self.main.db.clear_all_staff()
            if ok:
                self._refresh_table(); self._refresh_photos_tab()
                self.main.set_status("All records cleared.")
            else:
                QMessageBox.warning(self, "Error", msg)

    def _preview_selected(self):
        staff = self._get_selected_staff()
        if not staff:
            QMessageBox.information(self, "Select", "Please select a staff record to preview.")
            return
        preview_page = self.main.pages.get(4)
        if preview_page:
            preview_page.set_staff(staff)
        self.main.navigate_to(4)

    def _context_menu(self, pos):
        menu = QMenu(self)
        for label, slot in [("✏ Edit", self._edit_selected), ("👁 Preview Card", self._preview_selected)]:
            act = QAction(label, self); act.triggered.connect(slot); menu.addAction(act)
        menu.addSeparator()
        del_act = QAction("🗑 Delete", self); del_act.triggered.connect(self._delete_selected)
        menu.addAction(del_act)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _new_database(self):
        path, _ = QFileDialog.getSaveFileName(self, "Create New Database", "", "SQLite Database (*.db)")
        if path:
            if self.main.db.connect(path):
                self.main.update_db_label(); self._refresh_table()
                self.main.set_status("New database: {}".format(path))

    def _open_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Database", "", "SQLite Database (*.db);;All Files (*)")
        if path:
            if self.main.db.connect(path):
                self.main.update_db_label(); self._refresh_table()
                self.main.set_status("Opened: {}".format(path))

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Staff Data", "", "Excel/CSV Files (*.xlsx *.xls *.csv)")
        if not path: return
        try:
            import pandas as pd
            df = pd.read_csv(path, dtype=str) if path.endswith(".csv") else pd.read_excel(path, dtype=str)
            df = df.fillna("")
            columns = list(df.columns)
            if not columns:
                QMessageBox.warning(self, "Empty File", "The file has no columns."); return
            map_dlg = ColumnMapDialog(columns, self)
            if map_dlg.exec_() != QDialog.Accepted: return
            mapping = map_dlg.get_mapping()
            success, fail, errors = 0, 0, []
            for idx, row in df.iterrows():
                data = {}
                for app_field, file_col in mapping.items():
                    if app_field in ("first_name","last_name"): continue
                    data[app_field] = str(row.get(file_col,"")).strip() if file_col else ""
                first = str(row.get(mapping.get("first_name") or "","")).strip()
                last  = str(row.get(mapping.get("last_name") or "","")).strip()
                if first or last:
                    data["first_name"] = first
                    data["last_name"]  = last
                    data["name"] = "{} {}".format(first, last).strip()
                elif not data.get("name"):
                    data["name"] = ""
                if not data.get("name"):
                    fail += 1; errors.append("Row {}: No name — skipped.".format(idx+2)); continue
                ok, msg = self.main.db.add_staff(data)
                if ok: success += 1
                else: fail += 1; errors.append("Row {}: {}".format(idx+2, msg))
            msg_text = "Imported {} records.".format(success)
            if fail: msg_text += "\n{} skipped.".format(fail)
            if errors: msg_text += "\n\n" + "\n".join(errors[:10])
            QMessageBox.information(self, "Import Complete", msg_text)
            self._refresh_table(); self._refresh_photos_tab()
            self.main.set_status("Imported {} records".format(success))
        except ImportError:
            QMessageBox.warning(self, "Missing Library", "Run: pip install pandas openpyxl")
        except Exception as e:
            QMessageBox.warning(self, "Import Error", str(e))

    def _export_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Staff Data", "staff_export.xlsx",
                                               "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if path:
            ok, msg = self.main.db.export_to_excel(path)
            if ok: QMessageBox.information(self, "Export Complete", msg); self.main.set_status("Exported to {}".format(os.path.basename(path)))
            else: QMessageBox.warning(self, "Export Failed", msg)