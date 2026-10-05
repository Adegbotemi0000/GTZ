"""
GTZ ID Studio - Print Page
Original layout restored. Fixes: printer dialog on click, dropdown contrast, local-only print.
"""
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QMessageBox, QGroupBox,
    QFormLayout, QSplitter, QTextEdit, QDialog, QListWidget,
    QListWidgetItem, QDialogButtonBox, QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# Fix 1: Dropdown contrast — white bg, dark text
COMBO_STYLE = """
    QComboBox {
        background: #FFFFFF;
        color: #1A1F36;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 9.5pt;
    }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView {
        background: #FFFFFF;
        color: #1A1F36;
        selection-background-color: #EEF2FF;
        selection-color: #1A1F36;
        border: 1px solid #D1D5DB;
    }
"""


class PrintPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.print_queue = []
        self.single_staff = None
        self._tmpl_only_config = None
        self._tmpl_only_name   = ""
        self._build_ui()
        self._refresh_printers()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Print Manager")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        sub = QLabel("Print single or batch ID cards to any installed printer.")
        sub.setStyleSheet("font-size: 9.5pt; color: #6B7280;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Main split
        splitter = QSplitter(Qt.Horizontal)

        # ── Left: print settings ──────────────────────────────────────
        settings_frame = QFrame()
        settings_frame.setStyleSheet("background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E7EB;")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(20, 16, 20, 16)
        settings_layout.setSpacing(12)

        settings_title = QLabel("Print Settings")
        settings_title.setStyleSheet("font-size: 10.5pt; font-weight: bold; color: #1A1F36;")
        settings_layout.addWidget(settings_title)

        # Printer selection
        printer_grp = QGroupBox("Printer")
        printer_form = QFormLayout(printer_grp)

        self.printer_combo = QComboBox()
        self.printer_combo.setStyleSheet(COMBO_STYLE)   # Fix 1: visible text

        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedSize(30, 28)
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self._refresh_printers)
        printer_row = QHBoxLayout()
        printer_row.addWidget(self.printer_combo, stretch=1)
        printer_row.addWidget(refresh_btn)
        printer_form.addRow("Printer:", printer_row)

        # Removed "show dialog" checkbox — dialog always shows now (Fix 2)
        settings_layout.addWidget(printer_grp)

        # Card size
        card_grp = QGroupBox("Card Size")
        card_form = QFormLayout(card_grp)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(20, 300)
        self.width_spin.setValue(54.0)    # Portrait width
        self.width_spin.setSuffix(" mm")
        self.width_spin.setDecimals(1)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(20, 300)
        self.height_spin.setValue(84.5)   # Portrait height
        self.height_spin.setSuffix(" mm")
        self.height_spin.setDecimals(1)

        wh_row = QHBoxLayout()
        wh_row.addWidget(QLabel("W:"))
        wh_row.addWidget(self.width_spin)
        wh_row.addWidget(QLabel("H:"))
        wh_row.addWidget(self.height_spin)
        card_form.addRow("Dimensions:", wh_row)

        preset_row = QHBoxLayout()
        for label, w, h in [("CR80 Portrait", 54.0, 85.6), ("CR80 Land.", 85.6, 54.0), ("A6", 105.0, 74.0)]:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryBtn")
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, _w=w, _h=h: self._set_preset(_w, _h))
            preset_row.addWidget(btn)
        card_form.addRow("Presets:", preset_row)

        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 99)
        self.copies_spin.setValue(1)
        card_form.addRow("Copies:", self.copies_spin)

        settings_layout.addWidget(card_grp)

        # Print mode
        mode_grp = QGroupBox("Print Mode")
        mode_layout = QVBoxLayout(mode_grp)
        self.single_mode   = QCheckBox("Single card (selected staff)")
        self.single_mode.setChecked(True)
        self.batch_mode    = QCheckBox("Batch (all queued records)")
        self.template_mode = QCheckBox("Template only (no staff data — same card for everyone)")
        self.template_mode.setStyleSheet("QCheckBox { color: #059669; font-weight: bold; }")

        def _sync_modes(source):
            modes = [self.single_mode, self.batch_mode, self.template_mode]
            for m in modes:
                if m is not source:
                    m.blockSignals(True)
                    m.setChecked(False)
                    m.blockSignals(False)
            source.setChecked(True)

        self.single_mode.stateChanged.connect(  lambda s: _sync_modes(self.single_mode)   if s else None)
        self.batch_mode.stateChanged.connect(   lambda s: _sync_modes(self.batch_mode)    if s else None)
        self.template_mode.stateChanged.connect(lambda s: _sync_modes(self.template_mode) if s else None)
        mode_layout.addWidget(self.single_mode)
        mode_layout.addWidget(self.batch_mode)
        mode_layout.addWidget(self.template_mode)
        settings_layout.addWidget(mode_grp)

        settings_layout.addStretch()

        self.print_btn = QPushButton("🖨  Print Now")
        self.print_btn.setFixedHeight(44)
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E5BFF; color: #FFFFFF;
                font-size: 11pt; font-weight: bold; border-radius: 8px;
            }
            QPushButton:hover { background-color: #1A47E8; }
            QPushButton:disabled { background-color: #D1D5DB; }
        """)
        self.print_btn.clicked.connect(self._start_print)
        settings_layout.addWidget(self.print_btn)

        self.cancel_btn = QPushButton("⏹  Cancel Print")
        self.cancel_btn.setObjectName("DangerBtn")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_print)
        settings_layout.addWidget(self.cancel_btn)

        splitter.addWidget(settings_frame)

        # ── Right: queue + log ────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        queue_frame = QFrame()
        queue_frame.setStyleSheet("background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E7EB;")
        queue_layout = QVBoxLayout(queue_frame)
        queue_layout.setContentsMargins(16, 12, 16, 12)

        queue_hdr = QHBoxLayout()
        queue_title = QLabel("Print Queue")
        queue_title.setStyleSheet("font-size: 10.5pt; font-weight: bold; color: #1A1F36;")
        add_all_btn = QPushButton("+ Add All Staff")
        add_all_btn.setObjectName("SecondaryBtn")
        add_all_btn.clicked.connect(self._add_all_to_queue)
        select_btn = QPushButton("☑ Select Staff...")
        select_btn.setObjectName("SecondaryBtn")
        select_btn.setToolTip("Pick specific staff members to add to the print queue")
        select_btn.clicked.connect(self._select_staff_dialog)
        clear_btn = QPushButton("Clear Queue")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(self._clear_queue)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("SecondaryBtn")
        remove_btn.clicked.connect(self._remove_from_queue)
        queue_hdr.addWidget(queue_title)
        queue_hdr.addStretch()
        queue_hdr.addWidget(add_all_btn)
        queue_hdr.addWidget(select_btn)
        queue_hdr.addWidget(remove_btn)
        queue_hdr.addWidget(clear_btn)
        queue_layout.addLayout(queue_hdr)

        self.queue_table = QTableWidget()
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.queue_table.setShowGrid(False)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.setMaximumHeight(260)
        self.queue_table.setStyleSheet("""
            QTableWidget { background: #FFFFFF; border: none; }
            QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #F3F4F6; color: #1A1F36; }
            QTableWidget::item:selected { background: #EEF2FF; color: #1A1F36; }
        """)
        cols = ["#", "Name", "Staff ID", "Department", "QR", "Status"]
        self.queue_table.setColumnCount(len(cols))
        self.queue_table.setHorizontalHeaderLabels(cols)
        hdr2 = self.queue_table.horizontalHeader()
        hdr2.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4, 5]:
            hdr2.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hdr2.setStyleSheet("""
            QHeaderView::section {
                background: #F9FAFB; color: #6B7280; font-weight: 600;
                font-size: 8pt; padding: 10px; border: none;
                border-bottom: 2px solid #E5E7EB;
            }
        """)
        queue_layout.addWidget(self.queue_table)
        right_layout.addWidget(queue_frame)

        # Progress + log
        prog_frame = QFrame()
        prog_frame.setStyleSheet("background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E7EB;")
        prog_layout = QVBoxLayout(prog_frame)
        prog_layout.setContentsMargins(16, 12, 16, 12)
        prog_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #E5E7EB; border-radius: 6px; height: 12px; background: #F9FAFB; }
            QProgressBar::chunk { background: #2E5BFF; border-radius: 6px; }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready to print.")
        self.progress_label.setStyleSheet("color: #6B7280; font-size: 8.5pt;")
        prog_layout.addWidget(self.progress_label)

        log_title = QLabel("Print Log")
        log_title.setStyleSheet("font-size: 10pt; font-weight: bold; color: #1A1F36; margin-top: 4px;")
        prog_layout.addWidget(log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(160)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px;
                font-family: 'Consolas', monospace; font-size: 8pt; color: #374151;
            }
        """)
        prog_layout.addWidget(self.log_box)

        right_layout.addWidget(prog_frame)
        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter, stretch=1)

    # ── lifecycle ─────────────────────────────────────────────────────
    def on_activate(self):
        self._refresh_printers()
        if not self.print_queue:
            self._add_all_to_queue()

    def set_single_staff(self, staff: dict):
        self.single_staff = staff
        self.single_mode.setChecked(True)
        self.print_queue = [staff]
        self._refresh_queue_table()
        self._log("Single print queued: {} ({})".format(
            staff.get('name',''), staff.get('staff_id','')))

    def set_template_only_mode(self, config=None, template_name=""):
        """Called from template page Print Template button — no staff needed."""
        self.single_staff = None
        self.print_queue  = []
        self._tmpl_only_config = config   # store the specific template config
        self._tmpl_only_name   = template_name
        self._refresh_queue_table()
        self.template_mode.setChecked(True)
        self._log("Template-only mode: «{}» — prints as-is, no staff data.".format(
            template_name or "current template"))
        self.main.set_status("Template-only print mode active. Click Print Now to print.")

    def set_batch_staff(self, staff_list: list):
        self.single_staff = None
        self.batch_mode.setChecked(True)
        self.print_queue = list(staff_list)
        self._refresh_queue_table()
        self._log("Batch queue loaded: {} staff".format(len(staff_list)))

    def _set_preset(self, w, h):
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)

    # ── printers ──────────────────────────────────────────────────────
    def _refresh_printers(self):
        self.printer_combo.clear()
        printers = self.main.print_manager.get_available_printers()
        default  = self.main.print_manager.get_default_printer()
        for p in printers:
            self.printer_combo.addItem(p)
        if default and default in printers:
            self.printer_combo.setCurrentText(default)
        if not printers:
            self.printer_combo.addItem("No printers found")

    # ── queue ─────────────────────────────────────────────────────────
    def _select_staff_dialog(self):
        all_staff = self.main.db.get_all_staff()
        if not all_staff:
            QMessageBox.information(self, "No Staff", "No staff records found in the database.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Select Staff for Print Queue")
        dlg.setMinimumSize(520, 480)
        dlg.setStyleSheet("background:#FFFFFF;")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(16, 16, 16, 16)
        vl.setSpacing(10)

        # Search bar
        search = QLineEdit()
        search.setPlaceholderText("🔍  Search by name, staff ID or department...")
        search.setStyleSheet("QLineEdit { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:6px; padding:6px 10px; font-size:9pt; }")
        vl.addWidget(search)

        # Select all / none row
        sel_row = QHBoxLayout()
        sel_all_btn  = QPushButton("☑  Select All")
        sel_none_btn = QPushButton("☐  Clear All")
        count_lbl    = QLabel("0 selected")
        count_lbl.setStyleSheet("color:#6B7280; font-size:8.5pt;")
        for b in [sel_all_btn, sel_none_btn]:
            b.setObjectName("SecondaryBtn")
            b.setFixedHeight(28)
            sel_row.addWidget(b)
        sel_row.addStretch()
        sel_row.addWidget(count_lbl)
        vl.addLayout(sel_row)

        # Staff list with checkboxes
        lst = QListWidget()
        lst.setStyleSheet("""
            QListWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:9pt; }
            QListWidget::item { padding:6px 10px; color:#1A1F36; border-bottom:1px solid #F3F4F6; }
            QListWidget::item:selected { background:#EEF2FF; }
        """)

        # Pre-tick staff already in queue
        queued_ids = {s.get("id") for s in self.print_queue}

        def _populate(filter_text=""):
            lst.clear()
            ft = filter_text.lower()
            for s in all_staff:
                name  = s.get("name","")
                sid   = s.get("staff_id","")
                dept  = s.get("department","")
                if ft and ft not in name.lower() and ft not in sid.lower() and ft not in dept.lower():
                    continue
                text = "{}   |   {}   |   {}".format(name, sid, dept)
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, s)
                item.setCheckState(Qt.Checked if s.get("id") in queued_ids else Qt.Unchecked)
                lst.addItem(item)
            _upd_count()

        def _upd_count():
            n = sum(1 for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked)
            count_lbl.setText("{} selected".format(n))

        def _sel_all():
            for i in range(lst.count()): lst.item(i).setCheckState(Qt.Checked)
            _upd_count()

        def _sel_none():
            for i in range(lst.count()): lst.item(i).setCheckState(Qt.Unchecked)
            _upd_count()

        lst.itemChanged.connect(lambda _: _upd_count())
        sel_all_btn.clicked.connect(_sel_all)
        sel_none_btn.clicked.connect(_sel_none)
        search.textChanged.connect(_populate)
        _populate()
        vl.addWidget(lst, stretch=1)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("➕  Add to Queue")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet(
            "QPushButton { background:#2E5BFF; color:#FFF; border:none; border-radius:6px; padding:6px 18px; font-weight:bold; } QPushButton:hover { background:#1A47E8; }")
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet(
            "QPushButton { background:#F3F4F6; color:#374151; border:1px solid #D1D5DB; border-radius:6px; padding:6px 14px; } QPushButton:hover { background:#E5E7EB; }")
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        vl.addWidget(btn_box)

        if dlg.exec_() != QDialog.Accepted:
            return

        # Collect checked staff, avoiding duplicates
        selected = []
        existing_ids = {s.get("id") for s in self.print_queue}
        for i in range(lst.count()):
            item = lst.item(i)
            if item.checkState() == Qt.Checked:
                s = item.data(Qt.UserRole)
                if s.get("id") not in existing_ids:
                    selected.append(s)
                    existing_ids.add(s.get("id"))

        if selected:
            self.print_queue.extend(selected)
            self._refresh_queue_table()
            self._log("Added {} staff to queue.".format(len(selected)))
            self.main.set_status("{} staff added to print queue.".format(len(selected)))
        else:
            self._log("No new staff added.")

    def _add_all_to_queue(self):
        self.print_queue = list(self.main.db.get_all_staff())
        self._refresh_queue_table()
        self._log("Added {} records to queue.".format(len(self.print_queue)))

    def _clear_queue(self):
        self.print_queue = []
        self._refresh_queue_table()
        self._log("Queue cleared.")

    def _remove_from_queue(self):
        row = self.queue_table.currentRow()
        if 0 <= row < len(self.print_queue):
            removed = self.print_queue.pop(row)
            self._refresh_queue_table()
            self._log("Removed: {}".format(removed.get('name','')))

    def _refresh_queue_table(self):
        self.queue_table.setRowCount(0)
        self.queue_table.setRowCount(len(self.print_queue))
        for i, staff in enumerate(self.print_queue):
            qr = self.main.renderer.find_qr_for_staff(staff)
            self.queue_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.queue_table.setItem(i, 1, QTableWidgetItem(staff.get('name','')))
            self.queue_table.setItem(i, 2, QTableWidgetItem(staff.get('staff_id','')))
            self.queue_table.setItem(i, 3, QTableWidgetItem(staff.get('department','')))
            qr_item = QTableWidgetItem("✅" if qr else "❌")
            qr_item.setTextAlignment(Qt.AlignCenter)
            if not qr:
                qr_item.setForeground(QColor("#EF4444"))
            self.queue_table.setItem(i, 4, qr_item)
            self.queue_table.setItem(i, 5, QTableWidgetItem("Queued"))
            self.queue_table.setRowHeight(i, 38)

    def _update_queue_row(self, row, status):
        if row < self.queue_table.rowCount():
            item = QTableWidgetItem(status)
            if "✅" in status:
                item.setForeground(QColor("#059669"))
            elif "❌" in status:
                item.setForeground(QColor("#EF4444"))
            self.queue_table.setItem(row, 5, item)

    # ── print ─────────────────────────────────────────────────────────
    def _start_print(self):
        printer = self.printer_combo.currentText()
        if not printer or printer == "No printers found":
            QMessageBox.warning(self, "No Printer",
                "No printer selected.\nClick ↺ to refresh the list.")
            return

        tmpl_info, config = self.main.get_active_template()
        template_path = tmpl_info.get("file_path") if tmpl_info else None

        if self.template_mode.isChecked():
            # Use the specific template config passed from the template page
            tmpl_config = getattr(self, "_tmpl_only_config", None) or config
            self._print_template_only(printer, template_path, tmpl_config)
        elif self.single_mode.isChecked():
            self._print_single(printer, template_path, config)
        else:
            self._print_batch(printer, template_path, config)

    def _print_template_only(self, printer, template_path, config):
        """Print the template card once with no staff data — for back-side or static cards."""
        reply = QMessageBox.question(
            self, "Print Template",
            "This will print the template card as-is with no staff data.\n"
            "How many copies do you want?",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply != QMessageBox.Ok:
            return

        self._log("Rendering template-only card...")
        try:
            # Render with empty staff — all bound fields will be blank/placeholder
            image_bytes = self.main.renderer.render_to_bytes({}, template_path, config)
        except Exception as e:
            self._log("ERROR: {}".format(e))
            QMessageBox.warning(self, "Render Error", str(e))
            return

        ok, msg = self.main.print_manager.print_single(
            image_bytes, printer,
            card_w=self.width_spin.value(),
            card_h=self.height_spin.value(),
            copies=self.copies_spin.value(),
            parent_widget=self
        )
        if ok:
            self._log("✅ Template card printed ({} copies).".format(self.copies_spin.value()))
            self.main.set_status("✅ Template card printed.")
        else:
            self._log("❌ {}".format(msg))

    def _print_single(self, printer, template_path, config):
        staff = self.single_staff
        if not staff:
            if self.print_queue:
                staff = self.print_queue[0]
            else:
                QMessageBox.warning(self, "No Staff", "No staff selected for printing.")
                return

        self._log("Rendering: {}...".format(staff.get('name','')))
        try:
            image_bytes = self.main.renderer.render_to_bytes(staff, template_path, config)
        except Exception as e:
            self._log("ERROR: {}".format(e))
            QMessageBox.warning(self, "Render Error", str(e))
            return

        # Fix 3: pass parent so dialog appears on screen, outputFileName cleared inside printer.py
        ok, msg = self.main.print_manager.print_single(
            image_bytes, printer,
            card_w=self.width_spin.value(),
            card_h=self.height_spin.value(),
            copies=self.copies_spin.value(),
            parent_widget=self
        )
        if ok:
            self._log("✅ Printed: {}".format(staff.get('name','')))
            self._update_queue_row(0, "✅ Printed")
            self.main.set_status("Printed: {}".format(staff.get('name','')))
        else:
            self._log("❌ {}".format(msg))

    def _print_batch(self, printer, template_path, config):
        if not self.print_queue:
            QMessageBox.warning(self, "Empty Queue", "No records in print queue.")
            return

        # Show printer dialog ONCE before batch starts
        from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
        qprinter = QPrinter(QPrinter.HighResolution)
        qprinter.setPrinterName(printer)
        qprinter.setOutputFormat(QPrinter.NativeFormat)
        qprinter.setOutputFileName("")
        qprinter.setFullPage(True)
        qprinter.setCopyCount(self.copies_spin.value())
        dialog = QPrintDialog(qprinter, self)
        dialog.setWindowTitle("Batch Print — {} Cards".format(len(self.print_queue)))
        if dialog.exec_() != QPrintDialog.Accepted:
            self._log("Batch print cancelled.")
            return
        qprinter.setOutputFormat(QPrinter.NativeFormat)
        qprinter.setOutputFileName("")
        printer  = qprinter.printerName()
        confirmed_copies = qprinter.copyCount()

        self._log("Starting batch: {} cards...".format(len(self.print_queue)))
        self.print_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setMaximum(len(self.print_queue))
        self.progress_bar.setValue(0)

        jobs = []
        for staff in self.print_queue:
            try:
                image_bytes = self.main.renderer.render_to_bytes(staff, template_path, config)
                jobs.append({"staff": staff, "image_bytes": image_bytes})
            except Exception as e:
                self._log("⚠ Skipping {}: {}".format(staff.get('name',''), e))

        self.batch_worker = self.main.print_manager.create_batch_worker(
            jobs, printer,
            card_w=self.width_spin.value(),
            card_h=self.height_spin.value(),
            copies=confirmed_copies
        )
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_done)
        self.batch_worker.cancelled.connect(self._on_batch_cancelled)
        self.batch_worker.start()

    def _on_batch_progress(self, current, total, name):
        self.progress_bar.setValue(current)
        self.progress_label.setText("Printing {}/{}: {}".format(current, total, name))
        self._log("[{}/{}] {}".format(current, total, name))
        self._update_queue_row(current-1, "✅ Printed")

    def _on_batch_done(self, printed, errors):
        self.print_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self._log("✅ Batch done: {} printed, {} errors.".format(printed, len(errors)))
        if errors:
            self._log("Errors: " + " | ".join(errors))
        QMessageBox.information(self, "Print Complete",
            "Printed: {} cards\nErrors: {}".format(printed, len(errors)))
        self.main.set_status("Batch print done: {} cards".format(printed))

    def _on_batch_cancelled(self):
        self.print_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self._log("Print job cancelled.")

    def _cancel_print(self):
        if hasattr(self, "batch_worker") and self.batch_worker.isRunning():
            self.batch_worker.cancel()

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append("[{}]  {}".format(ts, msg))