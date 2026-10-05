# SmartID — Staff ID Card Management Application

A Windows desktop application for generating, managing, and printing staff ID cards with QR codes.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

Or double-click `run_smartid.bat`

## Project Structure

```
smartid/
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
├── run_smartid.bat            # Windows launcher
├── build_exe.py               # PyInstaller build script
├── USER_GUIDE.md              # Full user documentation
│
├── core/
│   ├── database.py            # SQLite + Excel/CSV manager
│   ├── renderer.py            # Card image renderer (Pillow)
│   └── printer.py             # Print manager (QPrinter)
│
├── ui/
│   ├── main_window.py         # Main window + sidebar nav
│   ├── styles.qss             # Global Qt stylesheet
│   └── pages/
│       ├── dashboard_page.py  # Overview + quick actions
│       ├── database_page.py   # Staff CRUD + import/export
│       ├── template_page.py   # Template import + layout config
│       ├── qr_page.py         # QR folder scan + matching
│       ├── preview_page.py    # Card preview + save
│       ├── print_page.py      # Single + batch printing
│       └── settings_page.py   # App settings
│
├── assets/                    # Icons, images
├── templates/                 # Saved template images
├── qr_codes/                  # Default QR folder
└── output/                    # Saved card output
```

## Features (Phase 1)

- ✅ Staff database (SQLite, Excel/CSV import/export)
- ✅ Card template management (PNG/SVG)
- ✅ QR code folder scanning & staff matching
- ✅ Card rendering with Pillow (template + photo + QR + text)
- ✅ Single card preview and save
- ✅ Batch save all cards as images
- ✅ Single + batch printing via QPrinter
- ✅ Fargo-compatible card dimensions (CR80)
- ✅ Persistent settings (database path, QR folder, print defaults)

## Technology Stack

- **Language:** Python 3.8+
- **GUI:** PyQt5
- **Database:** SQLite (primary), Excel/CSV import via pandas
- **Card Rendering:** Pillow (PIL)
- **Printing:** QPrinter (PyQt5)
