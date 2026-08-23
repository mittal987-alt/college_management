"""
admin.py — Admin-only routes for the FastAPI backend.

Endpoints:
  GET  /api/admin/stats              — usage stats (interactions + feedback)
  GET  /api/admin/config             — eligibility config
  PUT  /api/admin/config             — update eligibility config
  POST /api/admin/upload/students    — upload student roster CSV/JSON
  POST /api/admin/upload/attendance  — upload attendance CSV/JSON/PDF
  POST /api/admin/upload/timetable   — upload timetable JSON
  POST /api/admin/upload/calendar    — upload academic calendar JSON
"""

import json
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

import db
from auth import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
INTERACTIONS_LOG = DATA_DIR / "interactions.jsonl"
FEEDBACK_LOG = DATA_DIR / "feedback.jsonl"

# ── Column aliases (same logic as admin_upload.py) ────────────────────────────
ROLL_NO_ALIASES = ["roll_no", "roll no", "rollno", "enrollment_no", "enrollment no", "enrollmentno", "enroll_no"]
NAME_ALIASES = ["name", "student_name", "student name"]
STATUS_ALIASES = ["status", "attendance", "present/absent", "present_absent"]
EMAIL_ALIASES = ["email", "email_id", "emailid", "e-mail"]
PROGRAMME_ALIASES = ["programme", "program", "course", "department"]

STATUS_MAP = {
    "present": "present", "p": "present", "1": "present", "yes": "present", "true": "present",
    "absent": "absent", "a": "absent", "0": "absent", "no": "absent", "false": "absent",
}


def _find_col(columns, aliases):
    lower_map = {c.lower().strip(): c for c in columns}
    for a in aliases:
        if a in lower_map:
            return lower_map[a]
    return None


def _parse_csv(content: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(BytesIO(content), sep=None, engine="python", on_bad_lines="skip")
    except Exception:
        return pd.read_csv(BytesIO(content), on_bad_lines="skip")


def _parse_json_file(content: bytes) -> pd.DataFrame:
    data = json.loads(content)
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    return pd.DataFrame(data)


def _parse_pdf(content: bytes) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("PDF support requires pdfplumber: pip install pdfplumber")
    all_rows, header = [], None
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            if header is None:
                header = table[0]
                all_rows.extend(table[1:])
            else:
                all_rows.extend(table[1:] if table[0] == header else table)
    if not header:
        raise ValueError("No table found in PDF.")
    return pd.DataFrame(all_rows, columns=header)


# ── Stats ─────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(user: dict = Depends(get_admin_user)):
    """Return interaction + feedback statistics for the admin dashboard."""
    def _load_jsonl(path: Path):
        if not path.exists():
            return []
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    interactions = _load_jsonl(INTERACTIONS_LOG)
    feedback = _load_jsonl(FEEDBACK_LOG)
    college_q = [i for i in interactions if i.get("mode") == "college"]

    down_count = sum(1 for f in feedback if f.get("feedback") == "down")
    down_rate = (down_count / len(feedback) * 100) if feedback else 0.0

    query_type_counts: dict = {}
    for q in college_q:
        qt = q.get("query_type", "general")
        query_type_counts[qt] = query_type_counts.get(qt, 0) + 1

    query_freq: dict = {}
    for q in college_q:
        text = (q.get("query") or "").strip().lower()
        query_freq[text] = query_freq.get(text, 0) + 1
    top_queries = sorted(query_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # Daily feedback negative rate
    daily_down: dict = {}
    daily_total: dict = {}
    for f in feedback:
        d = (f.get("timestamp") or "")[:10]
        daily_total[d] = daily_total.get(d, 0) + 1
        if f.get("feedback") == "down":
            daily_down[d] = daily_down.get(d, 0) + 1
    daily_down_rate = {d: round(daily_down.get(d, 0) / t * 100, 1) for d, t in daily_total.items()}

    daily_volume: dict = {}
    for q in college_q:
        d = (q.get("timestamp") or "")[:10]
        daily_volume[d] = daily_volume.get(d, 0) + 1

    unique_users = len({q.get("user") for q in college_q})

    return {
        "total_questions": len(college_q),
        "unique_students": unique_users,
        "down_rate": round(down_rate, 1),
        "query_type_counts": query_type_counts,
        "top_queries": [{"query": q, "count": c} for q, c in top_queries],
        "daily_down_rate": daily_down_rate,
        "daily_volume": daily_volume,
        "recent_interactions": college_q[-200:],
    }


# ── Config ────────────────────────────────────────────────────────────────────
@router.get("/config")
async def get_config(user: dict = Depends(get_admin_user)):
    return {
        "min_attendance_pct": float(db.get_config("min_attendance_pct", 75)),
        "min_internal_pct": float(db.get_config("min_internal_pct", 40)),
    }


@router.put("/config")
async def update_config(request: Request, user: dict = Depends(get_admin_user)):
    body = await request.json()
    if "min_attendance_pct" in body:
        db.set_config("min_attendance_pct", str(body["min_attendance_pct"]))
    if "min_internal_pct" in body:
        db.set_config("min_internal_pct", str(body["min_internal_pct"]))
    return {"ok": True}


# ── Upload: Students ──────────────────────────────────────────────────────────
@router.post("/upload/students")
async def upload_students(file: UploadFile = File(...), user: dict = Depends(get_admin_user)):
    """Upload a student roster CSV/JSON and upsert each student into the DB."""
    content = await file.read()
    suffix = (file.filename or "").split(".")[-1].lower()
    try:
        if suffix == "csv":
            df = _parse_csv(content)
        elif suffix == "json":
            df = _parse_json_file(content)
        else:
            raise HTTPException(status_code=400, detail="Only CSV or JSON supported for student uploads.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    roll_col = _find_col(df.columns, ROLL_NO_ALIASES)
    name_col = _find_col(df.columns, NAME_ALIASES)
    email_col = _find_col(df.columns, EMAIL_ALIASES)
    prog_col = _find_col(df.columns, PROGRAMME_ALIASES)

    if not roll_col:
        raise HTTPException(status_code=422, detail=f"Could not find a roll number column. Columns found: {list(df.columns)}")

    saved = 0
    for _, row in df.iterrows():
        roll_no = str(row[roll_col]).strip()
        if not roll_no or roll_no.lower() == "nan":
            continue
        name = str(row[name_col]).strip() if name_col else ""
        email = str(row[email_col]).strip().lower() if email_col else ""
        programme = str(row[prog_col]).strip() if prog_col else ""
        db.save_student(roll_no, email, name, programme)
        saved += 1

    return {"ok": True, "saved": saved}


# ── Upload: Attendance ────────────────────────────────────────────────────────
@router.post("/upload/attendance")
async def upload_attendance(
    file: UploadFile = File(...),
    subject: str = Form(...),
    session_date: str = Form(...),
    user: dict = Depends(get_admin_user),
):
    """Upload an attendance sheet (CSV/JSON/PDF) for a given subject + date."""
    content = await file.read()
    suffix = (file.filename or "").split(".")[-1].lower()
    try:
        if suffix == "csv":
            df = _parse_csv(content)
        elif suffix == "json":
            df = _parse_json_file(content)
        elif suffix == "pdf":
            df = _parse_pdf(content)
        else:
            raise HTTPException(status_code=400, detail="Only CSV, JSON, or PDF supported.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    roll_col = _find_col(df.columns, ROLL_NO_ALIASES)
    status_col = _find_col(df.columns, STATUS_ALIASES)

    if not roll_col or not status_col:
        raise HTTPException(status_code=422, detail=f"Could not find roll number or status columns. Found: {list(df.columns)}")

    saved, skipped, bad_status = 0, 0, []
    for _, row in df.iterrows():
        roll_no = str(row[roll_col]).strip()
        if not roll_no or roll_no.lower() == "nan":
            skipped += 1
            continue
        raw_status = str(row[status_col]).strip().lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            bad_status.append({"roll_no": roll_no, "raw_status": raw_status})
            continue
        db.record_attendance_session(roll_no, subject.strip(), session_date, status)
        saved += 1

    return {"ok": True, "saved": saved, "skipped": skipped, "bad_status_rows": bad_status}


# ── Upload: Timetable ─────────────────────────────────────────────────────────
@router.post("/upload/timetable")
async def upload_timetable(file: UploadFile = File(...), user: dict = Depends(get_admin_user)):
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    out = DATA_DIR / "timetable.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "programmes": list(data.keys()) if isinstance(data, dict) else []}


# ── Upload: Calendar ──────────────────────────────────────────────────────────
@router.post("/upload/calendar")
async def upload_calendar(file: UploadFile = File(...), user: dict = Depends(get_admin_user)):
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    out = DATA_DIR / "academic_calendar.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "event_count": len(data) if isinstance(data, list) else 0}
