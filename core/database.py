"""
GTZ ID Studio - Database Manager
Handles SQLite, Excel, and CSV operations
"""
import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class DatabaseManager:
    def __init__(self):
        self.app_dir = os.path.join(os.path.expanduser("~"), ".smartid")
        os.makedirs(self.app_dir, exist_ok=True)
        self.default_db_path = os.path.join(self.app_dir, "smartid.db")
        self.current_db_path = self.default_db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.settings_path = os.path.join(self.app_dir, "settings.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> dict:
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_db_path": None,
            "last_qr_folder": None,
            "last_template": None,
            "printer_name": None,
            "card_width_mm": 85.6,
            "card_height_mm": 54.0,
            "copies": 1,
        }

    def save_settings(self):
        with open(self.settings_path, "w") as f:
            json.dump(self.settings, f, indent=2)

    def init_db(self):
        """Initialize or connect to the default SQLite database."""
        last_db = self.settings.get("last_db_path")
        if last_db and os.path.exists(last_db):
            self.current_db_path = last_db
        self.connect(self.current_db_path)

    def connect(self, db_path: str) -> bool:
        """Connect to a SQLite database."""
        try:
            if self.connection:
                self.connection.close()
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
            self.current_db_path = db_path
            self._ensure_staff_table()
            self.settings["last_db_path"] = db_path
            self.save_settings()
            return True
        except Exception as e:
            print(f"DB connect error: {e}")
            return False

    def _ensure_staff_table(self):
        """Create the staff table if it doesn't exist, and migrate existing DBs."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                staff_id TEXT DEFAULT '',
                department TEXT,
                designation TEXT,
                photo_path TEXT,
                qr_filename TEXT,
                email TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate existing DBs — add columns if missing
        existing = [r[1] for r in cursor.execute("PRAGMA table_info(staff)").fetchall()]
        if "first_name" not in existing:
            cursor.execute("ALTER TABLE staff ADD COLUMN first_name TEXT DEFAULT ''")
        if "last_name" not in existing:
            cursor.execute("ALTER TABLE staff ADD COLUMN last_name TEXT DEFAULT ''")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def get_all_staff(self) -> List[Dict]:
        """Fetch all staff records."""
        if not self.connection:
            return []
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM staff ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_staff_by_id(self, staff_id) -> Optional[Dict]:
        """Fetch by row id (int) or staff_id (str)."""
        cursor = self.connection.cursor()
        if isinstance(staff_id, int):
            cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
        else:
            cursor.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_staff_by_row_id(self, record_id: int) -> Optional[Dict]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM staff WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_staff(self, data: Dict) -> Tuple[bool, str]:
        try:
            cursor = self.connection.cursor()
            name = data.get("name", "")
            first_name = data.get("first_name", "") or ""
            last_name  = data.get("last_name", "") or ""
            # Auto-derive first/last from full name if not supplied
            if name and not first_name and not last_name:
                parts = name.strip().split(" ", 1)
                first_name = parts[0]
                last_name  = parts[1] if len(parts) > 1 else ""
            cursor.execute("""
                INSERT INTO staff (name, first_name, last_name, staff_id, department, designation, photo_path, qr_filename, email, phone)
                VALUES (:name, :first_name, :last_name, :staff_id, :department, :designation, :photo_path, :qr_filename, :email, :phone)
            """, {
                "name": name,
                "first_name": first_name,
                "last_name": last_name,
                "staff_id": data.get("staff_id", "") or "",
                "department": data.get("department", "") or "",
                "designation": data.get("designation", "") or "",
                "photo_path": data.get("photo_path", "") or "",
                "qr_filename": data.get("qr_filename", "") or "",
                "email": data.get("email", "") or "",
                "phone": data.get("phone", "") or "",
            })
            self.connection.commit()
            return True, "Staff added successfully."
        except sqlite3.IntegrityError:
            return False, f"Staff ID '{data.get('staff_id')}' already exists."
        except Exception as e:
            return False, str(e)

    def update_staff(self, record_id: int, data: Dict) -> Tuple[bool, str]:
        """Partial update — only modifies the fields supplied in data."""
        try:
            cursor = self.connection.cursor()
            allowed = {"name", "first_name", "last_name", "staff_id", "department", "designation",
                       "photo_path", "qr_filename", "email", "phone"}
            fields = {k: v for k, v in data.items() if k in allowed}
            if not fields:
                return False, "No valid fields to update."
            set_clause = ", ".join("{k}=:{k}".format(k=k) for k in fields)
            fields["_id"] = record_id
            cursor.execute(
                "UPDATE staff SET {s} WHERE id=:_id".format(s=set_clause), fields
            )
            self.connection.commit()
            return True, "Updated successfully."
        except Exception as e:
            return False, str(e)

    def delete_staff(self, record_id: int) -> Tuple[bool, str]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM staff WHERE id = ?", (record_id,))
            self.connection.commit()
            return True, "Deleted successfully."
        except Exception as e:
            return False, str(e)

    def clear_all_staff(self) -> Tuple[bool, str]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM staff")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='staff'")
            self.connection.commit()
            return True, "All records cleared."
        except Exception as e:
            return False, str(e)

    def search_staff(self, query: str) -> List[Dict]:
        cursor = self.connection.cursor()
        like = f"%{query}%"
        cursor.execute("""
            SELECT * FROM staff WHERE name LIKE ? OR staff_id LIKE ? OR department LIKE ?
            ORDER BY name
        """, (like, like, like))
        return [dict(row) for row in cursor.fetchall()]

    def import_from_excel(self, file_path: str) -> Tuple[int, int, List[str]]:
        """Import staff from Excel/CSV. Returns (success_count, fail_count, errors)."""
        if not PANDAS_AVAILABLE:
            return 0, 0, ["pandas not installed. Run: pip install pandas openpyxl"]
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Normalize column names
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            success, fail, errors = 0, 0, []
            for _, row in df.iterrows():
                data = {
                    "name": str(row.get("name", "")),
                    "staff_id": str(row.get("staff_id", row.get("id", ""))),
                    "department": str(row.get("department", "")),
                    "designation": str(row.get("designation", row.get("title", ""))),
                    "photo_path": str(row.get("photo_path", row.get("photo", ""))),
                    "qr_filename": str(row.get("qr_filename", row.get("qr", ""))),
                    "email": str(row.get("email", "")),
                    "phone": str(row.get("phone", "")),
                }
                ok, msg = self.add_staff(data)
                if ok:
                    success += 1
                else:
                    fail += 1
                    errors.append(f"Row {_+2}: {msg}")
            return success, fail, errors
        except Exception as e:
            return 0, 0, [str(e)]

    def export_to_excel(self, file_path: str) -> Tuple[bool, str]:
        if not PANDAS_AVAILABLE:
            return False, "pandas not installed."
        try:
            staff = self.get_all_staff()
            df = pd.DataFrame(staff)
            if file_path.endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            return True, f"Exported {len(staff)} records."
        except Exception as e:
            return False, str(e)

    # --- Template Management ---
    def get_all_templates(self) -> List[Dict]:
        if not self.connection:
            return []
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def save_template(self, name: str, file_path: str, config: dict) -> Tuple[bool, str]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO templates (name, file_path, config_json)
                VALUES (?, ?, ?)
            """, (name, file_path, json.dumps(config)))
            self.connection.commit()
            return True, "Template saved."
        except Exception as e:
            return False, str(e)

    def get_template(self, name: str) -> Optional[Dict]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM templates WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            try:
                d["config"] = json.loads(d.get("config_json", "{}"))
            except Exception:
                d["config"] = {}
            return d
        return None

    def delete_template(self, name: str) -> Tuple[bool, str]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM templates WHERE name = ?", (name,))
            self.connection.commit()
            return True, "Template deleted."
        except Exception as e:
            return False, str(e)

    def close(self):
        if self.connection:
            self.connection.close()


# ─────────────────────────────────────────────────────────────────────────────
class SQLServerManager:
    """
    Connects to a Microsoft SQL Server database, reads staff data,
    and syncs it into the local SQLite database.
    Supports photos stored as BLOB or as file paths.
    """

    # Fields the app understands — used for auto-mapping
    APP_FIELDS = {
        "name":        ["name", "fullname", "full_name", "staffname", "employeename", "employee_name"],
        "first_name":  ["firstname", "first_name", "fname", "givenname"],
        "last_name":   ["lastname", "last_name", "lname", "surname", "familyname"],
        "staff_id":    ["staffid", "staff_id", "employeeid", "employee_id", "empid", "id", "badge_id", "badgeid"],
        "department":  ["department", "dept", "division", "unit"],
        "designation": ["designation", "jobtitle", "job_title", "title", "position", "role"],
        "email":       ["email", "emailaddress", "email_address", "mail"],
        "phone":       ["phone", "phonenumber", "phone_number", "mobile", "tel", "telephone"],
        "photo":       ["photo", "picture", "image", "profilephoto", "profile_photo", "staffphoto", "photo_blob"],
    }

    def __init__(self):
        self.connection   = None
        self.conn_details = {}   # server, database, username, password, table
        self.photo_mode   = "blob"   # "blob" or "path"
        self.column_map   = {}   # app_field -> actual_column_name

    def connect(self, server: str, database: str, username: str,
                password: str) -> Tuple[bool, str]:
        """Test connection to SQL Server."""
        try:
            import pyodbc
        except ImportError:
            return False, "pyodbc not installed. Run: pip install pyodbc"
        try:
            conn_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER={};DATABASE={};UID={};PWD={};TrustServerCertificate=yes;"
            ).format(server, database, username, password)
            self.connection = pyodbc.connect(conn_str, timeout=10)
            self.conn_details = {
                "server": server, "database": database,
                "username": username, "password": password,
            }
            return True, "Connected to {} / {}".format(server, database)
        except Exception as e:
            return False, str(e)

    def get_tables(self) -> List[str]:
        """Return list of user tables in the connected database."""
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def get_columns(self, table: str) -> List[str]:
        """Return column names for the given table."""
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT TOP 0 * FROM [{}]".format(table))
            return [col[0] for col in cursor.description]
        except Exception:
            return []

    def auto_map(self, columns: List[str]) -> Dict[str, str]:
        """
        Try to auto-match table columns to app fields.
        Returns {app_field: column_name} for confident matches only.
        """
        mapping = {}
        cols_lower = {c.lower().replace(" ", "").replace("_", ""): c for c in columns}
        for app_field, variants in self.APP_FIELDS.items():
            for variant in variants:
                key = variant.lower().replace("_", "")
                if key in cols_lower:
                    mapping[app_field] = cols_lower[key]
                    break
        return mapping

    def fetch_staff(self, table: str, mapping: Dict[str, str],
                    photo_mode: str = "blob") -> Tuple[List[Dict], List[str]]:
        """
        Fetch all staff from SQL Server table using the given column mapping.
        Returns (staff_list, errors).
        """
        if not self.connection:
            return [], ["Not connected to SQL Server."]
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM [{}]".format(table))
            columns = [col[0] for col in cursor.description]
            rows    = cursor.fetchall()

            staff_list, errors = [], []
            for i, row in enumerate(rows):
                row_dict = dict(zip(columns, row))
                try:
                    staff = self._map_row(row_dict, mapping, photo_mode)
                    if staff:
                        staff_list.append(staff)
                except Exception as e:
                    errors.append("Row {}: {}".format(i + 2, e))
            return staff_list, errors
        except Exception as e:
            return [], [str(e)]

    def _map_row(self, row: dict, mapping: dict, photo_mode: str) -> Optional[Dict]:
        """Convert a SQL Server row to an app staff dict."""
        # Build name
        first = str(row.get(mapping.get("first_name", ""), "") or "").strip()
        last  = str(row.get(mapping.get("last_name",  ""), "") or "").strip()
        name  = str(row.get(mapping.get("name", ""), "") or "").strip()

        if first or last:
            name = "{} {}".format(first, last).strip()
        if not name:
            return None  # skip rows with no name

        staff = {
            "name":        name,
            "first_name":  first,
            "last_name":   last,
            "staff_id":    str(row.get(mapping.get("staff_id",    ""), "") or "").strip(),
            "department":  str(row.get(mapping.get("department",  ""), "") or "").strip(),
            "designation": str(row.get(mapping.get("designation", ""), "") or "").strip(),
            "email":       str(row.get(mapping.get("email",       ""), "") or "").strip(),
            "phone":       str(row.get(mapping.get("phone",       ""), "") or "").strip(),
            "photo_path":  "",
            "photo_blob":  None,
        }

        # Handle photo
        photo_col = mapping.get("photo", "")
        if photo_col and photo_col in row:
            raw = row[photo_col]
            if photo_mode == "blob" and raw and isinstance(raw, (bytes, bytearray)):
                staff["photo_blob"] = bytes(raw)
            elif photo_mode == "path" and raw:
                staff["photo_path"] = str(raw).strip()

        return staff

    def sync_to_local(self, db_manager, table: str, mapping: Dict[str, str],
                      photo_mode: str = "blob",
                      photos_dir: str = "") -> Tuple[int, int, int, List[str]]:
        """
        Smart sync — add new, update changed, skip unchanged.
        Returns (added, updated, skipped, errors).
        """
        staff_list, errors = self.fetch_staff(table, mapping, photo_mode)
        if not staff_list:
            return 0, 0, 0, errors or ["No records fetched from SQL Server."]

        added, updated, skipped = 0, 0, 0

        for staff in staff_list:
            # Save photo blob to file if needed
            if staff.get("photo_blob") and photos_dir:
                try:
                    os.makedirs(photos_dir, exist_ok=True)
                    safe = (staff.get("staff_id") or staff["name"]).replace(" ", "_").replace("/", "_")
                    photo_path = os.path.join(photos_dir, "{}.jpg".format(safe))
                    with open(photo_path, "wb") as f:
                        f.write(staff["photo_blob"])
                    staff["photo_path"] = photo_path
                except Exception as e:
                    errors.append("Photo save error for {}: {}".format(staff["name"], e))

            staff.pop("photo_blob", None)

            # Check if staff already exists by staff_id
            existing = None
            if staff.get("staff_id"):
                existing = db_manager.get_staff_by_id(staff["staff_id"])

            if not existing:
                ok, msg = db_manager.add_staff(staff)
                if ok:
                    added += 1
                else:
                    errors.append("Add {}: {}".format(staff["name"], msg))
            else:
                # Check if anything changed
                changed = any(
                    str(existing.get(k, "") or "") != str(staff.get(k, "") or "")
                    for k in ("name", "first_name", "last_name", "department",
                              "designation", "email", "phone")
                )
                if changed:
                    ok, msg = db_manager.update_staff(existing["id"], staff)
                    if ok:
                        updated += 1
                    else:
                        errors.append("Update {}: {}".format(staff["name"], msg))
                else:
                    skipped += 1

        return added, updated, skipped, errors

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None