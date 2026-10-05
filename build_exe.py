"""
GTZ ID Studio - Build Script
Creates a standalone Windows executable using PyInstaller.

Usage:
    python build_exe.py

Requirements:
    pip install pyinstaller
"""
import os
import subprocess
import sys


def build():
    print("=" * 55)
    print("  GTZ ID Studio - Building Windows Executable")
    print("=" * 55)

    icon_path = "assets/icon.ico"
    has_icon  = os.path.exists(icon_path)
    has_assets = os.path.isdir("assets")

    if has_icon:
        print("  OK Icon found: {}".format(icon_path))
    else:
        print("  WARNING No icon found at {} - building without icon.".format(icon_path))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",             # Single .exe — no folder, runs on any Windows PC
        "--windowed",            # No console window
        "--clean",
        "--noconfirm",
        "--name", "GTZ ID Studio",

        # Collect all PyQt5 plugins (fixes DLL errors on other PCs)
        "--collect-all", "PyQt5",

        # Stylesheet
        "--add-data", "ui/styles.qss;ui",

        # Hidden imports PyInstaller misses
        "--hidden-import", "PIL._imaging",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "PIL.ImageFont",
        "--hidden-import", "PIL.ImageFilter",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "PyQt5.QtPrintSupport",
        "--hidden-import", "PyQt5.QtSvg",
        "--hidden-import", "PyQt5.QtXml",
        "--hidden-import", "sqlite3",
        "--hidden-import", "qrcode",
        "--hidden-import", "qrcode.image.pil",
    ]

    # Add assets folder if it exists
    if has_assets:
        cmd += ["--add-data", "assets;assets"]

    # Add icon if it exists
    if has_icon:
        cmd += ["--icon", icon_path]

    cmd.append("main.py")

    print("\nRunning PyInstaller...\n")
    print("NOTE: --onefile build takes longer but runs on ANY Windows PC")
    print("      Startup will take 5-10 seconds on first launch (normal)\n")

    result = subprocess.run(cmd, capture_output=False)

    print()
    if result.returncode == 0:
        print("=" * 55)
        print("  BUILD SUCCESSFUL!")
        print("  File: dist/GTZ ID Studio.exe")
        print()
        print("  To distribute:")
        print("  - Send just the single  GTZ ID Studio.exe  file")
        print("  - Works on ANY Windows PC, no Python needed")
        print("  - First launch takes ~10 seconds (extracting), normal after")
        print("=" * 55)
    else:
        print("=" * 55)
        print("  BUILD FAILED. See output above.")
        print()
        print("  Common fixes:")
        print("  - pip install pyinstaller")
        print("  - pip install -r requirements.txt")
        print("  - Run from the smartid project root folder")
        print("=" * 55)

    return result.returncode


if __name__ == "__main__":
    sys.exit(build())