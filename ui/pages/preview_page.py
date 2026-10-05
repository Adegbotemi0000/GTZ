"""
GTSmartCardprint - Preview Page
Portrait card preview (54x84.5mm). Select specific staff for batch print.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QSplitter,
    QMessageBox, QAbstractItemView, QScrollArea, QFileDialog,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage


class RenderWorker(QThread):
    done  = pyqtSignal(bytes, dict)
    error = pyqtSignal(str)

    def __init__(self, staff, template_path, config, renderer):
        super().__init__()
        self.staff         = staff
        self.template_path = template_path
        self.config        = config
        self.renderer      = renderer

    def run(self):
        try:
            image_bytes = self.renderer.render_to_bytes(
                self.staff, self.template_path, self.config
            )
            self.done.emit(image_bytes, self.staff)
        except Exception as e:
            self.error.emit(str(e))


class PreviewPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main           = main_window
        self.current_staff  = None
        self.rendered_bytes = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("Card Preview")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1A1F36;")
        sub = QLabel("Preview ID cards before printing. Select individual staff or pick specific ones for batch.")
        sub.setStyleSheet("font-size: 9pt; color: #6B7280;")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()

        for label, slot, obj in [
            ("🔄  Refresh List",    self.on_activate,     "SecondaryBtn"),
            ("💾  Save This Card",  self._save_card,       "SecondaryBtn"),
            ("💾  Save All Cards",  self._save_all_cards,  "SecondaryBtn"),
            ("🖨  Print This Card", self._print_current,   None),
        ]:
            btn = QPushButton(label)
            btn.setMinimumWidth(130)
            if obj:
                btn.setObjectName(obj)
            btn.clicked.connect(slot)
            hdr.addWidget(btn)

        layout.addLayout(hdr)

        # ── Active template banner ────────────────────────────────────
        self.tmpl_banner = QLabel("No active template — go to Template Designer and save one.")
        self.tmpl_banner.setStyleSheet(
            "background:#FFF8E1; color:#92400E; padding:7px 14px; border-radius:6px; font-size:8.5pt;"
        )
        layout.addWidget(self.tmpl_banner)

        # ── Splitter ─────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        # Left: staff list with multi-select
        left = QFrame()
        left.setStyleSheet("background:#FFFFFF; border-radius:10px; border:1px solid #E5E7EB;")
        left.setFixedWidth(240)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(8)

        list_hdr = QHBoxLayout()
        list_title = QLabel("Staff List")
        list_title.setStyleSheet("font-size: 10.5pt; font-weight: bold; color: #1A1F36;")
        self.sel_count_lbl = QLabel("")
        self.sel_count_lbl.setStyleSheet("font-size: 8pt; color: #6B7280;")
        list_hdr.addWidget(list_title)
        list_hdr.addStretch()
        list_hdr.addWidget(self.sel_count_lbl)
        ll.addLayout(list_hdr)

        self.staff_list = QListWidget()
        self.staff_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.staff_list.setStyleSheet("""
            QListWidget { border:none; background:transparent; }
            QListWidget::item { padding:8px; border-radius:6px; border-bottom:1px solid #F3F4F6; }
            QListWidget::item:selected { background:#EEF2FF; color:#1A1F36; }
        """)
        self.staff_list.currentItemChanged.connect(self._on_staff_selected)
        self.staff_list.itemSelectionChanged.connect(self._on_selection_changed)
        ll.addWidget(self.staff_list, stretch=1)

        # Batch action buttons
        batch_row = QHBoxLayout(); batch_row.setSpacing(6)
        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setObjectName("SecondaryBtn")
        sel_all_btn.setFixedHeight(28)
        sel_all_btn.clicked.connect(self.staff_list.selectAll)

        sel_none_btn = QPushButton("Clear")
        sel_none_btn.setObjectName("SecondaryBtn")
        sel_none_btn.setFixedHeight(28)
        sel_none_btn.clicked.connect(self.staff_list.clearSelection)

        batch_print_btn = QPushButton("🖨 Print Selected")
        batch_print_btn.setFixedHeight(28)
        batch_print_btn.clicked.connect(self._print_selected)

        batch_row.addWidget(sel_all_btn)
        batch_row.addWidget(sel_none_btn)
        ll.addLayout(batch_row)
        ll.addWidget(batch_print_btn)

        splitter.addWidget(left)

        # Right: card preview area
        right = QFrame()
        right.setStyleSheet("background:#FFFFFF; border-radius:10px; border:1px solid #E5E7EB;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(10)

        prev_hdr = QHBoxLayout()
        prev_title = QLabel("Card Preview")
        prev_title.setStyleSheet("font-size: 10.5pt; font-weight: bold; color: #1A1F36;")
        self.staff_name_lbl = QLabel("")
        self.staff_name_lbl.setStyleSheet("color:#2E5BFF; font-size:10pt; font-weight:600;")
        prev_hdr.addWidget(prev_title)
        prev_hdr.addStretch()
        prev_hdr.addWidget(self.staff_name_lbl)
        rl.addLayout(prev_hdr)

        # Scroll area for the card — portrait so it needs scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("border:none; background:#E8EAED;")

        preview_container = QWidget()
        preview_container.setStyleSheet("background:#E8EAED;")
        pcl = QVBoxLayout(preview_container)
        pcl.setAlignment(Qt.AlignCenter)
        pcl.setContentsMargins(24, 24, 24, 24)

        self.preview_label = QLabel("Select a staff member\nto preview their ID card.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        # Portrait placeholder size: roughly 54:84.5 ratio → 300 wide × 470 tall
        self.preview_label.setFixedSize(300, 470)
        self.preview_label.setStyleSheet("""
            color:#9CA3AF; font-size:11pt;
            border:2px dashed #D1D5DB; border-radius:10px;
            background:#FFFFFF;
        """)
        pcl.addWidget(self.preview_label)
        scroll.setWidget(preview_container)
        rl.addWidget(scroll, stretch=1)

        # Loading / info bar
        self.loading_lbl = QLabel("⏳  Rendering...")
        self.loading_lbl.setStyleSheet("color:#2E5BFF; font-size:9.5pt; padding:2px 0;")
        self.loading_lbl.setVisible(False)
        rl.addWidget(self.loading_lbl)

        self.info_bar = QLabel("")
        self.info_bar.setStyleSheet("color:#6B7280; font-size:8.5pt; padding:2px 0;")
        rl.addWidget(self.info_bar)

        splitter.addWidget(right)
        splitter.setSizes([240, 700])
        layout.addWidget(splitter, stretch=1)

    # ── lifecycle ────────────────────────────────────────────────────
    def on_activate(self):
        self._refresh_staff_list()
        self._update_template_banner()

    def _update_template_banner(self):
        tmpl_info, _ = self.main.get_active_template()
        if tmpl_info and tmpl_info.get("name"):
            self.tmpl_banner.setText("✅  Active template: {}  — all previews use this design.".format(
                tmpl_info["name"]
            ))
            self.tmpl_banner.setStyleSheet(
                "background:#D1FAE5; color:#065F46; padding:7px 14px; border-radius:6px; font-size:8.5pt;"
            )
        else:
            self.tmpl_banner.setText("⚠  No active template — go to Template Designer and save one.")
            self.tmpl_banner.setStyleSheet(
                "background:#FFF8E1; color:#92400E; padding:7px 14px; border-radius:6px; font-size:8.5pt;"
            )

    def set_staff(self, staff: dict):
        """Called from database page — jump straight to this staff's preview."""
        self._refresh_staff_list()
        for i in range(self.staff_list.count()):
            item = self.staff_list.item(i)
            if item and item.data(Qt.UserRole).get("id") == staff.get("id"):
                self.staff_list.setCurrentItem(item)
                break

    def _refresh_staff_list(self):
        self.staff_list.clear()
        for staff in self.main.db.get_all_staff():
            has_photo = bool(staff.get("photo_path") and os.path.exists(staff.get("photo_path", "")))
            has_qr    = bool(self.main.renderer.find_qr_for_staff(staff))
            icon = "✅" if (has_photo and has_qr) else ("⚠️" if (has_photo or has_qr) else "❌")
            item = QListWidgetItem("{} {}  \n     {}".format(
                icon, staff["name"], staff.get("staff_id", "") or ""
            ))
            item.setData(Qt.UserRole, staff)
            self.staff_list.addItem(item)
        self.sel_count_lbl.setText("{} staff".format(self.staff_list.count()))

    # ── selection ────────────────────────────────────────────────────
    def _on_selection_changed(self):
        n = len(self.staff_list.selectedItems())
        self.sel_count_lbl.setText("{} selected".format(n) if n else
                                   "{} staff".format(self.staff_list.count()))

    def _on_staff_selected(self, current, previous):
        if not current:
            return
        staff = current.data(Qt.UserRole)
        self.current_staff = staff
        self.staff_name_lbl.setText(staff.get("name", ""))
        self._render_card(staff)

    # ── rendering ────────────────────────────────────────────────────
    def _render_card(self, staff: dict):
        tmpl_info, config = self.main.get_active_template()
        template_path = tmpl_info.get("file_path") if tmpl_info else None

        self.loading_lbl.setVisible(True)
        self.preview_label.setText("")
        self.preview_label.setStyleSheet(
            "border:1px solid #E5E7EB; border-radius:10px; background:#FFFFFF;"
        )

        self.worker = RenderWorker(staff, template_path, config, self.main.renderer)
        self.worker.done.connect(self._on_render_done)
        self.worker.error.connect(self._on_render_error)
        self.worker.start()

    def _on_render_done(self, image_bytes: bytes, staff: dict):
        self.rendered_bytes = image_bytes
        self.loading_lbl.setVisible(False)

        qimg  = QImage.fromData(image_bytes)
        pixmap = QPixmap.fromImage(qimg)

        # Scale to fit portrait preview area keeping aspect ratio
        preview_w = 300
        preview_h = int(preview_w * pixmap.height() / max(pixmap.width(), 1))
        self.preview_label.setFixedSize(preview_w, preview_h)

        scaled = pixmap.scaled(
            preview_w, preview_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet(
            "border:1px solid #D1D5DB; border-radius:10px; background:#FFFFFF;"
        )

        tmpl_info, _ = self.main.get_active_template()
        tmpl_name = tmpl_info.get("name", "Default") if tmpl_info else "Default layout"
        qr = self.main.renderer.find_qr_for_staff(staff)
        self.info_bar.setText(
            "Template: {}  •  QR: {}  •  Card: 54×84.5mm @ 300 DPI".format(
                tmpl_name,
                "✅ Linked" if qr else "⚠ Not found"
            )
        )
        self.main.set_status("Preview: {}".format(staff.get("name", "")))

    def _on_render_error(self, msg: str):
        self.loading_lbl.setVisible(False)
        self.preview_label.setText("Render error:\n{}".format(msg))
        self.preview_label.setStyleSheet(
            "color:#EF4444; font-size:9pt; border:2px dashed #FCA5A5; "
            "border-radius:10px; background:#FFF5F5;"
        )

    # ── print / save ─────────────────────────────────────────────────
    def _print_current(self):
        if not self.rendered_bytes or not self.current_staff:
            QMessageBox.information(self, "No Preview", "Please select a staff member first.")
            return
        print_page = self.main.pages.get(5)
        if print_page:
            print_page.set_single_staff(self.current_staff)
        self.main.navigate_to(5)

    def _print_selected(self):
        selected = [
            self.staff_list.item(i).data(Qt.UserRole)
            for i in range(self.staff_list.count())
            if self.staff_list.item(i).isSelected()
        ]
        if not selected:
            QMessageBox.information(self, "None Selected",
                                    "Select staff from the list first.\nUse Ctrl+Click or Shift+Click to pick multiple.")
            return
        print_page = self.main.pages.get(5)
        if print_page:
            print_page.set_batch_staff(selected)
        self.main.navigate_to(5)

    def _save_card(self):
        if not self.rendered_bytes or not self.current_staff:
            QMessageBox.information(self, "No Preview", "Please render a card first.")
            return
        staff = self.current_staff
        default = "{}_{}.png".format(
            staff.get("staff_id", "card"),
            staff.get("name", "").replace(" ", "_")
        )
        path, _ = QFileDialog.getSaveFileName(self, "Save Card", default, "PNG Files (*.png)")
        if path:
            with open(path, "wb") as f:
                f.write(self.rendered_bytes)
            self.main.set_status("Saved: {}".format(os.path.basename(path)))

    def _save_all_cards(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not folder:
            return
        staff_list = self.main.db.get_all_staff()
        if not staff_list:
            QMessageBox.information(self, "Empty", "No staff records found.")
            return

        tmpl_info, config = self.main.get_active_template()
        template_path = tmpl_info.get("file_path") if tmpl_info else None

        prog = QProgressDialog("Saving cards...", "Cancel", 0, len(staff_list), self)
        prog.setWindowModality(Qt.WindowModal)
        prog.show()

        saved, errors = 0, []
        for i, staff in enumerate(staff_list):
            if prog.wasCanceled():
                break
            prog.setValue(i)
            prog.setLabelText("Saving: {}".format(staff.get("name", "")))
            try:
                fname = "{}_{}.png".format(
                    staff.get("staff_id", str(staff.get("id", i))),
                    staff.get("name", "").replace(" ", "_")
                )
                self.main.renderer.save_card(
                    staff, template_path, config,
                    os.path.join(folder, fname)
                )
                saved += 1
            except Exception as e:
                errors.append("{}: {}".format(staff.get("name", ""), e))

        prog.setValue(len(staff_list))
        msg = "Saved {} card images to:\n{}".format(saved, folder)
        if errors:
            msg += "\n\n{} errors:\n{}".format(len(errors), "\n".join(errors[:5]))
        QMessageBox.information(self, "Done", msg)
        self.main.set_status("Saved {} cards to folder.".format(saved))