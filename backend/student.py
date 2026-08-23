"""
student.py — Student-facing data routes for the FastAPI backend.

Endpoints:
  GET  /api/student/attendance   — subject-wise attendance from the DB
  GET  /api/student/eligibility  — exam eligibility from DB (attendance + marks)
  GET  /api/student/timetable    — timetable for a given programme + day
  GET  /api/student/calendar     — academic calendar events
  POST /api/student/link         — link the logged-in email to a roll number
  POST /api/student/leave        — generate a leave application letter via LLM
"""

import json
import os
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

import db
from auth import get_current_user

router = APIRouter(prefix="/api/student", tags=["student"])

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


@router.get("/attendance")
async def get_attendance(user: dict = Depends(get_current_user)):
    """Return the logged-in student's attendance report."""
    report = db.get_student_attendance_report(user["email"])
    return report


@router.get("/eligibility")
async def get_eligibility(user: dict = Depends(get_current_user)):
    """Return the logged-in student's exam eligibility report."""
    report = db.get_student_eligibility_report(user["email"])
    return report


@router.get("/timetable")
async def get_timetable(programme: str = "BCA", day: str | None = None, user: dict = Depends(get_current_user)):
    """Return the timetable slots for the given programme and day (defaults to today)."""
    tt_path = DATA_DIR / "timetable.json"
    if not tt_path.exists():
        raise HTTPException(status_code=404, detail="Timetable not found. Admin must upload it first.")
    timetable = json.loads(tt_path.read_text(encoding="utf-8-sig"))
    day_name = day or date.today().strftime("%A")
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    programmes = list(timetable.keys())
    programme_slots = timetable.get(programme, {})
    available_days = [d for d in days_order if d in programme_slots]
    slots = programme_slots.get(day_name, [])
    return {
        "programme": programme,
        "day": day_name,
        "today": date.today().strftime("%A"),
        "programmes": programmes,
        "available_days": available_days,
        "slots": slots,
    }


@router.get("/calendar")
async def get_calendar(user: dict = Depends(get_current_user)):
    """Return the academic calendar events."""
    cal_path = DATA_DIR / "academic_calendar.json"
    if not cal_path.exists():
        raise HTTPException(status_code=404, detail="Academic calendar not found.")
    events = json.loads(cal_path.read_text(encoding="utf-8-sig"))
    today_str = date.today().isoformat()
    for e in events:
        e["days_away"] = (date.fromisoformat(e["date"]) - date.today()).days
    return {"today": today_str, "events": events}


@router.post("/link")
async def link_roll_no(request: Request, user: dict = Depends(get_current_user)):
    """Let a student link their roll number to their Google account."""
    body = await request.json()
    roll_no = body.get("roll_no", "").strip()
    if not roll_no:
        raise HTTPException(status_code=400, detail="Roll number is required.")
    success, message = db.link_student_email(roll_no, user["email"])
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message, "roll_no": roll_no}


@router.post("/leave")
async def generate_leave(request: Request, user: dict = Depends(get_current_user)):
    """Generate a formal leave application using the Groq LLM."""
    from langchain_groq import ChatGroq
    body = await request.json()
    student_name = body.get("student_name", "")
    roll_no = body.get("roll_no", "")
    programme = body.get("programme", "BCA")
    semester = body.get("semester", "1st")
    from_date = body.get("from_date", "")
    to_date = body.get("to_date", "")
    reason = body.get("reason", "")
    hod_name = body.get("hod_name", "")

    if not student_name.strip() or not reason.strip():
        raise HTTPException(status_code=400, detail="Name and reason are required.")

    try:
        from datetime import datetime as dt
        d_from = dt.fromisoformat(from_date)
        d_to = dt.fromisoformat(to_date)
        days = (d_to - d_from).days + 1
        from_fmt = d_from.strftime("%d %B %Y")
        to_fmt = d_to.strftime("%d %B %Y")
    except Exception:
        from_fmt, to_fmt, days = from_date, to_date, "?"

    hod_line = f"The HOD, {hod_name}," if hod_name.strip() else "The Head of Department,"
    prompt = (
        f"Write a formal leave application letter from a college student with these details:\n"
        f"Student Name: {student_name}\nRoll Number: {roll_no}\n"
        f"Programme: {programme}, {semester} Semester\n"
        f"Leave dates: {from_fmt} to {to_fmt} ({days} day(s))\n"
        f"Reason: {reason}\nAddressed to: {hod_line}\n\n"
        f"Write a professional, polite, and concise formal letter. "
        f"Include all standard components: sender's details, date, recipient, subject line, body, closing. "
        f"Do not add any commentary or explanation outside the letter itself."
    )
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.4)
    response = llm.invoke(prompt)
    return {"letter": response.content.strip()}
