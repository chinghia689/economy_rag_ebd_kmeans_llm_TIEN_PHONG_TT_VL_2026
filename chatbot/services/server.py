"""
FastAPI Server cho Chatbot Kinh Te Viet Nam.

Khoi dong:
    python chatbot/services/server.py
    hoac:
    uvicorn chatbot.services.server:app --host 0.0.0.0 --port 8001 --reload

Tham chieu:
    - docs/DOCS-main/skill_api_response_standard.md
    - docs/DOCS-main/skill_logging_monitoring.md
    - docs/DOCS-main/skill_coding_conventions.md
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from chatbot.main import ChatbotRunner
from chatbot.utils.base_db import UserDB
from chatbot.utils.jwt_utils import verify_jwt_token
from app.models.schemas import ApiSuccess, ApiError
from app.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Pydantic Models (Request/Response)
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Schema cho yeu cau chat tu Frontend."""
    question: str
    llm_provider: Optional[str] = None


class ChatResponseData(BaseModel):
    """Du lieu tra ve trong response chat."""
    answer: str
    sources: list[dict]
    response_time: float
    num_docs_retrieved: int
    num_docs_graded: int


class HealthData(BaseModel):
    """Du lieu tra ve trong response health check."""
    status: str
    llm_provider: str
    vector_store: str
    model_loaded: bool


# ------------------------------------------------------------------
# Helper: Lay user email tu JWT token
# ------------------------------------------------------------------
def get_user_email_from_token(authorization: str = None) -> str | None:
    """
    Trich xuat email tu Authorization header (Bearer token).

    Args:
        authorization: Gia tri Authorization header.

    Returns:
        Email cua user hoac None neu token khong hop le.
    """
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


# ------------------------------------------------------------------
# Global state
# ------------------------------------------------------------------
VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "openai")

chatbot_instance: ChatbotRunner = None
is_ready = False


def get_chatbot() -> ChatbotRunner:
    """Lay chatbot instance, raise 503 neu chua san sang."""
    global chatbot_instance, is_ready
    if chatbot_instance is None:
        raise HTTPException(
            status_code=503,
            detail=ApiError(
                message="Chatbot dang khoi tao, vui long thu lai sau.",
                error_code="SERVICE_UNAVAILABLE"
            ).model_dump()
        )
    return chatbot_instance


@asynccontextmanager
async def lifespan(app):
    """Khoi tao chatbot khi server start, don dep khi shutdown."""
    global chatbot_instance, is_ready

    logger.info("Dang khoi tao Chatbot Server...")

    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"Vector store khong tim thay tai: {VECTOR_STORE_PATH}")
        logger.info("Chay: python ingestion/vector_data_builder.py")
    else:
        try:
            chatbot_instance = ChatbotRunner(
                path_vector_store=VECTOR_STORE_PATH,
                llm_provider=DEFAULT_LLM,
            )
            is_ready = True
            logger.info(f"Chatbot da san sang! LLM: {DEFAULT_LLM}")
        except Exception as e:
            logger.error(f"Loi khoi tao chatbot: {e}", exc_info=True)

    yield  # Server dang chay

    logger.info("Shutting down server...")


# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------
app = FastAPI(
    title="Chatbot Kinh Te Viet Nam API",
    description="API cho he thong RAG Chatbot su dung Energy-Based Distance Retriever",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — chi cho phep cac origin cu the, khong dung "*" trong production
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Global Exception Handlers (skill_api_response_standard.md Muc 4)
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Bat tat ca loi khong mong doi.
    Dam bao nguoi dung luon nhan duoc JSON, khong bao gio nhan HTML error page.
    """
    logger.error(
        f"Loi khong mong doi tai {request.method} {request.url}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content=ApiError(
            message="Loi he thong. Vui long thu lai sau.",
            error_code="INTERNAL_SERVER_ERROR"
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Chuan hoa tat ca HTTPException sang ApiError format.
    Khac phuc truong hop FastAPI mac dinh tra {"detail": "..."} thay vi {"success": false, ...}.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict)
                else ApiError(message=str(exc.detail)).model_dump()
    )


# ------------------------------------------------------------------
# Auth Router
# ------------------------------------------------------------------
from chatbot.services.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1")


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------
@app.get("/api/health", tags=["System"])
async def health_check():
    """Kiem tra trang thai server."""
    return ApiSuccess(
        data=HealthData(
            status="ready" if is_ready else "initializing",
            llm_provider=DEFAULT_LLM,
            vector_store=VECTOR_STORE_PATH,
            model_loaded=is_ready,
        ).model_dump()
    )


@app.post("/api/chat", tags=["Chat"])
async def chat(request: ChatRequest, authorization: str = Header(default=None)):
    """
    Gui cau hoi va nhan cau tra loi tu chatbot.
    Tu dong luu lich su neu user da dang nhap (co JWT token).

    Args:
        request: ChatRequest chua cau hoi.
        authorization: JWT Bearer token (optional).

    Returns:
        ApiSuccess chua ChatResponseData.
    """
    bot = get_chatbot()

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Cau hoi khong duoc de trong.",
                error_code="EMPTY_QUESTION"
            ).model_dump()
        )

    # Lay email tu token (neu co)
    user_email = get_user_email_from_token(authorization)

    start_time = time.time()

    try:
        # Chuan bi input state
        input_state = {
            "question": request.question,
            "generation": "",
            "documents": [],
            "prompt": "",
        }

        # Chay workflow
        output_state = bot.compiled_workflow.invoke(input_state)

        elapsed = time.time() - start_time
        answer = output_state.get("generation", "Khong the tao cau tra loi.")
        docs = output_state.get("documents", [])

        # Format sources
        sources = []
        for doc in docs:
            sources.append({
                "content": doc.page_content[:500],
                "source": doc.metadata.get("source", "Khong ro nguon"),
                "full_content": doc.page_content,
            })

        # Luu lich su chat vao DB
        if user_email:
            try:
                with UserDB() as db:
                    db.save_chat_message(
                        user_email=user_email,
                        role="user",
                        content=request.question,
                    )
                    db.save_chat_message(
                        user_email=user_email,
                        role="bot",
                        content=answer,
                        sources=sources,
                        response_time=round(elapsed, 2),
                        num_docs=len(docs),
                    )
            except Exception as db_err:
                logger.warning(f"Khong the luu lich su chat: {db_err}")

        response_data = ChatResponseData(
            answer=answer,
            sources=sources,
            response_time=round(elapsed, 2),
            num_docs_retrieved=len(output_state.get("documents", [])),
            num_docs_graded=len(docs),
        )

        return ApiSuccess(
            message="Tra loi thanh cong",
            data=response_data.model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Loi xu ly chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message=f"Loi xu ly: {str(e)}",
                error_code="CHAT_PROCESSING_ERROR"
            ).model_dump()
        )


# ------------------------------------------------------------------
# Chat History Endpoints
# ------------------------------------------------------------------
@app.get("/api/chat/history", tags=["Chat History"])
async def get_chat_history(
    limit: int = 100,
    offset: int = 0,
    authorization: str = Header(default=None),
):
    """
    Lay lich su chat cua user dang dang nhap.
    Yeu cau JWT token trong Authorization header.
    """
    user_email = get_user_email_from_token(authorization)
    if not user_email:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Chua dang nhap.",
                error_code="UNAUTHORIZED"
            ).model_dump()
        )

    with UserDB() as db:
        messages = db.get_chat_history(user_email, limit=limit, offset=offset)
        total = db.get_chat_message_count(user_email)

    return ApiSuccess(
        data={
            "messages": messages,
            "total": total,
            "user_email": user_email,
        }
    )


@app.delete("/api/chat/history", tags=["Chat History"])
async def clear_chat_history(authorization: str = Header(default=None)):
    """
    Xoa toan bo lich su chat cua user dang dang nhap.
    Yeu cau JWT token trong Authorization header.
    """
    user_email = get_user_email_from_token(authorization)
    if not user_email:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Chua dang nhap.",
                error_code="UNAUTHORIZED"
            ).model_dump()
        )

    with UserDB() as db:
        deleted = db.clear_chat_history(user_email)

    return ApiSuccess(
        message="Xoa lich su thanh cong",
        data={"deleted": deleted, "user_email": user_email}
    )


# ------------------------------------------------------------------
# Serve Frontend (static files)
# ------------------------------------------------------------------
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", tags=["Frontend"])
    async def serve_frontend():
        """Serve trang chu frontend."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# ------------------------------------------------------------------
# Run Server
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8001))
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    logger.info(f"API Docs: http://localhost:{port}/docs")

    uvicorn.run(
        "chatbot.services.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,  # 1 worker vi model embedding dung chung
    )
