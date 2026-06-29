# ══════════════════════════════════════════════
# Dockerfile - Chatbot Kinh Tế Việt Nam
# ══════════════════════════════════════════════
# Build:  docker build -t chatbot-kinhte .
# Run:    prefer docker-compose up -d --build so volumes and localhost binding are applied
# ══════════════════════════════════════════════

FROM python:3.10-slim

# ── System dependencies ──
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

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
COPY app/ ./app/

# ── Environment ──
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8001

# ── Expose port ──
EXPOSE 8001

# ── Health check ──
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')" || exit 1

# ── Start server ──
CMD ["python", "chatbot/services/server.py"]
