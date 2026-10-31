"""STEP 1-2 - MySQL (XAMPP) connection, database initialization and all data access.
Tables follow lost_found_db.sql: users, lost_items, found_items, claims."""
import hashlib
import json
import os
import secrets
import shutil
import uuid
from datetime import date

try:
    import mysql.connector as mysql_c
except ImportError:  # reported as a friendly DBError on first use
    mysql_c = None

from config import DB_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOST_STATUSES = ("Pending", "Found", "Not Found", "Claimed")
FOUND_STATUSES = ("Pending", "Available", "Claim Pending", "Claimed")
# kind -> (table, id column, date column, location column, report-number prefix)
T = {"Lost": ("lost_items", "lost_item_id", "date_lost", "location_lost", "LST"),
     "Found": ("found_items", "found_item_id", "date_found", "location_found", "FND")}

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users(
        user_id INT(11) NOT NULL AUTO_INCREMENT, full_name VARCHAR(100) NOT NULL, student_id VARCHAR(50) NOT NULL,
        username VARCHAR(50) NOT NULL, password VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL,
        PRIMARY KEY (user_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS lost_items(
        lost_item_id INT(11) NOT NULL AUTO_INCREMENT, user_id INT(11) NOT NULL, item_name VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL, description TEXT NOT NULL, date_lost DATE NOT NULL,
        location_lost VARCHAR(150) NOT NULL, contact_info VARCHAR(150) NOT NULL, photo_path VARCHAR(255) NOT NULL,
        status VARCHAR(30) NOT NULL, PRIMARY KEY (lost_item_id), KEY user_id (user_id),
        CONSTRAINT lost_items_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS found_items(
        found_item_id INT(11) NOT NULL AUTO_INCREMENT, user_id INT(11) NOT NULL, item_name VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL, description TEXT NOT NULL, date_found DATE NOT NULL,
        location_found VARCHAR(150) NOT NULL, contact_info VARCHAR(150) NOT NULL, photo_path VARCHAR(255) NOT NULL,
        status VARCHAR(30) NOT NULL, PRIMARY KEY (found_item_id), KEY user_id (user_id),
        CONSTRAINT found_items_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS claims(
        claim_id INT(11) NOT NULL AUTO_INCREMENT, found_item_id INT(11) NOT NULL, user_id INT(11) NOT NULL,
        claim_date DATE NOT NULL, proof TEXT NOT NULL, status VARCHAR(30) NOT NULL, PRIMARY KEY (claim_id),
        KEY user_id (user_id), KEY found_item_id (found_item_id),
        CONSTRAINT claims_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT claims_ibfk_2 FOREIGN KEY (found_item_id) REFERENCES found_items(found_item_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


class DBError(Exception):
    """Any database / business-rule problem, with a message that is safe to show the user."""


# ---------------------------------------------------------------- connection
def _connect(with_db=True):
    if mysql_c is None:
        raise DBError("The 'mysql-connector-python' package is not installed.\nRun:  pip install mysql-connector-python")
    cfg = dict(DB_CONFIG)
    if not with_db:
        cfg.pop("database")
    try:
        return mysql_c.connect(connection_timeout=5, **cfg)
    except mysql_c.Error as e:
        raise DBError("Cannot connect to MySQL.\nOpen the XAMPP Control Panel and click Start next to MySQL "
                      f"(then check config.py).\n\nDetails: {e}")


def _run(sql, params=(), fetch=None):
    conn = None
    try:
        conn = _connect()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        result = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else cur.lastrowid
        conn.commit()
        return result
    except mysql_c.IntegrityError:
        raise DBError("That record already exists or contains invalid data.")
    except mysql_c.Error as e:
        raise DBError(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def init_db():
    """Create the database + tables if missing and seed the default admin (admin / Admin@123)."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = None
    try:
        conn = _connect(with_db=False)
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4")
        cur.execute(f"USE `{DB_CONFIG['database']}`")
        for stmt in SCHEMA:
            cur.execute(stmt)
        conn.commit()
    except mysql_c.Error as e:
        raise DBError(f"Could not initialize the database: {e}")
    finally:
        if conn:
            conn.close()
    if not _run("SELECT user_id FROM users WHERE role='admin' LIMIT 1", fetch="one"):
        _insert_user("Administrator", "ADMIN-001", "admin", "Admin@123", "admin")


# ---------------------------------------------------------------- helpers
def _hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 120_000).hex()}"


def _verify(password, stored):
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash(password, salt), stored)


def store_file(src):
    """Copy an uploaded image into uploads/ and return its relative path (saved in the DB)."""
    try:
        name = uuid.uuid4().hex + os.path.splitext(src)[1].lower()
        shutil.copy2(src, os.path.join(UPLOAD_DIR, name))
        return f"uploads/{name}"
    except OSError as e:
        raise DBError(f"Could not save the file: {e}")


def abs_path(rel):
    path = os.path.join(BASE_DIR, rel) if rel else None
    return path if path and os.path.isfile(path) else None


def _norm(r, kind):
    table, idc, dc, lc, prefix = T[kind]
    d = r[dc]
    iso = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
    return {"id": r[idc], "kind": kind, "user_id": r["user_id"], "name": r["item_name"], "category": r["category"],
            "description": r["description"], "date": iso, "location": r[lc], "contact": r["contact_info"],
            "photo": r["photo_path"], "photo_abs": abs_path(r["photo_path"]), "status": r["status"],
            "reporter": r.get("reporter", ""), "report_no": f"{prefix}-{iso[:4]}-{r[idc]:05d}"}


# ---------------------------------------------------------------- users
def _insert_user(full_name, student_id, username, password, role):
    return _run("INSERT INTO users(full_name,student_id,username,password,role) VALUES(%s,%s,%s,%s,%s)",
                (full_name, student_id, username, _hash(password), role))


def register_user(full_name, student_id, username, password):
    if _run("SELECT user_id FROM users WHERE username=%s", (username,), "one"):
        raise DBError("That username is already taken.")
    if _run("SELECT user_id FROM users WHERE student_id=%s", (student_id,), "one"):
        raise DBError("An account with this Student ID already exists.")
    return _insert_user(full_name, student_id, username, password, "student")


def authenticate(username, password):
    u = _run("SELECT * FROM users WHERE username=%s", (username,), "one")
    return u if u and _verify(password, u["password"]) else None


# ---------------------------------------------------------------- reports
def create_report(user_id, kind, name, category, description, date_iso, location, contact, photo_src=None):
    table, _, dc, lc, _ = T[kind]
    photo = store_file(photo_src) if photo_src else ""
    return _run(f"INSERT INTO {table}(user_id,item_name,category,description,{dc},{lc},contact_info,photo_path,status) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'Pending')",
                (user_id, name, category, description, date_iso, location, contact, photo))


def get_item(kind, item_id):
    table, idc = T[kind][:2]
    r = _run(f"SELECT x.*, u.full_name AS reporter FROM {table} x JOIN users u ON u.user_id=x.user_id WHERE x.{idc}=%s",
             (item_id,), "one")
    return _norm(r, kind) if r else None


def list_items(user_id=None, kind=None):
    out = []
    for k in ("Lost", "Found"):
        if kind and kind != k:
            continue
        table, idc = T[k][:2]
        rows = _run(f"SELECT x.*, u.full_name AS reporter FROM {table} x JOIN users u ON u.user_id=x.user_id "
                    f"WHERE (%s IS NULL OR x.user_id=%s) ORDER BY x.{idc} DESC", (user_id, user_id), "all")
        out += [_norm(r, k) for r in rows]
    return sorted(out, key=lambda i: (i["date"], i["id"]), reverse=True)


def candidates_for(item):
    """Items of the opposite type that could match (used by AI image matching)."""
    if item["kind"] == "Lost":
        return [i for i in list_items(kind="Found") if i["status"] in ("Pending", "Available")]
    return [i for i in list_items(kind="Lost") if i["status"] in ("Pending", "Not Found", "Found")]


def set_status(kind, item_id, status):
    if status not in (LOST_STATUSES if kind == "Lost" else FOUND_STATUSES):
        raise DBError(f"'{status}' is not a valid status for a {kind.lower()} report.")
    table, idc = T[kind][:2]
    _run(f"UPDATE {table} SET status=%s WHERE {idc}=%s", (status, item_id))


# ---------------------------------------------------------------- claims
def submit_claim(found_id, user_id, lost_id, proof_src):
    found = get_item("Found", found_id)
    if not found or found["status"] != "Available":
        raise DBError("This item is not available for claiming yet.")
    lost = get_item("Lost", lost_id)
    if not lost or lost["user_id"] != user_id:
        raise DBError("Please claim using one of your own lost reports.")
    proof = json.dumps({"file": store_file(proof_src), "lost_item_id": lost_id})
    _run("INSERT INTO claims(found_item_id,user_id,claim_date,proof,status) VALUES(%s,%s,%s,%s,'Pending')",
         (found_id, user_id, date.today(), proof))
    set_status("Found", found_id, "Claim Pending")


def list_claims(status=None):
    rows = _run("SELECT c.*, u.full_name AS claimant, u.student_id, f.item_name, f.date_found FROM claims c "
                "JOIN users u ON u.user_id=c.user_id JOIN found_items f ON f.found_item_id=c.found_item_id "
                "WHERE (%s IS NULL OR c.status=%s) ORDER BY c.claim_id DESC", (status, status), "all")
    for r in rows:
        try:
            p = json.loads(r["proof"])
        except ValueError:
            p = {"file": r["proof"]}
        r["proof_abs"], r["lost_item_id"] = abs_path(p.get("file")), p.get("lost_item_id")
        r["claim_date"] = r["claim_date"].strftime("%Y-%m-%d")
        r["report_no"] = f"FND-{r['date_found'].year}-{r['found_item_id']:05d}"
    return rows


def resolve_claim(claim_id, approve):
    c = next((x for x in list_claims() if x["claim_id"] == claim_id), None)
    if not c or c["status"] != "Pending":
        raise DBError("This claim was already processed.")
    _run("UPDATE claims SET status=%s WHERE claim_id=%s", ("Approved" if approve else "Rejected", claim_id))
    set_status("Found", c["found_item_id"], "Claimed" if approve else "Available")
    if approve and c["lost_item_id"]:
        set_status("Lost", c["lost_item_id"], "Claimed")


def stats(user_id=None):
    def n(sql, *p):
        return _run(sql, p, "one")["c"]
    f = " WHERE user_id=%s" if user_id else ""
    p = (user_id,) if user_id else ()
    g = " AND user_id=%s" if user_id else ""
    s = {"lost": n("SELECT COUNT(*) c FROM lost_items" + f, *p), "found": n("SELECT COUNT(*) c FROM found_items" + f, *p),
         "pending": n("SELECT COUNT(*) c FROM lost_items WHERE status='Pending'" + g, *p)
         + n("SELECT COUNT(*) c FROM found_items WHERE status='Pending'" + g, *p),
         "claimed": n("SELECT COUNT(*) c FROM lost_items WHERE status='Claimed'" + g, *p)}
    if not user_id:
        s["students"] = n("SELECT COUNT(*) c FROM users WHERE role='student'")
        s["claims"] = n("SELECT COUNT(*) c FROM claims WHERE status='Pending'")
    return s