"""
admin_data_upload.py — Admin pages for uploading Timetable and Academic Calendar data
(CSV, JSON, or PDF), replacing manual editing of timetable.json / academic_calendar.json.

Drop this file next to app.py, db.py, admin_upload.py, student_upload.py. Wire in like:

    from admin_data_upload import run_admin_timetable_upload, run_admin_calendar_upload
    ...
    if IS_ADMIN:
        mode_options.append("🗓️ Upload Timetable")
        mode_options.append("📅 Upload Calendar")
    ...
    elif mode == "🗓️ Upload Timetable":
        run_admin_timetable_upload()
    elif mode == "📅 Upload Calendar":
        run_admin_calendar_upload()

Expected TIMETABLE file columns (names are flexible):
    programme, day, time, subject, room (optional), teacher (optional)
    e.g. "BCA, Monday, 9:00-10:00, Web Technologies, Room 105, Mr. Kumar"

Expected CALENDAR file columns (names are flexible):
    date, title, type (exam / holiday / deadline / event)
    e.g. "2026-09-15, Mid-sem exams begin, exam"
"""

import json
from datetime import date as _date
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from ui_helpers import render_admin_banner

DATA_DIR = Path("data")
TIMETABLE_PATH = DATA_DIR / "timetable.json"
CALENDAR_PATH = DATA_DIR / "academic_calendar.json"


# ============================================================
# Shared file parsing (same approach as admin_upload.py / student_upload.py)
# ============================================================

def _parse_csv(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file, sep=None, engine="python", on_bad_lines="skip")
    except Exception:
        file.seek(0)
        return pd.read_csv(file, on_bad_lines="skip")


def _parse_json(file) -> pd.DataFrame:
    data = json.load(file)
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    return pd.DataFrame(data)


def _parse_pdf(file) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("PDF support needs: pip install pdfplumber")

    all_rows, header = [], None
    with pdfplumber.open(file) as pdf:
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
        raise ValueError("No table detected in this PDF (won't work for scanned/image-only PDFs).")
    return pd.DataFrame(all_rows, columns=header)


def _parse_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = uploaded_file.name.split(".")[-1].lower()
    if suffix == "csv":
        return _parse_csv(uploaded_file)
    elif suffix == "json":
        return _parse_json(uploaded_file)
    elif suffix == "pdf":
        return _parse_pdf(BytesIO(uploaded_file.read()))
    else:
        raise ValueError("Unsupported file type.")


def _find_column(columns, aliases):
    def _clean(c):
        return " ".join(str(c).replace("\n", " ").split()).lower().strip().rstrip(".")

    lower_map = {_clean(c): c for c in columns}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    for alias in aliases:
        for cleaned, original in lower_map.items():
            if alias in cleaned:
                return original
    return None


# ============================================================
# TIMETABLE upload
# ============================================================

TT_PROGRAMME_ALIASES = ["programme", "program", "course", "branch"]
TT_DAY_ALIASES = ["day", "weekday"]
TT_TIME_ALIASES = ["time", "slot", "time slot"]
TT_SUBJECT_ALIASES = ["subject", "class", "course name"]
TT_ROOM_ALIASES = ["room", "room no", "venue"]
TT_TEACHER_ALIASES = ["teacher", "faculty", "instructor"]

VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def run_admin_timetable_upload():
    render_admin_banner("Upload Timetable")
    st.markdown("""
    <div class="main-header">
        <h1>🗓️ Upload Timetable</h1>
        <p>Upload the full class timetable — replaces the current schedule shown to students</p>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Expected columns (names are flexible): **programme**, **day**, **time**, **subject**, "
        "**room** (optional), **teacher** (optional). One row per class slot. "
        "Use subject = 'LUNCH BREAK' for the lunch row."
    )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "json", "pdf"], key="timetable_upload")
    if not uploaded_file:
        return

    try:
        raw_df = _parse_uploaded_file(uploaded_file)
    except Exception as e:
        st.error(f"Couldn't read this file: {e}")
        return

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    prog_col = _find_column(raw_df.columns, TT_PROGRAMME_ALIASES)
    day_col = _find_column(raw_df.columns, TT_DAY_ALIASES)
    time_col = _find_column(raw_df.columns, TT_TIME_ALIASES)
    subject_col = _find_column(raw_df.columns, TT_SUBJECT_ALIASES)
    room_col = _find_column(raw_df.columns, TT_ROOM_ALIASES)
    teacher_col = _find_column(raw_df.columns, TT_TEACHER_ALIASES)

    missing = [
        label for label, col in
        [("programme", prog_col), ("day", day_col), ("time", time_col), ("subject", subject_col)]
        if not col
    ]
    if missing:
        st.error(f"Could not find a column for: {', '.join(missing)}. Columns found: {list(raw_df.columns)}")
        st.dataframe(raw_df.head(10), use_container_width=True)
        return

    clean_df = pd.DataFrame({
        "programme": raw_df[prog_col].astype(str).str.strip(),
        "day": raw_df[day_col].astype(str).str.strip().str.title(),
        "time": raw_df[time_col].astype(str).str.strip(),
        "subject": raw_df[subject_col].astype(str).str.strip(),
        "room": raw_df[room_col].astype(str).str.strip() if room_col else "",
        "teacher": raw_df[teacher_col].astype(str).str.strip() if teacher_col else "",
    })

    bad_day_mask = ~clean_df["day"].isin(VALID_DAYS)
    if bad_day_mask.any():
        st.warning(
            f"{bad_day_mask.sum()} row(s) have a day value that isn't a recognized weekday "
            f"and will be skipped: {sorted(clean_df.loc[bad_day_mask, 'day'].unique().tolist())}"
        )
    clean_df = clean_df[~bad_day_mask]

    st.markdown("#### Preview")
    st.dataframe(clean_df, use_container_width=True)

    if clean_df.empty:
        st.error("No valid rows to save.")
        return

    programmes_found = sorted(clean_df["programme"].unique().tolist())
    st.info(f"Ready to save timetable for: **{', '.join(programmes_found)}** ({len(clean_df)} class slots total).")

    replace_all = st.checkbox(
        "Replace the entire timetable file (unchecked = only update the programmes listed above, keep others)",
        value=False,
    )

    if st.button("✅ Confirm and Save Timetable", type="primary", use_container_width=True):
        if TIMETABLE_PATH.exists() and not replace_all:
            timetable = json.loads(TIMETABLE_PATH.read_text(encoding="utf-8-sig"))
        else:
            timetable = {}

        for programme in programmes_found:
            timetable[programme] = {}
            prog_rows = clean_df[clean_df["programme"] == programme]
            for day in prog_rows["day"].unique():
                day_rows = prog_rows[prog_rows["day"] == day]
                slots = []
                for _, row in day_rows.iterrows():
                    slot = {"time": row["time"], "subject": row["subject"]}
                    if row["room"]:
                        slot["room"] = row["room"]
                    if row["teacher"]:
                        slot["teacher"] = row["teacher"]
                    slots.append(slot)
                timetable[programme][day] = slots

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TIMETABLE_PATH.write_text(json.dumps(timetable, indent=2, ensure_ascii=False), encoding="utf-8")
        st.success(f"Timetable saved for {len(programmes_found)} programme(s). ✅")
        st.balloons()


# ============================================================
# ACADEMIC CALENDAR upload
# ============================================================

CAL_DATE_ALIASES = ["date"]
CAL_TITLE_ALIASES = ["title", "event", "name", "description"]
CAL_TYPE_ALIASES = ["type", "category"]

VALID_TYPES = ["exam", "holiday", "deadline", "event"]


def run_admin_calendar_upload():
    render_admin_banner("Upload Calendar")
    st.markdown("""
    <div class="main-header">
        <h1>📅 Upload Academic Calendar</h1>
        <p>Upload exams, holidays, deadlines and events — replaces the current calendar</p>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Expected columns (names are flexible): **date** (YYYY-MM-DD), **title**, "
        f"**type** (one of: {', '.join(VALID_TYPES)})."
    )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "json", "pdf"], key="calendar_upload")
    if not uploaded_file:
        return

    try:
        raw_df = _parse_uploaded_file(uploaded_file)
    except Exception as e:
        st.error(f"Couldn't read this file: {e}")
        return

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    date_col = _find_column(raw_df.columns, CAL_DATE_ALIASES)
    title_col = _find_column(raw_df.columns, CAL_TITLE_ALIASES)
    type_col = _find_column(raw_df.columns, CAL_TYPE_ALIASES)

    missing = [label for label, col in [("date", date_col), ("title", title_col), ("type", type_col)] if not col]
    if missing:
        st.error(f"Could not find a column for: {', '.join(missing)}. Columns found: {list(raw_df.columns)}")
        st.dataframe(raw_df.head(10), use_container_width=True)
        return

    clean_df = pd.DataFrame({
        "date_raw": raw_df[date_col].astype(str).str.strip(),
        "title": raw_df[title_col].astype(str).str.strip(),
        "type": raw_df[type_col].astype(str).str.strip().str.lower(),
    })

    clean_df["date_parsed"] = pd.to_datetime(clean_df["date_raw"], errors="coerce", format="mixed")
    bad_date_mask = clean_df["date_parsed"].isna()
    bad_type_mask = ~clean_df["type"].isin(VALID_TYPES)

    good_rows = clean_df[~bad_date_mask & ~bad_type_mask]
    bad_rows = clean_df[bad_date_mask | bad_type_mask]

    st.markdown("#### Preview")
    st.dataframe(good_rows[["date_raw", "title", "type"]], use_container_width=True)

    if not bad_rows.empty:
        st.warning(
            f"{len(bad_rows)} row(s) have an unparseable date or invalid type "
            f"(must be one of: {', '.join(VALID_TYPES)}) and will be skipped."
        )
        st.dataframe(bad_rows[["date_raw", "title", "type"]], use_container_width=True)

    if good_rows.empty:
        st.error("No valid rows to save.")
        return

    st.info(f"Ready to save **{len(good_rows)}** calendar event(s).")

    replace_all = st.checkbox(
        "Replace the entire calendar (unchecked = add these to the existing calendar)",
        value=False,
    )

    if st.button("✅ Confirm and Save Calendar", type="primary", use_container_width=True):
        new_events = [
            {"date": row["date_parsed"].strftime("%Y-%m-%d"), "title": row["title"], "type": row["type"]}
            for _, row in good_rows.iterrows()
        ]

        if CALENDAR_PATH.exists() and not replace_all:
            existing = json.loads(CALENDAR_PATH.read_text(encoding="utf-8-sig"))
        else:
            existing = []

        combined = existing + new_events
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CALENDAR_PATH.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        st.success(f"Saved {len(new_events)} event(s). Calendar now has {len(combined)} total. ✅")
        st.balloons()