"""
🚀 FastAPI Server cho Chatbot Kinh Tế Việt Nam.

Khởi động:
    python chatbot/services/server.py
    hoặc:
    uvicorn chatbot.services.server:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from chatbot.main import ChatbotRunner
from chatbot.utils.base_db import UserDB
from chatbot.utils.jwt_utils import verify_jwt_token


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    llm_provider: Optional[str] = None  # Override LLM nếu cần


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    response_time: float
    num_docs_retrieved: int
    num_docs_graded: int


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    vector_store: str
    model_loaded: bool


# ──────────────────────────────────────────────
# Helper: Lấy user email từ JWT token
# ──────────────────────────────────────────────
def get_user_email_from_token(authorization: str = None) -> str | None:
    """Trích xuất email từ Authorization header (Bearer token)."""
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_jwt_token(token)
        if payload:
            return payload.get("email")
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────
VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "openai")

chatbot_instance: ChatbotRunner = None
is_ready = False


def get_chatbot() -> ChatbotRunner:
    """Lấy chatbot instance, khởi tạo nếu chưa có."""
    global chatbot_instance, is_ready
    if chatbot_instance is None:
        raise HTTPException(status_code=503, detail="Chatbot đang khởi tạo, vui lòng thử lại sau.")
    return chatbot_instance


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    """Khởi tạo chatbot khi server start."""
    global chatbot_instance, is_ready

    print("🚀 Đang khởi tạo Chatbot Server...")

    if not os.path.exists(VECTOR_STORE_PATH):
        print(f"❌ Vector store không tìm thấy tại: {VECTOR_STORE_PATH}")
        print("💡 Chạy: python ingestion/vector_data_builder.py")
    else:
        try:
            chatbot_instance = ChatbotRunner(
                path_vector_store=VECTOR_STORE_PATH,
                llm_provider=DEFAULT_LLM,
            )
            is_ready = True
            print(f"✅ Chatbot đã sẵn sàng! LLM: {DEFAULT_LLM}")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo chatbot: {e}")

    yield  # Server đang chạy

    print("👋 Shutting down server...")


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Chatbot Kinh Tế Việt Nam API",
    description="API cho hệ thống RAG Chatbot sử dụng Energy-Based Distance Retriever",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Auth Router
# ──────────────────────────────────────────────
from chatbot.services.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1")


# ──────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Kiểm tra trạng thái server."""
    return HealthResponse(
        status="ready" if is_ready else "initializing",
        llm_provider=DEFAULT_LLM,
        vector_store=VECTOR_STORE_PATH,
        model_loaded=is_ready,
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, authorization: str = Header(default=None)):
    """
    Gửi câu hỏi và nhận câu trả lời từ chatbot.
    Tự động lưu lịch sử nếu user đã đăng nhập (có JWT token).

    - **question**: Câu hỏi về kinh tế Việt Nam
    """
    bot = get_chatbot()

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    # Lấy email từ token (nếu có)
    user_email = get_user_email_from_token(authorization)

    start_time = time.time()

    try:
        # Chuẩn bị input state
        input_state = {
            "question": request.question,
            "generation": "",
            "documents": [],
            "prompt": "",
        }

        # Chạy workflow
        output_state = bot.compiled_workflow.invoke(input_state)

        elapsed = time.time() - start_time
        answer = output_state.get("generation", "❌ Không thể tạo câu trả lời.")
        docs = output_state.get("documents", [])

        # Format sources
        sources = []
        for doc in docs:
            sources.append({
                "content": doc.page_content[:500],
                "source": doc.metadata.get("source", "Không rõ nguồn"),
                "full_content": doc.page_content,
            })

        # ── Lưu lịch sử chat vào DB ──
        if user_email:
            with UserDB() as db:
                # Lưu câu hỏi của user
                db.save_chat_message(
                    user_email=user_email,
                    role="user",
                    content=request.question,
                )
                # Lưu câu trả lời của bot
                db.save_chat_message(
                    user_email=user_email,
                    role="bot",
                    content=answer,
                    sources=sources,
                    response_time=round(elapsed, 2),
                    num_docs=len(docs),
                )

        return ChatResponse(
            answer=answer,
            sources=sources,
            response_time=round(elapsed, 2),
            num_docs_retrieved=len(output_state.get("documents", [])),
            num_docs_graded=len(docs),
        )

    except Exception as e:
        elapsed = time.time() - start_time
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")


# ──────────────────────────────────────────────
# Chat History Endpoints
# ──────────────────────────────────────────────
@app.get("/api/chat/history", tags=["Chat History"])
async def get_chat_history(
    limit: int = 100,
    offset: int = 0,
    authorization: str = Header(default=None),
):
    """
    Lấy lịch sử chat của user đang đăng nhập.
    Yêu cầu JWT token trong Authorization header.
    """
    user_email = get_user_email_from_token(authorization)
    if not user_email:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập.")

    with UserDB() as db:
        messages = db.get_chat_history(user_email, limit=limit, offset=offset)
        total = db.get_chat_message_count(user_email)

    return {
        "messages": messages,
        "total": total,
        "user_email": user_email,
    }


@app.delete("/api/chat/history", tags=["Chat History"])
async def clear_chat_history(authorization: str = Header(default=None)):
    """
    Xóa toàn bộ lịch sử chat của user đang đăng nhập.
    Yêu cầu JWT token trong Authorization header.
    """
    user_email = get_user_email_from_token(authorization)
    if not user_email:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập.")

    with UserDB() as db:
        deleted = db.clear_chat_history(user_email)

    return {"deleted": deleted, "user_email": user_email}


# ──────────────────────────────────────────────
# Serve Frontend (static files)
# ──────────────────────────────────────────────
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", tags=["Frontend"])
    async def serve_frontend():
        """Serve trang chủ frontend."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# ──────────────────────────────────────────────
# Run Server
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8001))
    print(f"🌐 Starting server on http://0.0.0.0:{port}")
    print(f"📖 API Docs: http://localhost:{port}/docs")

    uvicorn.run(
        "chatbot.services.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,  # 1 worker vì model embedding dùng chung
    )
