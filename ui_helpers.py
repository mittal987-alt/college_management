"""
ui_helpers.py — small shared UI pieces used across multiple files
(app.py, admin_upload.py, student_upload.py, admin_data_upload.py).
"""

import streamlit as st


def render_admin_banner(page_name: str):
    """Colored banner shown at the top of every admin-only page, so it's visually
    unmistakable that you're in an admin-only area rather than a student-facing one."""
    st.markdown(
        f"""<div class="admin-banner"><span class="pill">Admin</span>
        <span class="label">{page_name} — visible only to administrators</span></div>""",
        unsafe_allow_html=True,
    )