# ── Backend Dockerfile ────────────────────────────────────────────────────────
# Python 3.12 slim image for a lightweight production container
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed by some Python packages (e.g. faiss, pdfplumber)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# main.py loads .env from parent dir (Path(__file__).parent.parent / ".env").
# Inside the container /app is the working dir, so we create a symlink so that
# /app/../.env → /app/.env (which is bind-mounted by docker-compose).
RUN ln -sf /app/.env /.env

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
