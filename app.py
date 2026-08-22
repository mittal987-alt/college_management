"""
College Assistant — Streamlit app.

Two modes, one UI:
  1. College Assistant   - conditional RAG over academics_handbook.pdf / fee_structure.pdf,
                            PLUS live-data answers (attendance, eligibility, timetable) from
                            the SQLite database (db.py), for the logged-in student.
  2. Admin Dashboard     - usage stats, visible only to emails in ADMIN_EMAILS

Features:
  - Real token streaming (LangGraph `stream_mode="messages"`)
  - Source citations (PDF name + page number) for RAG answers
  - Live workflow graph visualization (mermaid -> PNG via mermaid.ink)
  - Google sign-in (Streamlit's native OIDC support)
  - Per-user chat history that persists across sessions (saved to disk, keyed by email)
  - Hindi / English response language toggle
  - 👍/👎 feedback on each answer, logged for the admin dashboard
  - Admin dashboard: most-asked questions, query volume by category, 👎 rate over time
  - Admin uploads: student roster + attendance data (CSV/JSON/PDF), stored in SQLite (db.py)
  - Chatbot can answer "what's my attendance", "am I eligible for exams", "what's my
    timetable today" using each student's real data, once admin has uploaded it and
    linked their roll number to their login email.

Requirements:
    pip install langgraph streamlit>=1.42.0 Authlib>=1.3.2 pandas pdfplumber

Environment (.env):
    GROQ_API_KEY=...
    ADMIN_EMAILS=admin1@college.edu,admin2@college.edu

Google sign-in setup (REQUIRED for this version to run):
    Create a `.streamlit/secrets.toml` file with:

        [auth]
        redirect_uri = "http://localhost:8501/oauth2callback"
        cookie_secret = "<a random secret string>"
        client_id = "<your Google OAuth client id>"
        client_secret = "<your Google OAuth client secret>"
        server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

    The client id/secret come from a Google Cloud OAuth "Web application" client
    (console.cloud.google.com -> APIs & Services -> Credentials). Add
    "<your-app-url>/oauth2callback" as an authorized redirect URI there too.
    Full walkthrough: https://docs.streamlit.io/develop/tutorials/authentication/google
"""

import os
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import TypedDict, Annotated

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from dotenv import load_dotenv

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import db
from admin_upload import run_admin_attendance_upload
from student_upload import run_admin_student_upload
from admin_data_upload import run_admin_timetable_upload, run_admin_calendar_upload
from ui_helpers import render_admin_banner

load_dotenv()

st.set_page_config(page_title="College Assistant", page_icon="🎓", layout="centered")

db.init_db()

# --------------------------------------------------------------------------------------
# Shared styling
# --------------------------------------------------------------------------------------
st.markdown("""
<style>
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

.main-header { text-align: center; padding: 1.5rem 0 1rem 0; }
.main-header h1 { font-size: 2.3rem; margin-bottom: 0.3rem; font-weight: 700; letter-spacing: -0.02em; }
.main-header p { color: #9a9aa5; font-size: 0.95rem; }

.query-badge {
    display: inline-block; padding: 3px 12px; border-radius: 999px;
    font-size: 0.7rem; font-weight: 700; margin-bottom: 6px; letter-spacing: 0.03em;
}
.badge-academic { background-color: #1f3a5f; color: #93c5fd; }
.badge-fee { background-color: #4a3110; color: #fcd34d; }
.badge-general { background-color: #1f4a2e; color: #86efac; }
.badge-attendance { background-color: #0f4a4a; color: #7dd3fc; }
.badge-eligibility { background-color: #4a1f3a; color: #f9a8d4; }
.badge-timetable { background-color: #3a2f0f; color: #fde68a; }

.source-chip {
    display: inline-block; padding: 2px 10px; margin: 2px 4px 2px 0;
    border-radius: 8px; font-size: 0.72rem; background-color: #262730; color: #b0b0b0;
    border: 1px solid #3a3a3a;
}

/* Distinct visual identity for admin-only pages, so it's unmistakable you're in admin mode */
.admin-banner {
    display: flex; align-items: center; gap: 10px;
    background: linear-gradient(90deg, rgba(124,92,252,0.18), rgba(124,92,252,0.04));
    border: 1px solid rgba(124,92,252,0.35);
    border-radius: 12px; padding: 10px 18px; margin-bottom: 1.2rem;
}
.admin-banner .pill {
    background: #7C5CFC; color: white; font-size: 0.68rem; font-weight: 800;
    letter-spacing: 0.08em; padding: 3px 10px; border-radius: 999px; text-transform: uppercase;
}
.admin-banner span.label { color: #c9bfff; font-size: 0.85rem; }

/* Sidebar polish */
section[data-testid="stSidebar"] button { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)




# ========================================================================================
# Persistence — simple JSON-file storage (swap for a real DB at scale)
# ========================================================================================
DATA_DIR = Path("data")
HISTORY_DIR = DATA_DIR / "chat_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
INTERACTIONS_LOG = DATA_DIR / "interactions.jsonl"
FEEDBACK_LOG = DATA_DIR / "feedback.jsonl"


def _safe_user_key(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:16]


def _user_history_dir(email: str) -> Path:
    d = HISTORY_DIR / _safe_user_key(email)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_conversations(email: str):
    """Return this user's past conversations as a list of {id, title, created_at}, newest first."""
    convs = []
    for f in _user_history_dir(email).glob("*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            if payload.get("display_messages"):  # skip empty/never-used conversations
                convs.append({
                    "id": f.stem,
                    "title": payload.get("title") or "New chat",
                    "created_at": payload.get("created_at", ""),
                })
        except Exception:
            continue
    convs.sort(key=lambda c: c["created_at"], reverse=True)
    return convs


def load_conversation(email: str, conv_id: str):
    """Returns (display_messages, lc_messages, title) for one conversation, or empty defaults if new."""
    path = _user_history_dir(email) / f"{conv_id}.json"
    if not path.exists():
        return [], [], "New chat"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        display_messages = payload.get("display_messages", [])
        lc_messages = [tuple(m) for m in payload.get("lc_messages", [])]
        title = payload.get("title") or "New chat"
        return display_messages, lc_messages, title
    except Exception:
        return [], [], "New chat"


def save_conversation(email: str, conv_id: str, title: str, display_messages: list, lc_messages: list):
    path = _user_history_dir(email) / f"{conv_id}.json"
    serial_lc = []
    for m in lc_messages:
        if isinstance(m, tuple):
            role, content = m
        else:
            role, content = getattr(m, "type", "human"), getattr(m, "content", "")
        serial_lc.append([role, content])

    created_at = None
    if path.exists():
        try:
            created_at = json.loads(path.read_text(encoding="utf-8")).get("created_at")
        except Exception:
            pass
    created_at = created_at or datetime.utcnow().isoformat()

    payload = {
        "title": title, "created_at": created_at,
        "display_messages": display_messages, "lc_messages": serial_lc,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_title_from_message(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "New chat"
    return text[:40] + ("…" if len(text) > 40 else "")


def log_interaction(user_email: str, mode: str, query: str, query_type: str, language: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_email, "mode": mode, "query": query,
        "query_type": query_type, "language": language,
    }
    with open(INTERACTIONS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def log_feedback(user_email: str, query: str, feedback: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_email, "query": query, "feedback": feedback,
    }
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _load_jsonl_df(path: Path, columns: list) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=columns)


def load_interactions_df() -> pd.DataFrame:
    return _load_jsonl_df(INTERACTIONS_LOG, ["timestamp", "user", "mode", "query", "query_type", "language"])


def load_feedback_df() -> pd.DataFrame:
    return _load_jsonl_df(FEEDBACK_LOG, ["timestamp", "user", "query", "feedback"])


# ========================================================================================
# Google sign-in (Streamlit native OIDC — see setup notes in the module docstring)
# ========================================================================================
def login_screen():
    st.markdown("""
    <div class="main-header">
        <h1>🎓 College AI Assistant</h1>
        <p>Please sign in with your college Google account to continue</p>
    </div>
    """, unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1, 1])
    with center:
        st.button("Log in with Google", on_click=st.login, type="primary", use_container_width=True)


if not st.user.is_logged_in:
    login_screen()
    st.stop()

USER_EMAIL = st.user.email
USER_NAME = st.user.get("name", USER_EMAIL)
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
IS_ADMIN = USER_EMAIL.lower() in ADMIN_EMAILS


# ========================================================================================
# Shared resources (cached once per process)
# ========================================================================================
@st.cache_resource(show_spinner="Loading knowledge base...")
def load_rag_resources():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def build_retriever(pdf_path: str):
        loader = PyPDFLoader(pdf_path)
        document = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_documents(document)
        vectorstore = FAISS.from_documents(chunks, embeddings)
        return vectorstore.as_retriever(search_kwargs={"k": 4})

    academic_retriever = build_retriever("academics_handbook.pdf")
    fee_retriever = build_retriever("fee_structure.pdf")
    return academic_retriever, fee_retriever


@st.cache_resource(show_spinner=False)
def load_llms():
    return {
        "groq_classifier": ChatGroq(model="openai/gpt-oss-120b", temperature=0.4),
    }


academic_retriever, fee_retriever = load_rag_resources()
llms = load_llms()


def render_roll_no_linker():
    """
    Shows a small form letting the logged-in student link their own roll number,
    if they aren't linked yet. Safe to call from any page — does nothing if the
    student is already linked. Returns True if linked (before or after this call).
    """
    existing_roll_no = db.get_roll_no_by_email(USER_EMAIL)
    if existing_roll_no:
        return True

    with st.expander("🔗 Link your roll number (one-time)", expanded=True):
        st.caption(
            "Your account isn't linked to a roll number yet. Enter the roll number / "
            "enrollment number / application number your college gave you — this only "
            "needs to be done once."
        )
        roll_no_input = st.text_input("Your roll / enrollment / application number", key="self_link_roll_no")
        if st.button("Link my account", key="self_link_button"):
            if not roll_no_input.strip():
                st.warning("Please enter your roll number.")
            else:
                success, message = db.link_student_email(roll_no_input.strip(), USER_EMAIL)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    return False


def render_graph(app, key: str):
    """Render a compiled LangGraph's structure as a diagram (mermaid.ink PNG, with text fallback)."""
    with st.expander("🗺️ View workflow graph"):
        try:
            png_bytes = app.get_graph().draw_mermaid_png()
            st.image(png_bytes, use_container_width=True)
        except Exception:
            st.caption("Diagram render unavailable (needs internet access to mermaid.ink). Raw graph:")
            st.code(app.get_graph().draw_mermaid(), language="text")


# ========================================================================================
# MODE 1 — College Assistant (conditional RAG + live student data)
# ========================================================================================
class CollegeState(TypedDict):
    programme: str
    user_email: str
    messages: Annotated[list, add_messages]
    query_type: str
    retrieved_context: str
    sources: list


def classifier_node(state: CollegeState) -> dict:
    last_message = state["messages"][-1].content
    prompt = (
        "Classify the following student query into exactly one category: "
        "'academic', 'fee', 'attendance', 'eligibility', 'timetable', or 'general'.\n\n"
        "Use 'academic' for questions about COLLEGE RULES/POLICY around exams, grading, "
        "credits, promotion, course structure, summer training, or degree requirements "
        "(e.g. 'what is the minimum attendance policy', 'how are grades calculated').\n"
        "Use 'fee' for questions about tuition, payment, refund, late charges, "
        "scholarships, or any money-related topic.\n"
        "Use 'attendance' for questions asking about the STUDENT'S OWN attendance record "
        "(e.g. 'what is my attendance', 'how many classes have I missed in DBMS').\n"
        "Use 'eligibility' for questions asking whether the STUDENT is personally eligible "
        "to sit for exams (e.g. 'am I eligible for exams', 'can I appear for finals').\n"
        "Use 'timetable' for questions about the STUDENT'S class schedule "
        "(e.g. 'what classes do I have today', 'when is my next class').\n"
        "Use 'general' for greetings, casual talk, or anything else.\n\n"
        f"Query: {last_message}\n\n"
        "Return only one word: academic, fee, attendance, eligibility, timetable, or general."
    )
    response = llms["groq_classifier"].invoke(prompt)
    category = response.content.strip().lower()
    valid = ["academic", "fee", "attendance", "eligibility", "timetable", "general"]
    category = next((c for c in valid if c in category), "general")
    return {"query_type": category}


def _retrieve_with_sources(retriever, query: str, source_label: str):
    docs = retriever.invoke(query)
    context = "\n\n".join(doc.page_content for doc in docs)
    sources = [
        {"label": source_label, "page": doc.metadata.get("page", "?")}
        for doc in docs
    ]
    return context, sources


def academic_rag_node(state: CollegeState) -> dict:
    query = state["messages"][-1].content
    context, sources = _retrieve_with_sources(academic_retriever, query, "Academics Handbook")
    return {"retrieved_context": context, "sources": sources}


def fee_rag_node(state: CollegeState) -> dict:
    query = state["messages"][-1].content
    context, sources = _retrieve_with_sources(fee_retriever, query, "Fee Structure")
    return {"retrieved_context": context, "sources": sources}


def general_node(state: CollegeState) -> dict:
    return {"retrieved_context": "NO_RETRIEVAL_NEEDED", "sources": []}


def attendance_node(state: CollegeState) -> dict:
    """Pulls the logged-in student's real attendance from the database."""
    report = db.get_student_attendance_report(state["user_email"])

    if not report.get("linked"):
        context = report["message"]
    elif "subjects" not in report:
        context = report["message"]
    else:
        lines = [
            f"Required attendance to be eligible: {report['required_pct']:.0f}%",
            f"Overall attendance: {report['overall_pct']:.1f}% "
            f"({'meets' if report['overall_eligible'] else 'does NOT meet'} the requirement)",
            "",
            "Subject-wise attendance:",
        ]
        for s in report["subjects"]:
            status = "OK" if s["eligible"] else "BELOW REQUIREMENT"
            lines.append(f"- {s['subject']}: {s['attended']}/{s['held']} classes = {s['pct']:.1f}% [{status}]")
        context = "\n".join(lines)

    return {"retrieved_context": context, "sources": [{"label": "Live attendance records", "page": "—"}]}


def eligibility_node(state: CollegeState) -> dict:
    """Checks the logged-in student's exam eligibility from real attendance + marks data."""
    report = db.get_student_eligibility_report(state["user_email"])

    if not report.get("linked"):
        context = report["message"]
    elif "subjects" not in report:
        context = report["message"]
    else:
        lines = [
            f"Required attendance: {report['required_attendance_pct']:.0f}% · "
            f"Required internal marks: {report['required_internal_pct']:.0f}%",
            f"Overall: {'ELIGIBLE for all subjects' if report['all_eligible'] else 'NOT eligible for at least one subject'}",
            "",
            "Subject-wise breakdown:",
        ]
        for s in report["subjects"]:
            marks_text = f"{s['internal_marks_pct']}%" if s["internal_marks_pct"] is not None else "no marks recorded"
            status = "ELIGIBLE" if s["eligible"] else "NOT ELIGIBLE"
            lines.append(
                f"- {s['subject']}: attendance {s['attendance_pct']:.1f}%, internals {marks_text} [{status}]"
            )
        context = "\n".join(lines)

    return {"retrieved_context": context, "sources": [{"label": "Live attendance & marks records", "page": "—"}]}


TIMETABLE_PATH_FOR_CHAT = Path("data") / "timetable.json"


def timetable_node(state: CollegeState) -> dict:
    """Reads today's (or the student's) schedule for their programme from timetable.json."""
    programme = state.get("programme", "Unknown")

    if not TIMETABLE_PATH_FOR_CHAT.exists():
        return {"retrieved_context": "No timetable data has been uploaded yet.", "sources": []}

    timetable = json.loads(TIMETABLE_PATH_FOR_CHAT.read_text(encoding="utf-8-sig"))
    today_name = date.today().strftime("%A")
    slots = timetable.get(programme, {}).get(today_name, [])

    if not slots:
        context = f"No timetable found for {programme} on {today_name}."
    else:
        lines = [f"{programme} schedule for today ({today_name}):"]
        for slot in slots:
            if slot["subject"] == "LUNCH BREAK":
                lines.append(f"- {slot['time']}: Lunch break")
                continue
            room = f", Room {slot['room']}" if slot.get("room") else ""
            teacher = f", {slot['teacher']}" if slot.get("teacher") else ""
            lines.append(f"- {slot['time']}: {slot['subject']}{room}{teacher}")
        context = "\n".join(lines)

    return {"retrieved_context": context, "sources": [{"label": "Timetable", "page": today_name}]}


def response_node(state: CollegeState) -> dict:
    query = state["messages"][-1].content
    programme = state.get("programme", "Unknown")
    context = state["retrieved_context"]

    language = st.session_state.get("language", "English")
    language_instruction = (
        "Respond entirely in Hindi (Devanagari script), even though the source "
        "documents and question may be in English."
        if language == "Hindi" else
        "Respond in English."
    )

    if context == "NO_RETRIEVAL_NEEDED":
        prompt = (
            f"You are a friendly college assistant talking to a {programme} student. "
            f"{language_instruction}\n"
            f"Answer this question using your own general knowledge:\n\n{query}"
        )
    else:
        prompt = (
            f"You are a college assistant helping a {programme} student. "
            f"{language_instruction}\n"
            f"Use the following information to answer the question accurately and personally "
            f"(this may be official document content, or the student's own live records — either "
            f"way, treat it as ground truth and don't contradict it).\n\n"
            f"Information:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Give a clear, friendly, and precise answer."
        )
    # Streamed via graph stream_mode="messages" when invoked from the UI.
    response = llms["groq_classifier"].invoke(prompt)
    return {"messages": [("ai", response.content.strip())]}


def route_query(state: CollegeState):
    return {
        "academic": "academic_rag",
        "fee": "fee_rag",
        "attendance": "attendance",
        "eligibility": "eligibility",
        "timetable": "timetable",
    }.get(state["query_type"], "general")


@st.cache_resource(show_spinner=False)
def build_college_graph():
    graph = StateGraph(CollegeState)
    graph.add_node("classifier", classifier_node)
    graph.add_node("academic_rag", academic_rag_node)
    graph.add_node("fee_rag", fee_rag_node)
    graph.add_node("general", general_node)
    graph.add_node("attendance", attendance_node)
    graph.add_node("eligibility", eligibility_node)
    graph.add_node("timetable", timetable_node)
    graph.add_node("response", response_node)

    graph.add_edge(START, "classifier")
    graph.add_conditional_edges(
        "classifier", route_query,
        {
            "academic_rag": "academic_rag", "fee_rag": "fee_rag", "general": "general",
            "attendance": "attendance", "eligibility": "eligibility", "timetable": "timetable",
        },
    )
    graph.add_edge("academic_rag", "response")
    graph.add_edge("fee_rag", "response")
    graph.add_edge("general", "response")
    graph.add_edge("attendance", "response")
    graph.add_edge("eligibility", "response")
    graph.add_edge("timetable", "response")
    graph.add_edge("response", END)
    return graph.compile()


def _set_feedback(idx: int, value: str):
    msgs = st.session_state.college_messages
    if 0 <= idx < len(msgs):
        msgs[idx]["feedback"] = value
        log_feedback(USER_EMAIL, msgs[idx].get("query", ""), value)
        save_conversation(
            USER_EMAIL,
            st.session_state.college_conversation_id,
            st.session_state.get("college_title", "New chat"),
            st.session_state.college_messages,
            st.session_state.college_lc_messages,
        )


def run_college_mode():
    app = build_college_graph()

    st.markdown("""
    <div class="main-header">
        <h1>🎓 College Assistant</h1>
        <p>Ask me about academics, fees, your attendance, eligibility, timetable, or anything else campus-related</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Setup")
        programme_map = {"BCA": "BCA", "BBA": "BBA", "B.Com (H)": "B.Com (H)"}
        student_programme = st.selectbox("Select your programme", options=list(programme_map.keys()))
        st.caption(f"📌 Currently set as: **{student_programme}** student")

        if st.button("🆕 New Chat", use_container_width=True, key="college_new_chat"):
            st.session_state.college_conversation_id = uuid.uuid4().hex[:12]
            st.session_state.college_messages = []
            st.session_state.college_lc_messages = []
            st.session_state.college_title = "New chat"
            st.rerun()

        st.markdown("#### 🕘 Recent chats")
        past_conversations = list_conversations(USER_EMAIL)
        if not past_conversations:
            st.caption("No past chats yet.")
        for conv in past_conversations[:20]:
            is_active = conv["id"] == st.session_state.get("college_conversation_id")
            label = ("🟢 " if is_active else "") + conv["title"]
            if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                if not is_active:
                    dm, lcm, title = load_conversation(USER_EMAIL, conv["id"])
                    st.session_state.college_conversation_id = conv["id"]
                    st.session_state.college_messages = dm
                    st.session_state.college_lc_messages = lcm
                    st.session_state.college_title = title
                    st.rerun()

        render_graph(app, "college")

    if "college_conversation_id" not in st.session_state:
        # First visit this session: start a fresh, unsaved conversation.
        st.session_state.college_conversation_id = uuid.uuid4().hex[:12]
        st.session_state.college_messages = []
        st.session_state.college_lc_messages = []
        st.session_state.college_title = "New chat"

    if not st.session_state.college_messages:
        st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)
        suggestions = [
            "📊 What's my attendance?",
            "🔔 Am I eligible for exams?",
            "🗓️ What classes do I have today?",
            "💰 What's the fee refund policy?",
        ]
        cols = st.columns(len(suggestions))
        clicked_suggestion = None
        for col, text in zip(cols, suggestions):
            with col:
                if st.button(text, use_container_width=True, key=f"suggest_{text}"):
                    clicked_suggestion = text.split(" ", 1)[1]  # drop the emoji
        if clicked_suggestion:
            st.session_state.college_pending_query = clicked_suggestion

    for i, msg in enumerate(st.session_state.college_messages):
        avatar = "🧑‍🎓" if msg["role"] == "user" else "🎓"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant" and msg.get("query_type"):
                badge_class = f"badge-{msg['query_type']}"
                st.markdown(
                    f'<span class="query-badge {badge_class}">{msg["query_type"].upper()}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown(msg["content"])
            if msg.get("sources"):
                chips = "".join(
                    f'<span class="source-chip">📄 {s["label"]} · p.{s["page"]}</span>'
                    for s in msg["sources"]
                )
                st.markdown(chips, unsafe_allow_html=True)
            if msg["role"] == "assistant":
                fb = msg.get("feedback")
                c1, c2, _ = st.columns([1, 1, 10])
                with c1:
                    st.button(
                        "👍" if fb != "up" else "✅",
                        key=f"fb_up_{i}", help="Helpful",
                        on_click=_set_feedback, args=(i, "up"),
                    )
                with c2:
                    st.button(
                        "👎" if fb != "down" else "✅",
                        key=f"fb_down_{i}", help="Not helpful",
                        on_click=_set_feedback, args=(i, "down"),
                    )

    user_query = st.chat_input("Type your question here...")
    if st.session_state.get("college_pending_query"):
        user_query = st.session_state.pop("college_pending_query")
    if not user_query:
        return

    st.session_state.college_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(user_query)

    st.session_state.college_lc_messages.append(("human", user_query))

    with st.chat_message("assistant", avatar="🎓"):
        badge_slot = st.empty()
        text_slot = st.empty()

        def token_stream():
            """Consume the graph's token stream, yielding only text from the response node."""
            full = {"text": ""}
            for chunk, metadata in app.stream(
                {
                    "programme": student_programme,
                    "user_email": USER_EMAIL,
                    "messages": st.session_state.college_lc_messages,
                },
                stream_mode="messages",
            ):
                if metadata.get("langgraph_node") == "response" and getattr(chunk, "content", None):
                    full["text"] += chunk.content
                    yield chunk.content
            token_stream.final_text = full["text"]

        streamed_text = st.write_stream(token_stream())

        # Re-run a plain invoke to reliably capture final structured state
        # (query_type, sources, updated messages) alongside the streamed text.
        result = app.invoke({
            "programme": student_programme,
            "user_email": USER_EMAIL,
            "messages": st.session_state.college_lc_messages,
        })

        query_type = result.get("query_type", "general")
        sources = result.get("sources", [])
        badge_class = f"badge-{query_type}"
        badge_slot.markdown(
            f'<span class="query-badge {badge_class}">{query_type.upper()}</span>',
            unsafe_allow_html=True,
        )
        if sources:
            chips = "".join(
                f'<span class="source-chip">📄 {s["label"]} · p.{s["page"]}</span>' for s in sources
            )
            st.markdown(chips, unsafe_allow_html=True)

    ai_text = result["messages"][-1].content
    st.session_state.college_lc_messages = result["messages"]
    st.session_state.college_messages.append({
        "role": "assistant", "content": ai_text, "query_type": query_type, "sources": sources,
        "query": user_query, "feedback": None,
    })

    language = st.session_state.get("language", "English")
    log_interaction(USER_EMAIL, "college", user_query, query_type, language)

    if st.session_state.get("college_title", "New chat") == "New chat":
        st.session_state.college_title = make_title_from_message(user_query)

    save_conversation(
        USER_EMAIL,
        st.session_state.college_conversation_id,
        st.session_state.college_title,
        st.session_state.college_messages,
        st.session_state.college_lc_messages,
    )
    st.rerun()  # re-render so the new message shows its feedback buttons


# ========================================================================================
# MODE 2 — Academic Calendar
# ========================================================================================
CALENDAR_PATH = DATA_DIR / "academic_calendar.json"

TYPE_CONFIG = {
    "exam":     {"emoji": "📝", "color": "#ef4444", "label": "Exam"},
    "holiday":  {"emoji": "🏖️", "color": "#22c55e", "label": "Holiday"},
    "deadline": {"emoji": "⏰", "color": "#f97316", "label": "Deadline"},
    "event":    {"emoji": "🎉", "color": "#8b5cf6", "label": "Event"},
}


def run_calendar_mode():
    st.markdown("""
    <div class="main-header">
        <h1>📅 Academic Calendar</h1>
        <p>Upcoming exams, holidays, deadlines and college events</p>
    </div>
    """, unsafe_allow_html=True)

    if not CALENDAR_PATH.exists():
        st.error("academic_calendar.json not found in data/ directory.")
        return

    events = json.loads(CALENDAR_PATH.read_text(encoding="utf-8-sig"))
    today = date.today()

    # Sidebar filters
    with st.sidebar:
        st.markdown("### 🔍 Filter")
        show_types = []
        for t, cfg in TYPE_CONFIG.items():
            if st.checkbox(f"{cfg['emoji']} {cfg['label']}", value=True, key=f"cal_{t}"):
                show_types.append(t)
        show_past = st.checkbox("Show past events", value=False, key="cal_past")

    # Build dataframe
    rows = []
    for e in events:
        ev_date = date.fromisoformat(e["date"])
        if e["type"] not in show_types:
            continue
        if not show_past and ev_date < today:
            continue
        days_away = (ev_date - today).days
        rows.append({"Date": ev_date, "Event": e["title"], "Type": e["type"], "days_away": days_away})

    if not rows:
        st.info("No events match your filters.")
        return

    rows.sort(key=lambda x: x["Date"])

    # Next-7-days highlight
    upcoming = [r for r in rows if 0 <= r["days_away"] <= 7]
    if upcoming:
        st.markdown("#### 🔔 Next 7 Days")
        for r in upcoming:
            cfg = TYPE_CONFIG[r["Type"]]
            label = "Today!" if r["days_away"] == 0 else (f"Tomorrow" if r["days_away"] == 1 else f"In {r['days_away']} days")
            st.markdown(
                f"""<div style='border-left:4px solid {cfg['color']};padding:8px 12px;margin:4px 0;
                background:rgba(0,0,0,0.2);border-radius:4px;'>
                <b>{cfg['emoji']} {r['Event']}</b><br>
                <small style='color:#aaa;'>{r['Date'].strftime('%d %b %Y')} &nbsp;·&nbsp;
                <span style='color:{cfg['color']};'>{label}</span></small></div>""",
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # Full calendar table
    st.markdown("#### 📋 All Upcoming Events")
    for r in rows:
        cfg = TYPE_CONFIG[r["Type"]]
        days_text = (
            "Today" if r["days_away"] == 0
            else f"{r['days_away']} days away" if r["days_away"] > 0
            else f"{abs(r['days_away'])} days ago"
        )
        col1, col2, col3 = st.columns([2, 5, 2])
        col1.markdown(f"**{r['Date'].strftime('%d %b')}**")
        col2.markdown(f"{cfg['emoji']} {r['Event']}")
        col3.markdown(f"<small style='color:{cfg['color']};'>{days_text}</small>", unsafe_allow_html=True)


# ========================================================================================
# MODE 3 — Attendance Tracker (now auto-populated from the database when linked)
# ========================================================================================
def run_attendance_mode():
    st.markdown("""
    <div class="main-header">
        <h1>📊 Attendance Tracker</h1>
        <p>Check your subject-wise attendance and eligibility to sit for exams</p>
    </div>
    """, unsafe_allow_html=True)

    report = db.get_student_attendance_report(USER_EMAIL)

    if not report.get("linked"):
        render_roll_no_linker()
        st.caption("Once linked, your real attendance will show here automatically. Meanwhile, you can enter it manually below.")
        _run_manual_attendance_entry()
        return

    if "subjects" not in report:
        st.info(f"You're linked as roll number **{report['roll_no']}**, but " + report["message"])
        _run_manual_attendance_entry()
        return

    required_pct = report["required_pct"]
    st.caption(f"Showing live data for roll number **{report['roll_no']}** · required attendance: **{required_pct:.0f}%**")

    col1, col2, col3 = st.columns(3)
    total_held = sum(s["held"] for s in report["subjects"])
    total_attended = sum(s["attended"] for s in report["subjects"])
    col1.metric("Total Classes Held", total_held)
    col2.metric("Total Attended", total_attended)
    status_color = "normal" if report["overall_eligible"] else "inverse"
    col3.metric(
        "Overall Attendance", f"{report['overall_pct']:.1f}%",
        delta=f"{report['overall_pct'] - required_pct:+.1f}% vs required", delta_color=status_color,
    )

    st.markdown("#### 📋 Subject-wise Breakdown")
    for s in report["subjects"]:
        color = "#22c55e" if s["eligible"] else "#ef4444"
        icon = "✅" if s["eligible"] else "❌"
        st.markdown(
            f"""<div style='border-left:4px solid {color};padding:8px 14px;margin:6px 0;
            background:rgba(0,0,0,0.2);border-radius:4px;'>
            <b>{icon} {s['subject']}</b> &nbsp;
            <span style='color:{color};font-size:1.1rem;font-weight:700;'>{s['pct']:.1f}%</span>
            <span style='color:#aaa;font-size:0.85rem;'> ({s['attended']}/{s['held']} classes)</span>
            </div>""",
            unsafe_allow_html=True,
        )

    chart_data = pd.DataFrame(
        {"Attendance %": [s["pct"] for s in report["subjects"]]},
        index=[s["subject"] for s in report["subjects"]],
    )
    st.markdown("#### 📈 Attendance Chart")
    st.bar_chart(chart_data)


def _run_manual_attendance_entry():
    """Fallback: the original manual-entry form, for students not yet linked in the database."""
    REQUIRED_PCT = 75.0

    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        n_subjects = st.number_input("Number of subjects", min_value=1, max_value=12, value=5, step=1, key="att_n")
        required_pct = st.number_input("Required attendance %", min_value=50, max_value=100, value=75, step=1, key="att_req")
        REQUIRED_PCT = float(required_pct)

    st.markdown("#### Enter your attendance details")
    st.caption("Fill in the total classes held and classes you attended for each subject.")

    subjects = []
    cols_header = st.columns([3, 2, 2])
    cols_header[0].markdown("**Subject Name**")
    cols_header[1].markdown("**Classes Held**")
    cols_header[2].markdown("**Classes Attended**")

    for i in range(int(n_subjects)):
        c1, c2, c3 = st.columns([3, 2, 2])
        name = c1.text_input(f"Subject {i+1}", key=f"att_name_{i}", label_visibility="collapsed",
                             placeholder=f"Subject {i+1}")
        held = c2.number_input("Held", min_value=0, max_value=500, value=0, key=f"att_held_{i}",
                               label_visibility="collapsed")
        attended = c3.number_input("Attended", min_value=0, max_value=500, value=0, key=f"att_att_{i}",
                                   label_visibility="collapsed")
        subjects.append({"name": name or f"Subject {i+1}", "held": held, "attended": attended})

    if st.button("Calculate Attendance", type="primary", key="att_calc"):
        st.markdown("---")
        total_held = sum(s["held"] for s in subjects)
        total_attended = sum(s["attended"] for s in subjects)
        overall_pct = (total_attended / total_held * 100) if total_held > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Classes Held", total_held)
        col2.metric("Total Attended", total_attended)
        status_color = "normal" if overall_pct >= REQUIRED_PCT else "inverse"
        col3.metric("Overall Attendance", f"{overall_pct:.1f}%", delta=f"{overall_pct - REQUIRED_PCT:+.1f}% vs required",
                    delta_color=status_color)

        st.markdown("#### 📋 Subject-wise Breakdown")
        for s in subjects:
            pct = (s["attended"] / s["held"] * 100) if s["held"] > 0 else 0.0
            eligible = pct >= REQUIRED_PCT
            color = "#22c55e" if eligible else "#ef4444"
            icon = "✅" if eligible else "❌"

            extra = ""
            if not eligible and s["held"] > 0:
                needed = 0
                while ((s["attended"] + needed) / (s["held"] + needed) * 100) < REQUIRED_PCT:
                    needed += 1
                    if needed > 500:
                        break
                extra = f" — Need <b>{needed}</b> more consecutive classes to reach {REQUIRED_PCT:.0f}%"

            st.markdown(
                f"""<div style='border-left:4px solid {color};padding:8px 14px;margin:6px 0;
                background:rgba(0,0,0,0.2);border-radius:4px;'>
                <b>{icon} {s['name']}</b> &nbsp;
                <span style='color:{color};font-size:1.1rem;font-weight:700;'>{pct:.1f}%</span>
                <span style='color:#aaa;font-size:0.85rem;'> ({s['attended']}/{s['held']} classes){extra}</span>
                </div>""",
                unsafe_allow_html=True,
            )

        chart_data = pd.DataFrame(
            {"Attendance %": [((s["attended"] / s["held"] * 100) if s["held"] > 0 else 0.0) for s in subjects]},
            index=[s["name"] for s in subjects],
        )
        st.markdown("#### 📈 Attendance Chart")
        st.bar_chart(chart_data)


# ========================================================================================
# MODE 4 — CGPA Calculator
# ========================================================================================
GRADE_SCALE = {
    "O  (91-100)": 10, "A+ (81-90)": 9, "A  (71-80)": 8,
    "B+ (61-70)": 7,  "B  (51-60)": 6, "C  (41-50)": 5, "F  (0-40)": 0,
}


def run_cgpa_mode():
    st.markdown("""
    <div class="main-header">
        <h1>🧮 CGPA Calculator</h1>
        <p>Calculate your semester GPA and cumulative CGPA using the 10-point grading scale</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        n_sems = st.number_input("Number of semesters", min_value=1, max_value=8, value=1, step=1, key="cgpa_nsem")
        n_subjects = st.number_input("Subjects per semester", min_value=1, max_value=10, value=5, step=1, key="cgpa_nsub")

    st.markdown("#### Enter your grades")
    all_sem_data = []

    for sem in range(int(n_sems)):
        st.markdown(f"**Semester {sem + 1}**")
        h1, h2, h3 = st.columns([3, 1, 2])
        h1.caption("Subject")
        h2.caption("Credits")
        h3.caption("Grade")
        sem_subjects = []
        for sub in range(int(n_subjects)):
            c1, c2, c3 = st.columns([3, 1, 2])
            name = c1.text_input("Sub", key=f"cgpa_name_{sem}_{sub}", label_visibility="collapsed",
                                  placeholder=f"Subject {sub+1}")
            credits = c2.number_input("Cr", min_value=1, max_value=6, value=4, key=f"cgpa_cr_{sem}_{sub}",
                                       label_visibility="collapsed")
            grade = c3.selectbox("Gr", list(GRADE_SCALE.keys()), key=f"cgpa_gr_{sem}_{sub}",
                                  label_visibility="collapsed")
            sem_subjects.append({"name": name or f"Sub {sub+1}", "credits": credits, "grade": grade})
        all_sem_data.append(sem_subjects)
        st.markdown("")

    if st.button("Calculate CGPA", type="primary", key="cgpa_calc"):
        st.markdown("---")
        sgpas = []
        total_credits_all = 0
        total_weighted_all = 0.0

        for sem_idx, sem_subjects in enumerate(all_sem_data):
            total_credits = sum(s["credits"] for s in sem_subjects)
            weighted = sum(s["credits"] * GRADE_SCALE[s["grade"]] for s in sem_subjects)
            sgpa = weighted / total_credits if total_credits > 0 else 0.0
            sgpas.append(sgpa)
            total_credits_all += total_credits
            total_weighted_all += weighted
            st.markdown(
                f"**Semester {sem_idx+1} SGPA: "
                f"<span style='color:#60a5fa;font-size:1.2rem;'>{sgpa:.2f}</span>**",
                unsafe_allow_html=True,
            )
            rows = [{"Subject": s["name"], "Credits": s["credits"], "Grade": s["grade"],
                     "Points": GRADE_SCALE[s["grade"]]} for s in sem_subjects]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        cgpa = total_weighted_all / total_credits_all if total_credits_all > 0 else 0.0
        cgpa_color = "#22c55e" if cgpa >= 7 else ("#f97316" if cgpa >= 5 else "#ef4444")
        st.markdown(
            f"<h2 style='text-align:center;'>🎓 Your CGPA: "
            f"<span style='color:{cgpa_color};'>{cgpa:.2f}</span> / 10.00</h2>",
            unsafe_allow_html=True,
        )
        if len(sgpas) > 1:
            st.markdown("#### 📈 SGPA Trend")
            st.bar_chart(pd.DataFrame({"SGPA": sgpas},
                                       index=[f"Sem {i+1}" for i in range(len(sgpas))]))


# ========================================================================================
# MODE 5 — Leave Application Generator
# ========================================================================================
def run_leave_mode():
    st.markdown("""
    <div class="main-header">
        <h1>📝 Leave Application Generator</h1>
        <p>Generate a formal leave application letter for your HOD in seconds</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("leave_form"):
        c1, c2 = st.columns(2)
        student_name = c1.text_input("Full Name", placeholder="Rahul Kumar")
        roll_no = c2.text_input("Roll Number", placeholder="BCA/2024/001")

        c3, c4 = st.columns(2)
        programme = c3.selectbox("Programme", ["BCA", "BBA", "B.Com (H)"])
        semester = c4.selectbox("Semester", ["1st", "2nd", "3rd", "4th", "5th", "6th"])

        c5, c6 = st.columns(2)
        from_date = c5.date_input("Leave From", value=date.today())
        to_date = c6.date_input("Leave Till", value=date.today())

        reason = st.text_area("Reason for Leave", placeholder="e.g. I am suffering from high fever and have been advised rest by the doctor for 3 days.", height=100)
        hod_name = st.text_input("HOD's Name (optional)", placeholder="Dr. Sharma")
        submitted = st.form_submit_button("Generate Application", type="primary", use_container_width=True)

    if submitted:
        if not student_name.strip() or not reason.strip():
            st.warning("Please fill in your name and reason for leave.")
            return

        days = (to_date - from_date).days + 1
        hod_line = f"The HOD, {hod_name}," if hod_name.strip() else "The Head of Department,"

        prompt = (
            f"Write a formal leave application letter from a college student with these details:\n"
            f"Student Name: {student_name}\n"
            f"Roll Number: {roll_no}\n"
            f"Programme: {programme}, {semester} Semester\n"
            f"Leave dates: {from_date.strftime('%d %B %Y')} to {to_date.strftime('%d %B %Y')} ({days} day(s))\n"
            f"Reason: {reason}\n"
            f"Addressed to: {hod_line}\n\n"
            f"Write a professional, polite, and concise formal letter. "
            f"Include all standard components: sender's details, date, recipient, subject line, body, closing. "
            f"Do not add any commentary or explanation outside the letter itself."
        )

        with st.spinner("Generating your leave application..."):
            response = llms["groq_classifier"].invoke(prompt)
            letter = response.content.strip()

        st.markdown("#### 📄 Your Leave Application")
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:20px 24px;"
            f"font-family:Georgia,serif;line-height:1.8;white-space:pre-wrap;'>{letter}</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️ Download as .txt", data=letter,
            file_name=f"leave_application_{student_name.replace(' ','_')}.txt",
            mime="text/plain", use_container_width=True,
        )


# ========================================================================================
# MODE 6 — Exam Eligibility Checker (now auto-populated from the database when linked)
# ========================================================================================
def run_eligibility_mode():
    st.markdown("""
    <div class="main-header">
        <h1>🔔 Exam Eligibility Checker</h1>
        <p>Find out if you're eligible to sit for end-semester exams based on college rules</p>
    </div>
    """, unsafe_allow_html=True)

    report = db.get_student_eligibility_report(USER_EMAIL)

    if not report.get("linked"):
        render_roll_no_linker()
        st.caption("Once linked, your real eligibility will show here automatically. Meanwhile, you can check manually below.")
        _run_manual_eligibility_check()
        return

    if "subjects" not in report:
        st.info(f"You're linked as roll number **{report['roll_no']}**, but " + report["message"])
        _run_manual_eligibility_check()
        return

    st.caption(
        f"Showing live data for roll number **{report['roll_no']}** · "
        f"required attendance: **{report['required_attendance_pct']:.0f}%** · "
        f"required internal marks: **{report['required_internal_pct']:.0f}%**"
    )

    for s in report["subjects"]:
        eligible = s["eligible"]
        icon, color, status = ("✅", "#22c55e", "ELIGIBLE") if eligible else ("❌", "#ef4444", "NOT ELIGIBLE")

        reasons = []
        if not s["attendance_ok"]:
            reasons.append(f"Attendance {s['attendance_pct']:.1f}% below requirement")
        if s["internal_marks_ok"] is False:
            reasons.append(f"Internals {s['internal_marks_pct']}% below requirement")
        elif s["internal_marks_pct"] is None:
            reasons.append("No internal marks recorded yet")
        reason_text = " · ".join(reasons) if reasons else "All criteria met"

        st.markdown(
            f"""<div style='border-left:4px solid {color};padding:10px 14px;margin:6px 0;
            background:rgba(0,0,0,0.2);border-radius:4px;'>
            <b>{icon} {s['subject']}</b> &nbsp;
            <span style='color:{color};font-weight:700;'>{status}</span><br>
            <small style='color:#aaa;'>{reason_text}</small></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if report["all_eligible"]:
        st.success("🎉 You are eligible to appear in all end-semester examinations!")
    else:
        st.error("⚠️ You may not be eligible for some exams. Please contact your class teacher immediately.")


def _run_manual_eligibility_check():
    """Fallback: the original manual-entry eligibility form, for students not yet linked."""
    ATTEND_REQ = 75.0
    INTERNAL_REQ_PCT = 40.0

    with st.sidebar:
        st.markdown("### ⚙️ Rules")
        attend_req = st.number_input("Min Attendance %", 50, 100, 75, key="elig_att")
        internal_max = st.number_input("Internal Marks Max", 10, 100, 30, key="elig_intmax")
        internal_min_pct = st.number_input("Min Internal % required", 10, 100, 40, key="elig_intpct")
        ATTEND_REQ = float(attend_req)
        INTERNAL_MIN = internal_max * internal_min_pct / 100

        n_subjects = st.number_input("Number of subjects", 1, 12, 5, key="elig_nsub")

    st.markdown("#### Enter subject-wise details")
    h1, h2, h3 = st.columns([3, 2, 2])
    h1.caption("Subject")
    h2.caption(f"Attendance %")
    h3.caption(f"Internal Marks (out of {internal_max})")

    subjects = []
    for i in range(int(n_subjects)):
        c1, c2, c3 = st.columns([3, 2, 2])
        name = c1.text_input("Sub", key=f"elig_name_{i}", label_visibility="collapsed", placeholder=f"Subject {i+1}")
        att = c2.number_input("Att%", 0.0, 100.0, 0.0, key=f"elig_att_{i}", label_visibility="collapsed")
        internals = c3.number_input("Marks", 0.0, float(internal_max), 0.0, key=f"elig_int_{i}", label_visibility="collapsed")
        subjects.append({"name": name or f"Subject {i+1}", "att": att, "internals": internals})

    if st.button("Check Eligibility", type="primary", key="elig_check"):
        st.markdown("---")
        all_eligible = True
        for s in subjects:
            att_ok = s["att"] >= ATTEND_REQ
            int_ok = s["internals"] >= INTERNAL_MIN
            eligible = att_ok and int_ok
            if not eligible:
                all_eligible = False

            if eligible:
                icon, color, status = "✅", "#22c55e", "ELIGIBLE"
            elif s["att"] < (ATTEND_REQ - 10) or s["internals"] < (INTERNAL_MIN * 0.5):
                icon, color, status = "❌", "#ef4444", "NOT ELIGIBLE"
            else:
                icon, color, status = "⚠️", "#f97316", "BORDERLINE"

            reasons = []
            if not att_ok:
                reasons.append(f"Attendance {s['att']:.1f}% &lt; {ATTEND_REQ:.0f}% required")
            if not int_ok:
                reasons.append(f"Internals {s['internals']:.0f} &lt; {INTERNAL_MIN:.1f} required")
            reason_text = " · ".join(reasons) if reasons else "All criteria met"

            st.markdown(
                f"""<div style='border-left:4px solid {color};padding:10px 14px;margin:6px 0;
                background:rgba(0,0,0,0.2);border-radius:4px;'>
                <b>{icon} {s['name']}</b> &nbsp;
                <span style='color:{color};font-weight:700;'>{status}</span><br>
                <small style='color:#aaa;'>{reason_text}</small></div>""",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if all_eligible:
            st.success("🎉 You are eligible to appear in all end-semester examinations!")
        else:
            st.error("⚠️ You may not be eligible for some exams. Please contact your class teacher immediately.")


# ========================================================================================
# MODE 7 — Timetable
# ========================================================================================
TIMETABLE_PATH = DATA_DIR / "timetable.json"


def run_timetable_mode():
    st.markdown("""
    <div class="main-header">
        <h1>🗓️ Class Timetable</h1>
        <p>View your daily class schedule by programme and day</p>
    </div>
    """, unsafe_allow_html=True)

    if not TIMETABLE_PATH.exists():
        st.error("timetable.json not found in data/ directory.")
        return

    timetable = json.loads(TIMETABLE_PATH.read_text(encoding="utf-8-sig"))
    programmes = list(timetable.keys())
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    today_name = date.today().strftime("%A")  # e.g. "Monday"

    with st.sidebar:
        st.markdown("### 📅 Select Schedule")
        programme = st.selectbox("Programme", programmes, key="tt_prog")
        available_days = [d for d in days_order if d in timetable.get(programme, {})]
        default_day = today_name if today_name in available_days else available_days[0]
        day = st.selectbox("Day", available_days,
                           index=available_days.index(default_day), key="tt_day")

    slots = timetable.get(programme, {}).get(day, [])
    if not slots:
        st.info("No timetable data for this selection.")
        return

    is_today = (day == today_name)
    from datetime import datetime as _dt
    now_hour = _dt.now().hour
    now_min = _dt.now().minute

    st.markdown(f"#### {programme} — {day}{'  *(Today)*' if is_today else ''}")

    for slot in slots:
        is_lunch = slot["subject"] == "LUNCH BREAK"
        is_current = False
        if is_today and not is_lunch and "-" in slot["time"]:
            try:
                start_h = int(slot["time"].split("-")[0].split(":")[0])
                end_h = int(slot["time"].split("-")[1].split(":")[0])
                is_current = (start_h <= now_hour < end_h)
            except Exception:
                pass

        if is_lunch:
            st.markdown(
                "<div style='text-align:center;color:#aaa;padding:6px 0;border-top:1px dashed #333;"
                "border-bottom:1px dashed #333;margin:4px 0;font-size:0.85rem;'>🍽️ LUNCH BREAK · 12:00 – 13:00</div>",
                unsafe_allow_html=True,
            )
            continue

        border = "#60a5fa" if is_current else "#333"
        bg = "rgba(96,165,250,0.08)" if is_current else "rgba(0,0,0,0.2)"
        now_badge = " <span style='color:#60a5fa;font-size:0.75rem;font-weight:700;'>▶ NOW</span>" if is_current else ""
        room_text = f" · Room {slot['room']}" if slot.get("room") else ""
        teacher_text = f" · {slot['teacher']}" if slot.get("teacher") else ""

        st.markdown(
            f"""<div style='border-left:4px solid {border};padding:10px 14px;margin:4px 0;
            background:{bg};border-radius:4px;'>
            <b>{slot['time']}</b>{now_badge} &nbsp;
            <span style='font-size:1.05rem;'>{slot['subject']}</span><br>
            <small style='color:#aaa;'>{room_text}{teacher_text}</small></div>""",
            unsafe_allow_html=True,
        )


# ========================================================================================
# MODE 8 — Admin Dashboard (visible only to emails listed in ADMIN_EMAILS)
# ========================================================================================
def run_admin_dashboard():
    render_admin_banner("Admin Dashboard")
    st.markdown("""
    <div class="main-header">
        <h1>🛠️ Admin Dashboard</h1>
        <p>Usage insights for the College Assistant</p>
    </div>
    """, unsafe_allow_html=True)

    interactions = load_interactions_df()
    feedback = load_feedback_df()

    if interactions.empty:
        st.info("No usage data yet. Once students start using the College Assistant, stats will show up here.")
        return

    interactions["timestamp"] = pd.to_datetime(interactions["timestamp"])
    interactions["date"] = interactions["timestamp"].dt.date
    college_q = interactions[interactions["mode"] == "college"]

    down_rate = (feedback["feedback"] == "down").mean() * 100 if not feedback.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total questions asked", len(college_q))
    c2.metric("Unique students", college_q["user"].nunique())
    c3.metric("👎 rate (all-time)", f"{down_rate:.1f}%")

    st.subheader("Query volume by category")
    if not college_q.empty:
        st.bar_chart(college_q["query_type"].value_counts())

    st.subheader("Most asked questions")
    if not college_q.empty:
        top_q = college_q["query"].str.strip().str.lower().value_counts().head(10)
        st.table(top_q.rename("times asked"))
    else:
        st.caption("No questions logged yet.")

    st.subheader("👎 rate over time")
    if not feedback.empty:
        feedback["timestamp"] = pd.to_datetime(feedback["timestamp"])
        feedback["date"] = feedback["timestamp"].dt.date
        daily_down_rate = feedback.groupby("date")["feedback"].apply(lambda s: (s == "down").mean() * 100)
        st.line_chart(daily_down_rate)
    else:
        st.caption("No feedback submitted yet.")

    st.subheader("Query volume over time")
    st.bar_chart(college_q.groupby("date").size())

    st.subheader("⚙️ Eligibility rules")
    st.caption("These thresholds are used everywhere eligibility is checked — the chatbot, "
               "the Attendance Tracker, and the Exam Eligibility page (once a student is linked).")
    current_att = float(db.get_config("min_attendance_pct", default=75))
    current_marks = float(db.get_config("min_internal_pct", default=40))
    c1, c2 = st.columns(2)
    new_att = c1.number_input("Minimum attendance % required", 0, 100, int(current_att), key="cfg_att")
    new_marks = c2.number_input("Minimum internal marks % required", 0, 100, int(current_marks), key="cfg_marks")
    if st.button("💾 Save rules", key="cfg_save"):
        db.set_config("min_attendance_pct", str(new_att))
        db.set_config("min_internal_pct", str(new_marks))
        st.success("Eligibility rules updated.")

    with st.expander("Raw interaction log (most recent 200)"):
        st.dataframe(college_q.sort_values("timestamp", ascending=False).head(200), use_container_width=True)


# ========================================================================================
# Mode switcher
# ========================================================================================
LANGUAGE_OPTIONS = {"English": "English", "हिंदी (Hindi)": "Hindi"}

with st.sidebar:
    st.markdown(f"**Signed in as**  \n{USER_NAME}")
    st.caption(USER_EMAIL)
    st.button("Log out", on_click=st.logout, use_container_width=True)
    st.markdown("---")

    st.markdown("### 🌐 Response language")
    lang_label = st.selectbox(
        "Response language", list(LANGUAGE_OPTIONS.keys()),
        label_visibility="collapsed", key="language_choice",
    )
    st.session_state.language = LANGUAGE_OPTIONS[lang_label]
    st.markdown("---")

    st.markdown("### Choose a tool")

    student_labels = [
        "College Assistant", "Academic Calendar", "Attendance Tracker",
        "CGPA Calculator", "Leave Application", "Exam Eligibility", "Timetable",
    ]
    student_icons = ["mortarboard", "calendar-event", "bar-chart", "calculator", "envelope", "bell", "table"]

    admin_labels = ["Upload Students", "Upload Attendance", "Upload Timetable", "Upload Calendar", "Admin Dashboard"]
    admin_icons = ["people", "cloud-upload", "calendar-week", "calendar-plus", "speedometer2"]

    all_labels = student_labels + (admin_labels if IS_ADMIN else [])
    all_icons = student_icons + (admin_icons if IS_ADMIN else [])

    selected_label = option_menu(
        menu_title=None,
        options=all_labels,
        icons=all_icons,
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"font-size": "15px"},
            "nav-link": {
                "font-size": "14px", "text-align": "left", "margin": "2px 0",
                "border-radius": "8px", "padding": "8px 12px",
            },
            "nav-link-selected": {"background-color": "#7C5CFC", "color": "white", "font-weight": "600"},
        },
    )

    label_to_emoji_key = {
        "College Assistant": "🎓 College Assistant", "Academic Calendar": "📅 Academic Calendar",
        "Attendance Tracker": "📊 Attendance Tracker", "CGPA Calculator": "🧮 CGPA Calculator",
        "Leave Application": "📝 Leave Application", "Exam Eligibility": "🔔 Exam Eligibility",
        "Timetable": "🗓️ Timetable", "Upload Students": "👥 Upload Students",
        "Upload Attendance": "📤 Upload Attendance", "Upload Timetable": "🗓️ Upload Timetable",
        "Upload Calendar": "📅 Upload Calendar", "Admin Dashboard": "🛠️ Admin Dashboard",
    }
    mode = label_to_emoji_key[selected_label]
    st.markdown("---")

if mode == "🎓 College Assistant":
    run_college_mode()
elif mode == "📅 Academic Calendar":
    run_calendar_mode()
elif mode == "📊 Attendance Tracker":
    run_attendance_mode()
elif mode == "🧮 CGPA Calculator":
    run_cgpa_mode()
elif mode == "📝 Leave Application":
    run_leave_mode()
elif mode == "🔔 Exam Eligibility":
    run_eligibility_mode()
elif mode == "🗓️ Timetable":
    run_timetable_mode()
elif mode == "👥 Upload Students":
    run_admin_student_upload()
elif mode == "📤 Upload Attendance":
    run_admin_attendance_upload()
elif mode == "🗓️ Upload Timetable":
    run_admin_timetable_upload()
elif mode == "📅 Upload Calendar":
    run_admin_calendar_upload()
else:
    run_admin_dashboard()