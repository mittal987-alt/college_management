"""
main.py — FastAPI entry point for the College Assistant backend.

Run locally:
    uvicorn main:app --reload --port 8000

Environment variables (.env in project root):
    GROQ_API_KEY
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    SECRET_KEY
    ADMIN_EMAILS
    FRONTEND_URL   (default: http://localhost:5173)
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Load .env from the project root (one level up from this file)
load_dotenv(Path(__file__).parent.parent / ".env")

import db
from auth import router as auth_router
from chat import router as chat_router
from student import router as student_router
from admin import router as admin_router

db.init_db()

app = FastAPI(title="College Assistant API", version="2.0.0")

# ── Session middleware (required by authlib for OAuth state) ──────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
)

# ── CORS — allow the React dev server and any configured frontend URL ─────────
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(student_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
