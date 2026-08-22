"""
admin_upload.py — Admin page for uploading attendance data (CSV, JSON, or PDF).

Drop this file next to your main app.py and db.py. In your main app, import it
and call run_admin_attendance_upload() from your admin-only section, e.g.:

    from admin_upload import run_admin_attendance_upload
    ...
    if IS_ADMIN:
        mode_options.append("📤 Upload Attendance")
    ...
    elif mode == "📤 Upload Attendance":
        run_admin_attendance_upload()

Requires: pandas (you already have it), pdfplumber (for PDF uploads only)
    pip install pdfplumber
"""

import json
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

import db
from ui_helpers import render_admin_banner


# ------------------------------------------------------------
# Column name detection — admin's file might use slightly different headers
# ------------------------------------------------------------
ROLL_NO_ALIASES = ["roll_no", "roll no", "rollno", "enrollment_no", "enrollment no", "enrollmentno", "enroll_no"]
NAME_ALIASES = ["name", "student_name", "student name"]
STATUS_ALIASES = ["status", "attendance", "present/absent", "present_absent"]

STATUS_MAP = {
    "present": "present", "p": "present", "1": "present", "yes": "present", "true": "present",
    "absent": "absent", "a": "absent", "0": "absent", "no": "absent", "false": "absent",
}


def _find_column(columns, aliases):
    lower_map = {c.lower().strip(): c for c in columns}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


def _normalize_dataframe(df: pd.DataFrame):
    """
    Take a raw DataFrame (from CSV/JSON/PDF) and return a clean DataFrame with
    exactly columns: roll_no, name, status  — or raise a clear error if columns
    can't be found.
    """
    df.columns = [str(c).strip() for c in df.columns]

    roll_col = _find_column(df.columns, ROLL_NO_ALIASES)
    name_col = _find_column(df.columns, NAME_ALIASES)
    status_col = _find_column(df.columns, STATUS_ALIASES)

    missing = []
    if not roll_col:
        missing.append("roll number / enrollment number")
    if not status_col:
        missing.append("present/absent status")
    if missing:
        raise ValueError(
            f"Could not find a column for: {', '.join(missing)}. "
            f"Columns found in file: {list(df.columns)}"
        )

    clean = pd.DataFrame({
        "roll_no": df[roll_col].astype(str).str.strip(),
        "name": df[name_col].astype(str).str.strip() if name_col else "",
        "status_raw": df[status_col].astype(str).str.strip(),
    })

    # Normalize status values (Present/P/1/... -> "present" or "absent")
    clean["status"] = clean["status_raw"].str.lower().map(STATUS_MAP)

    return clean


def _parse_csv(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file, sep=None, engine="python", on_bad_lines="skip")
    except Exception:
        file.seek(0)
        return pd.read_csv(file, on_bad_lines="skip")


def _parse_json(file) -> pd.DataFrame:
    data = json.load(file)
    # Support both a flat list of records and {"records": [...]}
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    return pd.DataFrame(data)


def _parse_pdf(file) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "PDF support needs the 'pdfplumber' package. Install it with:\n"
            "    pip install pdfplumber"
        )

    all_rows = []
    header = None
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            if header is None:
                header = table[0]
                all_rows.extend(table[1:])
            else:
                # Skip repeated header rows on later pages, if present
                all_rows.extend(table[1:] if table[0] == header else table)

    if not header:
        raise ValueError(
            "No table could be detected in this PDF. This works for PDFs with a real "
            "table (like an exported attendance sheet) — not scanned/image-only PDFs."
        )

    return pd.DataFrame(all_rows, columns=header)


def run_admin_attendance_upload():
    render_admin_banner("Upload Attendance")
    st.markdown("""
    <div class="main-header">
        <h1>📤 Upload Attendance</h1>
        <p>Upload a class attendance sheet as CSV, JSON, or PDF</p>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Expected columns (names are flexible): **roll number / enrollment number**, "
        "**name** (optional), **status** (Present/Absent, P/A, or 1/0)."
    )

    c1, c2 = st.columns(2)
    subject = c1.text_input("Subject", placeholder="e.g. Business Communication")
    session_date = c2.date_input("Class date", value=date.today())

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "json", "pdf"])

    if not uploaded_file:
        return

    if not subject.strip():
        st.warning("Please enter the subject name before uploading.")
        return

    # Parse based on file type
    try:
        suffix = uploaded_file.name.split(".")[-1].lower()
        if suffix == "csv":
            raw_df = _parse_csv(uploaded_file)
        elif suffix == "json":
            raw_df = _parse_json(uploaded_file)
        elif suffix == "pdf":
            raw_df = _parse_pdf(BytesIO(uploaded_file.read()))
        else:
            st.error("Unsupported file type.")
            return
    except Exception as e:
        st.error(f"Couldn't read this file: {e}")
        return

    # Normalize into roll_no / name / status
    try:
        clean_df = _normalize_dataframe(raw_df)
    except ValueError as e:
        st.error(str(e))
        st.markdown("**Raw file preview** (so you can check the actual column names):")
        st.dataframe(raw_df.head(10), use_container_width=True)
        return

    # Flag any rows where status couldn't be understood
    bad_rows = clean_df[clean_df["status"].isna()]
    good_rows = clean_df[clean_df["status"].notna()]

    st.markdown(f"#### Preview — {subject} · {session_date.strftime('%d %b %Y')}")
    st.dataframe(good_rows[["roll_no", "name", "status"]], use_container_width=True)

    if not bad_rows.empty:
        st.warning(
            f"{len(bad_rows)} row(s) had a status value I couldn't understand and will be "
            f"skipped. Recognized values: Present/Absent, P/A, 1/0, Yes/No."
        )
        st.dataframe(bad_rows[["roll_no", "name", "status_raw"]], use_container_width=True)

    if good_rows.empty:
        st.error("No valid rows to save.")
        return

    st.info(f"Ready to save **{len(good_rows)}** student record(s) for this session.")

    if st.button("✅ Confirm and Save to Database", type="primary", use_container_width=True):
        saved = 0
        for _, row in good_rows.iterrows():
            db.record_attendance_session(
                roll_no=row["roll_no"],
                subject=subject.strip(),
                session_date=session_date.isoformat(),
                status=row["status"],
            )
            saved += 1
        st.success(f"Saved attendance for {saved} student(s). ✅")
        st.balloons()