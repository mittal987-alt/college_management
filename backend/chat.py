"""
chat.py — LangGraph chatbot router for the FastAPI backend.

Endpoints:
  POST /api/chat/stream              — SSE streaming chat response
  GET  /api/chat/conversations       — list saved conversations
  GET  /api/chat/conversations/{id}  — load a specific conversation
  POST /api/chat/conversations/{id}/feedback — log 👍/👎 feedback
"""

import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from typing import TypedDict

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import db
from auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent   # project root (c:\projects\college)
DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "chat_history"
INTERACTIONS_LOG = DATA_DIR / "interactions.jsonl"
FEEDBACK_LOG = DATA_DIR / "feedback.jsonl"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ── LLM + RAG (loaded once) ───────────────────────────────────────────────────
_embeddings = None
_academic_retriever = None
_fee_retriever = None
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        import os
        _llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.4)
    return _llm


def _build_retriever(pdf_path: Path):
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vs = FAISS.from_documents(chunks, embeddings)
    return vs.as_retriever(search_kwargs={"k": 4})


def get_academic_retriever():
    global _academic_retriever
    if _academic_retriever is None:
        _academic_retriever = _build_retriever(BASE_DIR / "academics_handbook.pdf")
    return _academic_retriever


def get_fee_retriever():
    global _fee_retriever
    if _fee_retriever is None:
        _fee_retriever = _build_retriever(BASE_DIR / "fee_structure.pdf")
    return _fee_retriever


# ── LangGraph state + nodes (ported from app.py) ─────────────────────────────
class CollegeState(TypedDict):
    programme: str
    user_email: str
    messages: Annotated[list, add_messages]
    query_type: str
    retrieved_context: str
    sources: list
    language: str


def classifier_node(state: CollegeState) -> dict:
    last_message = state["messages"][-1].content
    prompt = (
        "Classify the following student query into exactly one category: "
        "'academic', 'fee', 'attendance', 'eligibility', 'timetable', or 'general'.\n\n"
        "Use 'academic' for questions about COLLEGE RULES/POLICY around exams, grading, "
        "credits, promotion, course structure, summer training, or degree requirements.\n"
        "Use 'fee' for questions about tuition, payment, refund, late charges, scholarships.\n"
        "Use 'attendance' for questions asking about the STUDENT'S OWN attendance record.\n"
        "Use 'eligibility' for questions asking whether the STUDENT is personally eligible "
        "to sit for exams.\n"
        "Use 'timetable' for questions about the STUDENT'S class schedule.\n"
        "Use 'general' for greetings, casual talk, or anything else.\n\n"
        f"Query: {last_message}\n\n"
        "Return only one word: academic, fee, attendance, eligibility, timetable, or general."
    )
    response = _get_llm().invoke(prompt)
    category = response.content.strip().lower()
    valid = ["academic", "fee", "attendance", "eligibility", "timetable", "general"]
    category = next((c for c in valid if c in category), "general")
    return {"query_type": category}


def _retrieve_with_sources(retriever, query: str, label: str):
    docs = retriever.invoke(query)
    context = "\n\n".join(doc.page_content for doc in docs)
    sources = [{"label": label, "page": doc.metadata.get("page", "?")} for doc in docs]
    return context, sources


def academic_rag_node(state: CollegeState) -> dict:
    ctx, src = _retrieve_with_sources(get_academic_retriever(), state["messages"][-1].content, "Academics Handbook")
    return {"retrieved_context": ctx, "sources": src}


def fee_rag_node(state: CollegeState) -> dict:
    ctx, src = _retrieve_with_sources(get_fee_retriever(), state["messages"][-1].content, "Fee Structure")
    return {"retrieved_context": ctx, "sources": src}


def general_node(state: CollegeState) -> dict:
    return {"retrieved_context": "NO_RETRIEVAL_NEEDED", "sources": []}


def attendance_node(state: CollegeState) -> dict:
    report = db.get_student_attendance_report(state["user_email"])
    if not report.get("linked"):
        ctx = report["message"]
    elif "subjects" not in report:
        ctx = report["message"]
    else:
        lines = [
            f"Required attendance: {report['required_pct']:.0f}%",
            f"Overall attendance: {report['overall_pct']:.1f}% "
            f"({'meets' if report['overall_eligible'] else 'does NOT meet'} the requirement)",
            "", "Subject-wise attendance:",
        ]
        for s in report["subjects"]:
            status = "OK" if s["eligible"] else "BELOW REQUIREMENT"
            lines.append(f"- {s['subject']}: {s['attended']}/{s['held']} = {s['pct']:.1f}% [{status}]")
        ctx = "\n".join(lines)
    return {"retrieved_context": ctx, "sources": [{"label": "Live attendance records", "page": "—"}]}


def eligibility_node(state: CollegeState) -> dict:
    report = db.get_student_eligibility_report(state["user_email"])
    if not report.get("linked"):
        ctx = report["message"]
    elif "subjects" not in report:
        ctx = report["message"]
    else:
        lines = [
            f"Required attendance: {report['required_attendance_pct']:.0f}% · "
            f"Required internal marks: {report['required_internal_pct']:.0f}%",
            f"Overall: {'ELIGIBLE for all subjects' if report['all_eligible'] else 'NOT eligible for at least one subject'}",
            "", "Subject-wise breakdown:",
        ]
        for s in report["subjects"]:
            marks_text = f"{s['internal_marks_pct']}%" if s["internal_marks_pct"] is not None else "no marks recorded"
            status = "ELIGIBLE" if s["eligible"] else "NOT ELIGIBLE"
            lines.append(f"- {s['subject']}: attendance {s['attendance_pct']:.1f}%, internals {marks_text} [{status}]")
        ctx = "\n".join(lines)
    return {"retrieved_context": ctx, "sources": [{"label": "Live attendance & marks records", "page": "—"}]}


def timetable_node(state: CollegeState) -> dict:
    from datetime import date
    programme = state.get("programme", "Unknown")
    tt_path = DATA_DIR / "timetable.json"
    if not tt_path.exists():
        return {"retrieved_context": "No timetable data has been uploaded yet.", "sources": []}
    timetable = json.loads(tt_path.read_text(encoding="utf-8-sig"))
    today_name = date.today().strftime("%A")
    slots = timetable.get(programme, {}).get(today_name, [])
    if not slots:
        ctx = f"No timetable found for {programme} on {today_name}."
    else:
        lines = [f"{programme} schedule for today ({today_name}):"]
        for slot in slots:
            if slot["subject"] == "LUNCH BREAK":
                lines.append(f"- {slot['time']}: Lunch break")
                continue
            room = f", Room {slot['room']}" if slot.get("room") else ""
            teacher = f", {slot['teacher']}" if slot.get("teacher") else ""
            lines.append(f"- {slot['time']}: {slot['subject']}{room}{teacher}")
        ctx = "\n".join(lines)
    return {"retrieved_context": ctx, "sources": [{"label": "Timetable", "page": today_name}]}


def response_node(state: CollegeState) -> dict:
    query = state["messages"][-1].content
    programme = state.get("programme", "Unknown")
    context = state["retrieved_context"]
    language = state.get("language", "English")
    lang_instr = (
        "Respond entirely in Hindi (Devanagari script)." if language == "Hindi"
        else "Respond in English."
    )
    if context == "NO_RETRIEVAL_NEEDED":
        prompt = (f"You are a friendly college assistant talking to a {programme} student. "
                  f"{lang_instr}\nAnswer this question: {query}")
    else:
        prompt = (f"You are a college assistant helping a {programme} student. {lang_instr}\n"
                  f"Use the following information to answer accurately:\n\n{context}\n\nQuestion: {query}\n\n"
                  f"Give a clear, friendly, and precise answer.")
    response = _get_llm().invoke(prompt)
    return {"messages": [("ai", response.content.strip())]}


def route_query(state: CollegeState):
    return {
        "academic": "academic_rag", "fee": "fee_rag",
        "attendance": "attendance", "eligibility": "eligibility",
        "timetable": "timetable",
    }.get(state["query_type"], "general")


def _build_graph():
    graph = StateGraph(CollegeState)
    for name, fn in [
        ("classifier", classifier_node), ("academic_rag", academic_rag_node),
        ("fee_rag", fee_rag_node), ("general", general_node),
        ("attendance", attendance_node), ("eligibility", eligibility_node),
        ("timetable", timetable_node), ("response", response_node),
    ]:
        graph.add_node(name, fn)
    graph.add_edge(START, "classifier")
    graph.add_conditional_edges("classifier", route_query, {
        "academic_rag": "academic_rag", "fee_rag": "fee_rag", "general": "general",
        "attendance": "attendance", "eligibility": "eligibility", "timetable": "timetable",
    })
    for node in ["academic_rag", "fee_rag", "general", "attendance", "eligibility", "timetable"]:
        graph.add_edge(node, "response")
    graph.add_edge("response", END)
    return graph.compile()


_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


# ── Conversation persistence (same JSON format as before) ─────────────────────
def _safe_key(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:16]


def _user_dir(email: str) -> Path:
    d = HISTORY_DIR / _safe_key(email)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_conversations(email: str):
    convs = []
    for f in _user_dir(email).glob("*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            if payload.get("display_messages"):
                convs.append({
                    "id": f.stem, "title": payload.get("title") or "New chat",
                    "created_at": payload.get("created_at", ""),
                })
        except Exception:
            continue
    convs.sort(key=lambda c: c["created_at"], reverse=True)
    return convs


def _load_conversation(email: str, conv_id: str):
    path = _user_dir(email) / f"{conv_id}.json"
    if not path.exists():
        return [], [], "New chat"
    try:
        p = json.loads(path.read_text(encoding="utf-8"))
        lc = [tuple(m) for m in p.get("lc_messages", [])]
        return p.get("display_messages", []), lc, p.get("title") or "New chat"
    except Exception:
        return [], [], "New chat"


def _save_conversation(email: str, conv_id: str, title: str, display_messages: list, lc_messages: list):
    path = _user_dir(email) / f"{conv_id}.json"
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
    path.write_text(json.dumps({
        "title": title, "created_at": created_at,
        "display_messages": display_messages, "lc_messages": serial_lc,
    }, ensure_ascii=False), encoding="utf-8")


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/stream")
async def chat_stream(request: Request, user: dict = Depends(get_current_user)):
    """SSE endpoint — streams the LangGraph response token by token."""
    body = await request.json()
    query: str = body.get("query", "")
    programme: str = body.get("programme", "BCA")
    conv_id: str = body.get("conv_id", uuid.uuid4().hex[:12])
    language: str = body.get("language", "English")

    display_messages, lc_messages, title = _load_conversation(user["email"], conv_id)
    lc_messages.append(("human", query))

    async def event_generator() -> AsyncGenerator[str, None]:
        full_text = ""
        query_type = "general"
        sources = []

        # Stream tokens
        for chunk, metadata in get_graph().stream(
            {
                "programme": programme,
                "user_email": user["email"],
                "messages": lc_messages,
                "language": language,
            },
            stream_mode="messages",
        ):
            if metadata.get("langgraph_node") == "response" and getattr(chunk, "content", None):
                full_text += chunk.content
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        # Run a plain invoke to get structured state (query_type, sources)
        result = get_graph().invoke({
            "programme": programme,
            "user_email": user["email"],
            "messages": lc_messages,
            "language": language,
        })
        query_type = result.get("query_type", "general")
        sources = result.get("sources", [])
        ai_text = result["messages"][-1].content

        # Persist conversation
        display_messages.append({"role": "user", "content": query})
        display_messages.append({
            "role": "assistant", "content": ai_text,
            "query_type": query_type, "sources": sources, "query": query, "feedback": None,
        })
        if title == "New chat":
            title_new = (query[:40] + "…" if len(query) > 40 else query)
        else:
            title_new = title
        _save_conversation(user["email"], conv_id, title_new, display_messages, result["messages"])

        # Log interaction
        with open(INTERACTIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "user": user["email"], "mode": "college",
                "query": query, "query_type": query_type, "language": language,
            }) + "\n")

        # Send final metadata
        yield f"data: {json.dumps({'type': 'done', 'query_type': query_type, 'sources': sources, 'conv_id': conv_id, 'title': title_new})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    return _list_conversations(user["email"])


@router.get("/conversations/{conv_id}")
async def load_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    display_messages, _, title = _load_conversation(user["email"], conv_id)
    return {"id": conv_id, "title": title, "messages": display_messages}


@router.post("/conversations/{conv_id}/feedback")
async def set_feedback(conv_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    msg_index: int = body.get("msg_index", -1)
    feedback: str = body.get("feedback", "")
    display_messages, lc_messages, title = _load_conversation(user["email"], conv_id)
    if 0 <= msg_index < len(display_messages):
        display_messages[msg_index]["feedback"] = feedback
        query = display_messages[msg_index].get("query", "")
        _save_conversation(user["email"], conv_id, title, display_messages, lc_messages)
        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "user": user["email"], "query": query, "feedback": feedback,
            }) + "\n")
    return {"ok": True}
