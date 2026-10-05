# SmartID — User Guide
## Version 1.0 | Staff ID Card Management Application

---

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [First Launch](#first-launch)
4. [Dashboard](#dashboard)
5. [Staff Database](#staff-database)
6. [Template Manager](#template-manager)
7. [QR Code Manager](#qr-code-manager)
8. [Card Preview](#card-preview)
9. [Print Manager](#print-manager)
10. [Settings](#settings)
11. [Troubleshooting](#troubleshooting)

---

## 1. Overview

SmartID is a Windows desktop application for generating, managing, and printing staff ID cards with QR codes. It replaces external tools like Assure ID and provides a complete workflow from database management to card printing.

**Key capabilities:**
- Import and manage staff database (SQLite, Excel, CSV)
- Load card templates designed in Illustrator (PNG/SVG)
- Auto-match QR codes from a folder to staff records
- Preview rendered cards before printing
- Print single or batch cards to any Windows printer (including Fargo ID card printers)

---

## 2. Installation

### Requirements
- Windows 10/11 (64-bit)
- Python 3.8 or later *(if running from source)*
- Printer driver installed (Fargo or standard Windows printer)

### Option A: Run from Source
```
1. Install Python 3.8+ from python.org
2. Open Command Prompt in the SmartID folder
3. Run: pip install -r requirements.txt
4. Run: python main.py
   — or double-click: run_smartid.bat
```

### Option B: Standalone Executable
```
1. Run: python build_exe.py
2. Find executable at: dist/SmartID/SmartID.exe
3. Copy the SmartID folder to any location
4. Double-click SmartID.exe to launch
```

---

## 3. First Launch

On first launch, SmartID will:
1. Create a local database at `C:\Users\[YourName]\.smartid\smartid.db`
2. Show the Dashboard with system status
3. Prompt you to set up your database and QR folder (via Settings or Dashboard quick actions)

**Recommended first-time setup:**
1. Go to **Staff Database** → Import or create your database
2. Go to **Templates** → Import your card template
3. Go to **QR Codes** → Set your QR folder and run a scan
4. Go to **Preview** → Verify card output
5. Go to **Print** → Print your cards

---

## 4. Dashboard

The dashboard gives you an at-a-glance view:

| Card | Description |
|------|-------------|
| Total Staff | Number of staff records in database |
| Templates | Number of saved templates |
| QR Codes Linked | Staff records with a matched QR file |
| Cards Printed | Session print count |

**System Status** panel shows:
- Database connection status
- Active template
- QR folder path
- Default printer

**Quick Actions** let you jump directly to any workflow step.

---

## 5. Staff Database

### Connecting to a Database
- **New Database** — Creates a fresh SQLite `.db` file
- **Open Database** — Connects to an existing `.db` file
- **Import Excel/CSV** — Imports staff data from spreadsheet

### Required Column Names for Import
When importing from Excel/CSV, columns should be named:

| Column | Required | Notes |
|--------|----------|-------|
| `name` | ✅ Yes | Full name |
| `staff_id` | ✅ Yes | Must be unique |
| `department` | No | Department name |
| `designation` | No | Job title |
| `email` | No | Email address |
| `phone` | No | Phone number |
| `photo_path` | No | Full path to photo file |
| `qr_filename` | No | QR file name (without extension) |

### Adding Staff Manually
Click **Add Staff** to open the staff form. Fields marked * are required.

### Editing Staff
- Double-click a row, or
- Select a row and click **Edit Selected**

### Deleting Staff
Select a row and click **Delete Selected** (confirmation required).

### Searching
Type in the search box to filter by name, staff ID, or department.

### Status Indicators
- ✅ Photo/QR column — file exists and is linked
- ❌ or — — file missing or not set

---

## 6. Template Manager

### Importing a Template
1. Click **Import Template (PNG/SVG)**
2. Browse to your card template image (PNG recommended for best quality)
3. Enter a name for the template
4. The template is saved in the database

> **Tip:** Design your template in Adobe Illustrator at 1012×638 pixels (85.6×54mm @ 300 DPI), export as PNG. Leave blank areas where the photo, QR, and text will be placed.

### Configuring Layout
After selecting a template from the list, adjust positions in the **Layout Configuration** panel on the right:

**Photo settings:**
- X, Y — top-left corner position in pixels
- W, H — width and height in pixels

**QR Code settings:**
- X, Y — top-left corner position
- W, H — width and height

**Text Field settings (for each field):**
- X, Y — text starting position
- Font Size — in pixels
- Color — click to open color picker

> **Card coordinate system:** Origin (0,0) is the top-left corner. Card is 1012 pixels wide × 638 pixels tall at 300 DPI.

### Activating a Template
Select a template and click **Use Template** to make it the active template for preview and printing.

### Saving Configuration
Click **Save Config** to save your layout adjustments to the template.

---

## 7. QR Code Manager

### Setting the QR Folder
1. Click **Browse Folder**
2. Select the folder containing your QR code image files
3. The folder is remembered between sessions

### QR File Naming
SmartID matches QR files to staff records using:
1. **Exact match** on the `qr_filename` field in the database
2. **Fallback** match on the `staff_id` field

Supported extensions: `.png`, `.jpg`, `.jpeg`, `.bmp`

**Example:** Staff ID `EMP-001`, QR filename field blank → looks for `EMP-001.png` in the folder.

### Running a Scan
Click **Scan & Match** to scan the folder and show match status for all staff:
- ✅ Found — QR file located successfully
- ❌ Missing — No matching QR file found

### Export Match Report
Click **Export Match Report** to save a CSV showing all staff and their QR match status.

---

## 8. Card Preview

### Previewing a Card
1. Select a staff member from the list on the left
2. The card is rendered and displayed automatically
3. Green ✅ next to a name = QR matched; ⚠️ = QR missing

### Preview Info Bar
Shows: Active template name • QR link status • Card dimensions

### Saving Cards as Images
- **Save as PNG** — Saves the current preview card
- **Save All Cards** — Renders and saves all staff cards to a selected folder

> Saved cards are at 300 DPI and are suitable for professional card printers.

---

## 9. Print Manager

### Selecting a Printer
- Choose from the **Printer** dropdown (auto-detected Windows printers)
- Click ↺ to refresh the printer list
- Check **Show print dialog** to configure additional print options before printing

### Card Size Settings
Default is CR80 (85.6 × 54mm) — standard credit card size. Use presets:
- **CR80** — 85.6 × 54mm (standard ID card)
- **CR79** — 84.0 × 53mm (slightly smaller)
- **A6** — 105 × 74mm

### Print Queue
- Click **Add All Staff** to load all staff into the queue
- QR match status shown (✅/❌) per record
- Remove individual records with **Remove Selected**

### Single Card Printing
1. Select **Single card** mode
2. Make sure a staff record is selected (from Preview page, or first in queue)
3. Click **Print Now**

### Batch Printing
1. Select **Batch** mode
2. Review the print queue
3. Click **Print Now** and confirm
4. Progress bar and log show printing status
5. Use **Cancel Print** to stop batch mid-way

### Print Log
All print events are logged with timestamps in the Print Log panel.

---

## 10. Settings

| Setting | Description |
|---------|-------------|
| Current Database | Path to active SQLite database |
| QR Codes Folder | Path to folder with QR image files |
| Card Width / Height | Default card dimensions (mm) |
| Default Copies | Number of copies per card |

Click **Save Settings** to persist changes.

---

## 11. Troubleshooting

### "No printers found"
- Ensure your printer driver is installed in Windows
- For Fargo printers: install the Fargo driver from HID Global
- Click ↺ (refresh) in the Print page

### QR codes not matching
- Check the `qr_filename` column in your database matches the file name (without extension)
- Or ensure files are named by Staff ID
- Run the Scan in the QR Manager to see which are missing

### Template not showing correctly
- Use PNG format exported at 300 DPI, 1012×638 px
- SVG files are supported but may render differently

### Photos not displaying
- Ensure `photo_path` in the database is an **absolute path** (e.g., `C:\Photos\john.jpg`)
- Supported formats: JPG, PNG, BMP

### App won't start
- Ensure Python 3.8+ is installed
- Run: `pip install -r requirements.txt`
- Check for error messages in the command window

### Import failing
- Ensure Excel column names match expected names (see Section 5)
- Column names are case-insensitive and spaces are converted to underscores
- Save Excel file and close it before importing

---

## Support

For support, contact your system administrator or development team.

*SmartID v1.0 — Phase 1 Release*
