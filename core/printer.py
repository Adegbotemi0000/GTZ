"""
GTZ ID Studio - Print Manager
Local-only printing. Always shows dialog. Blocks file/OneDrive output.
"""
from typing import List, Dict, Tuple
from PyQt5.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog
from PyQt5.QtGui import QPainter, QImage, QPixmap
from PyQt5.QtCore import QSizeF, QRectF, QThread, pyqtSignal, QObject


def _do_print(printer, image_bytes, card_w, card_h):
    """
    Core print function — must always be called from the MAIN thread.
    Draws the card at exact physical size on whatever paper is loaded.
    For card printers (Fargo etc.) the card IS the paper so it fills edge to edge.
    For laser/inkjet it centres the card on the sheet.
    """
    qimg = QImage()
    qimg.loadFromData(image_bytes)
    # Convert to RGB32 explicitly — ensures Fargo driver sees full colour, not greyscale
    if qimg.format() != QImage.Format_RGB32:
        qimg = qimg.convertToFormat(QImage.Format_RGB32)
    pixmap = QPixmap.fromImage(qimg)

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Could not start print job — painter failed to begin.")

    dpi          = printer.resolution()
    card_w_dots  = int(card_w / 25.4 * dpi)
    card_h_dots  = int(card_h / 25.4 * dpi)
    page         = printer.pageRect()

    # If card fits exactly (card printer) draw edge to edge, otherwise centre
    x = max(0, (page.width()  - card_w_dots) // 2)
    y = max(0, (page.height() - card_h_dots) // 2)

    target = QRectF(x, y, card_w_dots, card_h_dots)
    painter.drawPixmap(target.toRect(), pixmap)
    painter.end()


class RenderWorker(QThread):
    """
    Renders card images in background to keep UI responsive.
    Does NOT touch QPrinter or QPainter — printing is done on main thread.
    """
    progress  = pyqtSignal(int, int, str)   # current, total, name
    finished  = pyqtSignal(list)             # list of {staff, image_bytes}
    error     = pyqtSignal(str)

    def __init__(self, jobs_data, renderer, template_path, config):
        super().__init__()
        self.jobs_data     = jobs_data       # list of staff dicts
        self.renderer      = renderer
        self.template_path = template_path
        self.config        = config
        self._cancel       = False

    def cancel(self): self._cancel = True

    def run(self):
        rendered = []
        total = len(self.jobs_data)
        for i, staff in enumerate(self.jobs_data):
            if self._cancel:
                return
            name = staff.get("name", "Record {}".format(i + 1))
            self.progress.emit(i + 1, total, name)
            try:
                image_bytes = self.renderer.render_to_bytes(
                    staff, self.template_path, self.config
                )
                rendered.append({"staff": staff, "image_bytes": image_bytes})
            except Exception as e:
                self.error.emit("Skipping {}: {}".format(name, e))
        self.finished.emit(rendered)


class PrintManager:
    def get_available_printers(self) -> List[str]:
        return [i.printerName() for i in QPrinterInfo.availablePrinters()]

    def get_default_printer(self) -> str:
        info = QPrinterInfo.defaultPrinter()
        return info.printerName() if info else ""

    def print_single(
        self,
        image_bytes: bytes,
        printer_name: str,
        card_w: float = 54.0,
        card_h: float = 84.5,
        copies: int = 1,
        parent_widget=None,
    ) -> Tuple[bool, str]:
        """Show dialog and print one card — must be called from main thread."""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPrinterName(printer_name)
            printer.setOutputFormat(QPrinter.NativeFormat)
            printer.setOutputFileName("")
            printer.setFullPage(True)
            printer.setCopyCount(copies)

            dialog = QPrintDialog(printer, parent_widget)
            dialog.setWindowTitle("Print ID Card — Select Printer")
            if dialog.exec_() != QPrintDialog.Accepted:
                return False, "Print cancelled."

            # Re-enforce native output after dialog
            printer.setOutputFormat(QPrinter.NativeFormat)
            printer.setOutputFileName("")

            _do_print(printer, image_bytes, card_w, card_h)
            return True, "Printed successfully."
        except Exception as e:
            return False, str(e)

    def print_batch_jobs(
        self,
        rendered_jobs: list,
        printer: QPrinter,
        card_w: float = 54.0,
        card_h: float = 84.5,
    ) -> Tuple[int, list]:
        """
        Print pre-rendered jobs using an already-confirmed QPrinter.
        Must be called from the MAIN thread.
        Returns (printed_count, errors).
        """
        printed, errors = 0, []
        for job in rendered_jobs:
            name = job.get("staff", {}).get("name", "Unknown")
            try:
                _do_print(printer, job["image_bytes"], card_w, card_h)
                printed += 1
                # New page for next card
                if job != rendered_jobs[-1]:
                    printer.newPage()
            except Exception as e:
                errors.append("{}: {}".format(name, e))
        return printed, errors

    def create_render_worker(self, jobs_data, renderer, template_path, config):
        """Create a background worker that renders card images only (no printing)."""
        return RenderWorker(jobs_data, renderer, template_path, config)