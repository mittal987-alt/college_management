"""
db.py — SQLite database layer for the College Assistant app.

Drop this file next to your main app.py. It handles:
  - Creating the database + tables (init_db)
  - Reading/writing attendance data
  - Reading/writing marks data
  - Reading/writing admin config (e.g. eligibility thresholds)
  - Linking a student's roll number to their login email

Usage in your main app.py:

    import db
    db.init_db()   # call once, near the top, right after DATA_DIR.mkdir()

Nothing here touches Streamlit — this file only knows about the database,
so it's easy to test on its own (see test_db.py).
"""

import sqlite3
from pathlib import Path

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "college.db"


def get_connection():
    """Open a connection to the database. Creates the data/ folder if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["subject"]
    return conn


def init_db():
    """Create all tables if they don't already exist. Safe to call every app start."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email          TEXT PRIMARY KEY,
            password_hash  TEXT,
            name           TEXT,
            is_admin       INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll_no    TEXT PRIMARY KEY,
            email      TEXT UNIQUE,
            name       TEXT,
            programme  TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            roll_no    TEXT NOT NULL,
            subject    TEXT NOT NULL,
            held       INTEGER NOT NULL DEFAULT 0,
            attended   INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (roll_no, subject)
        )
    """)

    # One row per student per class session. This is the real source of truth —
    # the `attendance` table above is kept for simple manual totals if you ever need them,
    # but uploads from CSV (enrollment_no, roll_no, name, status) go here instead,
    # so every upload ADDS to history rather than overwriting a running total.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            roll_no       TEXT NOT NULL,
            subject       TEXT NOT NULL,
            session_date  TEXT NOT NULL,
            status        TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            PRIMARY KEY (roll_no, subject, session_date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            roll_no         TEXT NOT NULL,
            subject         TEXT NOT NULL,
            internal_marks  REAL NOT NULL DEFAULT 0,
            internal_max    REAL NOT NULL DEFAULT 30,
            PRIMARY KEY (roll_no, subject)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key    TEXT PRIMARY KEY,
            value  TEXT
        )
    """)

    conn.commit()
    conn.close()


def create_user(email: str, password_hash: str, name: str = "", is_admin: bool = False):
    """Create a local email/password user in the auth database."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO users (email, password_hash, name, is_admin)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            password_hash = excluded.password_hash,
            name = excluded.name,
            is_admin = excluded.is_admin
        """,
        (email.strip().lower(), password_hash, name.strip(), 1 if is_admin else 0),
    )
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    """Return a user row keyed by email, or None if the user does not exist."""
    conn = get_connection()
    row = conn.execute(
        "SELECT email, password_hash, name, is_admin FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# Students — link a roll number to a login email
# ============================================================

def save_student(roll_no: str, email: str = "", name: str = "", programme: str = ""):
    """
    Create or update a student record. Call this once per student (e.g. from an admin upload).
    email is optional — pass "" if not known yet; it's stored as NULL so multiple
    students without an email don't collide with the UNIQUE constraint.
    """
    conn = get_connection()
    email_value = email.strip().lower() if email and email.strip() else None
    conn.execute("""
        INSERT INTO students (roll_no, email, name, programme)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(roll_no) DO UPDATE SET
            email = COALESCE(excluded.email, students.email),
            name = excluded.name,
            programme = excluded.programme
    """, (roll_no.strip(), email_value, name.strip(), programme.strip()))
    conn.commit()
    conn.close()


def link_student_email(roll_no: str, email: str):
    """
    Let a student self-link their login email to an existing roll number record
    (added earlier by admin, possibly without an email). Only succeeds if that
    roll number already exists — this prevents anyone from linking to a roll
    number that was never uploaded by admin. Returns (success: bool, message: str).
    """
    roll_no = roll_no.strip()
    email = email.strip().lower()

    existing = get_student(roll_no)
    if not existing:
        return False, (
            f"Roll number '{roll_no}' was not found. Please check it's correct, "
            f"or ask your admin to add you first."
        )

    if existing.get("email") and existing["email"] != email:
        return False, (
            f"Roll number '{roll_no}' is already linked to a different account. "
            f"If this is a mistake, contact your admin."
        )

    conn = get_connection()
    conn.execute("UPDATE students SET email = ? WHERE roll_no = ?", (email, roll_no))
    conn.commit()
    conn.close()
    return True, f"Linked successfully as {roll_no}."


def get_roll_no_by_email(email: str):
    """Look up a student's roll number from their login email. Returns None if not linked yet."""
    conn = get_connection()
    row = conn.execute(
        "SELECT roll_no FROM students WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return row["roll_no"] if row else None


def get_student(roll_no: str):
    """Return a student's full record as a dict, or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# Attendance
# ============================================================

def save_attendance(roll_no: str, subject: str, held: int, attended: int):
    """Insert or update the attendance row for one student + subject."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance (roll_no, subject, held, attended)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(roll_no, subject) DO UPDATE SET
            held = excluded.held,
            attended = excluded.attended
    """, (roll_no.strip(), subject.strip(), int(held), int(attended)))
    conn.commit()
    conn.close()


def get_attendance(roll_no: str):
    """Return a list of dicts: [{'subject': ..., 'held': ..., 'attended': ...}, ...] for one student."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT subject, held, attended FROM attendance WHERE roll_no = ? ORDER BY subject",
        (roll_no,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------
# Session-based attendance (from CSV uploads: one row per student per class)
# ------------------------------------------------------------

def record_attendance_session(roll_no: str, subject: str, session_date: str, status: str):
    """
    Record one student's attendance for one class session.
    status must be 'present' or 'absent'.
    Re-uploading the same roll_no + subject + date safely overwrites that single session
    (e.g. if admin re-uploads a corrected sheet), without touching other sessions.
    """
    status = status.strip().lower()
    if status not in ("present", "absent"):
        raise ValueError(f"status must be 'present' or 'absent', got: {status!r}")

    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance_sessions (roll_no, subject, session_date, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(roll_no, subject, session_date) DO UPDATE SET
            status = excluded.status
    """, (roll_no.strip(), subject.strip(), session_date.strip(), status))
    conn.commit()
    conn.close()


def get_attendance_summary(roll_no: str):
    """
    Return per-subject totals computed from all recorded sessions:
    [{'subject': ..., 'held': ..., 'attended': ..., 'pct': ...}, ...]
    This is what student-facing pages should use once sessions have been uploaded.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            subject,
            COUNT(*) AS held,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) AS attended
        FROM attendance_sessions
        WHERE roll_no = ?
        GROUP BY subject
        ORDER BY subject
    """, (roll_no,)).fetchall()
    conn.close()

    result = []
    for r in rows:
        held, attended = r["held"], r["attended"]
        pct = (attended / held * 100) if held > 0 else 0.0
        result.append({"subject": r["subject"], "held": held, "attended": attended, "pct": round(pct, 1)})
    return result


# ============================================================
# Marks
# ============================================================

def save_marks(roll_no: str, subject: str, internal_marks: float, internal_max: float = 30):
    """Insert or update the internal marks row for one student + subject."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO marks (roll_no, subject, internal_marks, internal_max)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(roll_no, subject) DO UPDATE SET
            internal_marks = excluded.internal_marks,
            internal_max = excluded.internal_max
    """, (roll_no.strip(), subject.strip(), float(internal_marks), float(internal_max)))
    conn.commit()
    conn.close()


def get_marks(roll_no: str):
    """Return a list of dicts: [{'subject': ..., 'internal_marks': ..., 'internal_max': ...}, ...]."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT subject, internal_marks, internal_max FROM marks WHERE roll_no = ? ORDER BY subject",
        (roll_no,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# Config — admin-set values like eligibility thresholds
# ============================================================

def set_config(key: str, value: str):
    """Set (or overwrite) a config value, e.g. set_config('min_attendance_pct', '75')."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()


def get_config(key: str, default=None):
    """Get a config value. Returns `default` if the key has never been set."""
    conn = get_connection()
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


# ============================================================
# Combined lookups — used by the chatbot's live-data nodes
# ============================================================

def get_student_attendance_report(email: str):
    """
    One-stop lookup for the chatbot: given a logged-in student's email, returns
    a dict describing their attendance situation, or an explanation if they're
    not linked yet. Always returns a dict — never raises — so the calling node
    can just describe the result to the LLM.
    """
    roll_no = get_roll_no_by_email(email)
    if not roll_no:
        return {
            "linked": False,
            "message": (
                "This student's account is not yet linked to a roll number. "
                "They should ask the admin to add them via the Upload Students page."
            ),
        }

    summary = get_attendance_summary(roll_no)
    if not summary:
        return {
            "linked": True,
            "roll_no": roll_no,
            "message": "No attendance sessions have been recorded for this student yet.",
        }

    min_pct = float(get_config("min_attendance_pct", default=75))
    for row in summary:
        row["eligible"] = row["pct"] >= min_pct

    overall_held = sum(r["held"] for r in summary)
    overall_attended = sum(r["attended"] for r in summary)
    overall_pct = round((overall_attended / overall_held * 100) if overall_held > 0 else 0.0, 1)

    return {
        "linked": True,
        "roll_no": roll_no,
        "required_pct": min_pct,
        "overall_pct": overall_pct,
        "overall_eligible": overall_pct >= min_pct,
        "subjects": summary,
    }


def get_student_eligibility_report(email: str):
    """
    One-stop lookup for exam eligibility: combines attendance % and internal marks %
    against the admin-set thresholds, per subject.
    """
    roll_no = get_roll_no_by_email(email)
    if not roll_no:
        return {
            "linked": False,
            "message": (
                "This student's account is not yet linked to a roll number. "
                "They should ask the admin to add them via the Upload Students page."
            ),
        }

    attendance_summary = {row["subject"]: row for row in get_attendance_summary(roll_no)}
    marks_rows = get_marks(roll_no)

    min_att_pct = float(get_config("min_attendance_pct", default=75))
    min_marks_pct = float(get_config("min_internal_pct", default=40))

    subjects = set(attendance_summary) | {m["subject"] for m in marks_rows}
    if not subjects:
        return {
            "linked": True,
            "roll_no": roll_no,
            "message": "No attendance or marks data has been recorded for this student yet.",
        }

    marks_by_subject = {m["subject"]: m for m in marks_rows}
    report = []
    for subject in sorted(subjects):
        att = attendance_summary.get(subject)
        att_pct = att["pct"] if att else 0.0
        att_ok = att_pct >= min_att_pct

        marks = marks_by_subject.get(subject)
        if marks and marks["internal_max"] > 0:
            marks_pct = round(marks["internal_marks"] / marks["internal_max"] * 100, 1)
        else:
            marks_pct = None
        marks_ok = (marks_pct is not None) and (marks_pct >= min_marks_pct)

        report.append({
            "subject": subject,
            "attendance_pct": att_pct,
            "attendance_ok": att_ok,
            "internal_marks_pct": marks_pct,
            "internal_marks_ok": marks_ok if marks_pct is not None else None,
            "eligible": att_ok and (marks_ok if marks_pct is not None else True),
        })

    return {
        "linked": True,
        "roll_no": roll_no,
        "required_attendance_pct": min_att_pct,
        "required_internal_pct": min_marks_pct,
        "subjects": report,
        "all_eligible": all(r["eligible"] for r in report),
    }


# ============================================================
# Combined eligibility check — attendance + marks + admin-set thresholds
# ============================================================

def get_eligibility_summary(roll_no: str):
    """
    Combine attendance and marks against admin-set thresholds (from config).
    Returns (results, min_attendance_pct, min_internal_pct) where results is:
    [{'subject': ..., 'attendance_pct': ..., 'internal_pct': ... or None,
      'attendance_ok': bool, 'internal_ok': bool, 'eligible': bool}, ...]

    If marks haven't been uploaded for a subject, internal_pct is None and
    internal_ok defaults to True (we don't block on data that doesn't exist yet).
    """
    min_attendance_pct = float(get_config("min_attendance_pct", 75))
    min_internal_pct = float(get_config("min_internal_pct", 40))

    attendance = get_attendance_summary(roll_no)
    marks = {m["subject"]: m for m in get_marks(roll_no)}

    results = []
    for a in attendance:
        subject = a["subject"]
        attendance_pct = a["pct"]
        attendance_ok = attendance_pct >= min_attendance_pct

        m = marks.get(subject)
        if m and m["internal_max"] > 0:
            internal_pct = round(m["internal_marks"] / m["internal_max"] * 100, 1)
            internal_ok = internal_pct >= min_internal_pct
        else:
            internal_pct = None
            internal_ok = True  # no marks data yet — don't block on missing info

        results.append({
            "subject": subject,
            "attendance_pct": attendance_pct,
            "internal_pct": internal_pct,
            "attendance_ok": attendance_ok,
            "internal_ok": internal_ok,
            "eligible": attendance_ok and internal_ok,
        })

    return results, min_attendance_pct, min_internal_pct


if __name__ == "__main__":
    # Running `python db.py` directly just sets up the database — handy for a quick manual check.
    init_db()
    print(f"Database ready at: {DB_PATH.resolve()}")