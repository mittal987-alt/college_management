"""
student_upload.py — Admin page for uploading the student roster.

This links each student's roll number to their Google login email, so the
app can automatically look up "whose data is this" without the student
typing anything in.

Drop this file next to app.py, db.py, and admin_upload.py. Wire it in like:

    from student_upload import run_admin_student_upload
    ...
    if IS_ADMIN:
        mode_options.append("👥 Upload Students")
    ...
    elif mode == "👥 Upload Students":
        run_admin_student_upload()

Expected file columns (names are flexible, same idea as admin_upload.py):
    roll_no (or enrollment_no), name, email, programme (optional)
"""

import json
from io import BytesIO

import pandas as pd
import streamlit as st

import db
from ui_helpers import render_admin_banner

ROLL_NO_ALIASES = [
    "roll_no", "roll no", "rollno", "roll number",
    "enrollment_no", "enrollment no", "enrollmentno", "enroll_no", "enrollment number",
    "application_no", "application no", "applicationno", "application number",
    "app no", "app_no", "appl no", "reg no", "reg_no", "registration no", "registration number",
]
NAME_ALIASES = ["name", "student_name", "student name", "full name"]
EMAIL_ALIASES = ["email", "email address", "gmail", "college_email", "e-mail", "e mail"]
PROGRAMME_ALIASES = ["programme", "program", "course", "branch", "brach"]


def _find_column(columns, aliases):
    # Normalize: collapse embedded newlines/extra whitespace (common in PDF-extracted
    # headers like "APPLICATION\nNO.") down to single spaces before comparing.
    def _clean(c):
        return " ".join(str(c).replace("\n", " ").split()).lower().strip().rstrip(".")

    lower_map = {_clean(c): c for c in columns}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    # Fallback: partial match (e.g. "application no" inside "application no (unique)")
    for alias in aliases:
        for cleaned, original in lower_map.items():
            if alias in cleaned:
                return original
    return None


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]

    roll_col = _find_column(df.columns, ROLL_NO_ALIASES)
    name_col = _find_column(df.columns, NAME_ALIASES)
    email_col = _find_column(df.columns, EMAIL_ALIASES)
    programme_col = _find_column(df.columns, PROGRAMME_ALIASES)

    if not roll_col:
        raise ValueError(
            f"Could not find a column for roll number / enrollment / application number. "
            f"Columns found in file: {list(df.columns)}"
        )

    return pd.DataFrame({
        "roll_no": df[roll_col].astype(str).str.strip(),
        "name": df[name_col].astype(str).str.strip() if name_col else "",
        "email": df[email_col].astype(str).str.strip().str.lower() if email_col else "",
        "programme": df[programme_col].astype(str).str.strip() if programme_col else "",
    })


def _parse_csv(file) -> pd.DataFrame:
    # Try to auto-detect the delimiter (comma, semicolon, tab, pipe) instead of
    # assuming comma — many Excel exports (especially with regional settings)
    # use semicolons instead. Also skip rows that are genuinely malformed rather
    # than crashing the whole upload.
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


def run_admin_student_upload():
    render_admin_banner("Upload Students")
    st.markdown("""
    <div class="main-header">
        <h1>👥 Upload Students</h1>
        <p>Link each student's roll number to their login email (one-time setup, re-upload to add more)</p>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Expected columns (names are flexible): **roll number / enrollment number**, "
        "**email**, **name** (optional), **programme** (optional)."
    )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "json", "pdf"], key="student_roster_upload")
    if not uploaded_file:
        return

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

    try:
        clean_df = _normalize_dataframe(raw_df)
    except ValueError as e:
        st.error(str(e))
        st.markdown("**Raw file preview**:")
        st.dataframe(raw_df.head(10), use_container_width=True)
        return

    # Only roll number is strictly required now — email is optional (students without
    # one yet will self-link later from their own account).
    valid_mask = clean_df["roll_no"].str.strip() != ""
    good_rows = clean_df[valid_mask]
    bad_rows = clean_df[~valid_mask]

    has_emails = (clean_df["email"].str.contains("@", na=False)).any()

    st.markdown("#### Preview")
    st.dataframe(good_rows, use_container_width=True)

    if not has_emails:
        st.info(
            "ℹ️ No email column was found (or it's empty) — that's fine. These students will "
            "be saved with just their roll number, and can **link their own email** the first "
            "time they log in (they'll be prompted to enter their roll number)."
        )

    if not bad_rows.empty:
        st.warning(f"{len(bad_rows)} row(s) have a missing roll number and will be skipped.")
        st.dataframe(bad_rows, use_container_width=True)

    if good_rows.empty:
        st.error("No valid rows to save.")
        return

    st.info(f"Ready to save/update **{len(good_rows)}** student record(s).")

    if st.button("✅ Confirm and Save to Database", type="primary", use_container_width=True):
        saved = 0
        for _, row in good_rows.iterrows():
            db.save_student(
                roll_no=row["roll_no"],
                email=row["email"] if "@" in row["email"] else "",
                name=row["name"],
                programme=row["programme"],
            )
            saved += 1
        st.success(f"Saved {saved} student record(s). ✅")
        st.balloons()