"""
GTZ ID Studio - Staff ID Card Management Application
Main entry point
"""
import sys
import os

# Enable DPI scaling BEFORE QApplication is created
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# High DPI support for all screen sizes
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from core.database import DatabaseManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GTZ ID Studio")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GT-ZINO/Xtreme Cr8")

    font = QFont("Segoe UI", 9)
    app.setFont(font)

    with open(os.path.join(os.path.dirname(__file__), "ui", "styles.qss"), "r") as f:
        app.setStyleSheet(f.read())

    db = DatabaseManager()
    db.init_db()

    window = MainWindow(db)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()