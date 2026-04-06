# ══════════════════════════════════════════════
# Dockerfile - Chatbot Kinh Tế Việt Nam
# ══════════════════════════════════════════════
# Build:  docker build -t chatbot-kinhte .
# Run:    docker run -p 8000:8000 --gpus all --env-file .env chatbot-kinhte
# ══════════════════════════════════════════════

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# ── System dependencies ──
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set python3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# ── Working directory ──
WORKDIR /app

# ── Install Python dependencies (cached layer) ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn[standard]

# ── Copy source code ──
COPY chatbot/ ./chatbot/
COPY ingestion/ ./ingestion/
COPY frontend/ ./frontend/
COPY chroma_economy_db/ ./chroma_economy_db/
COPY .env .

# ── Environment ──
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# ── Expose port ──
EXPOSE 8000

# ── Health check ──
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# ── Start server ──
CMD ["python", "chatbot/services/server.py"]
