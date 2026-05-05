"""
FastAPI Server cho Chatbot Kinh Tế Việt Nam.

Khởi động:
    python chatbot/services/server.py
    hoặc:
    uvicorn chatbot.services.server:app --host 0.0.0.0 --port 8001 --reload

Tham chiếu:
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

import uuid

from fastapi import FastAPI, HTTPException, Header, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from chatbot.main import ChatbotRunner
from chatbot.utils.base_db import UserDB
from chatbot.utils.jwt_utils import verify_jwt_token
from app.models.schemas import ApiSuccess, ApiError
from app.security.security import get_current_user
from app.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Pydantic Models (Request/Response)
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Schema cho yêu cầu chat từ Frontend."""
    question: str
    llm_provider: Optional[str] = None


class ChatResponseData(BaseModel):
    """Dữ liệu trả về trong response chat."""
    answer: str
    sources: list[dict]
    response_time: float
    num_docs_retrieved: int
    num_docs_graded: int


class HealthData(BaseModel):
    """Dữ liệu trả về trong response health check."""
    status: str
    llm_provider: str
    vector_store: str
    model_loaded: bool


# ------------------------------------------------------------------
# Helper: Lấy user email từ JWT token
# ------------------------------------------------------------------
def get_user_email_from_token(authorization: str = None) -> str | None:
    """
    Trích xuất email từ Authorization header (Bearer token).

    Args:
        authorization: Giá trị Authorization header.

    Returns:
        Email của user hoặc None nếu token không hợp lệ.
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
    """Lấy chatbot instance, raise 503 nếu chưa sẵn sàng."""
    global chatbot_instance, is_ready
    if chatbot_instance is None:
        raise HTTPException(
            status_code=503,
            detail=ApiError(
                message="Chatbot đang khởi tạo, vui lòng thử lại sau.",
                error_code="SERVICE_UNAVAILABLE"
            ).model_dump()
        )
    return chatbot_instance


@asynccontextmanager
async def lifespan(app):
    """Khởi tạo chatbot khi server start, dọn dẹp khi shutdown."""
    global chatbot_instance, is_ready

    logger.info("Đang khởi tạo Chatbot Server...")

    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"Vector store không tìm thấy tại: {VECTOR_STORE_PATH}")
        logger.info("Chạy: python ingestion/vector_data_builder.py")
    else:
        try:
            chatbot_instance = ChatbotRunner(
                path_vector_store=VECTOR_STORE_PATH,
                llm_provider=DEFAULT_LLM,
            )
            is_ready = True
            logger.info(f"Chatbot đã sẵn sàng! LLM: {DEFAULT_LLM}")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo chatbot: {e}", exc_info=True)

    yield

    logger.info("Shutting down server...")


# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------
app = FastAPI(
    title="Chatbot Kinh Tế Việt Nam API",
    description="API cho hệ thống RAG Chatbot sử dụng Energy-Based Distance Retriever",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — chỉ cho phép các origin cụ thể, không dùng "*" trong production
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Global Exception Handlers (skill_api_response_standard.md Mục 4)
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Bắt tất cả lỗi không mong đợi.
    Đảm bảo người dùng luôn nhận được JSON, không bao giờ nhận HTML error page.
    """
    logger.error(
        f"Lỗi không mong đợi tại {request.method} {request.url}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content=ApiError(
            message="Lỗi hệ thống. Vui lòng thử lại sau.",
            error_code="INTERNAL_SERVER_ERROR"
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Chuẩn hóa tất cả HTTPException sang ApiError format.
    Khắc phục trường hợp FastAPI mặc định trả {"detail": "..."}.
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
    """Kiểm tra trạng thái server."""
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
    Gửi câu hỏi và nhận câu trả lời từ chatbot.
    Tự động lưu lịch sử nếu user đã đăng nhập (có JWT token).

    Args:
        request: ChatRequest chứa câu hỏi.
        authorization: JWT Bearer token (optional).

    Returns:
        ApiSuccess chứa ChatResponseData.
    """
    bot = get_chatbot()

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Câu hỏi không được để trống.",
                error_code="EMPTY_QUESTION"
            ).model_dump()
        )

    user_email = get_user_email_from_token(authorization)
    start_time = time.time()

    try:
        input_state = {
            "question": request.question,
            "generation": "",
            "documents": [],
            "prompt": "",
        }

        output_state = bot.compiled_workflow.invoke(input_state)

        elapsed = time.time() - start_time
        answer = output_state.get("generation", "Không thể tạo câu trả lời.")
        docs = output_state.get("documents", [])

        sources = []
        for doc in docs:
            sources.append({
                "content": doc.page_content[:500],
                "source": doc.metadata.get("source", "Không rõ nguồn"),
                "full_content": doc.page_content,
            })

        # Lưu lịch sử chat vào DB nếu user đã đăng nhập
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
                logger.warning(f"Không thể lưu lịch sử chat: {db_err}")

        response_data = ChatResponseData(
            answer=answer,
            sources=sources,
            response_time=round(elapsed, 2),
            num_docs_retrieved=len(output_state.get("documents", [])),
            num_docs_graded=len(docs),
        )

        return ApiSuccess(
            message="Trả lời thành công",
            data=response_data.model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Lỗi xử lý chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message=f"Lỗi xử lý: {str(e)}",
                error_code="CHAT_PROCESSING_ERROR"
            ).model_dump()
        )


# ------------------------------------------------------------------
# Chat History Endpoints (sử dụng Depends(get_current_user) thay vì Header thủ công)
# ------------------------------------------------------------------
@app.get("/api/chat/history", tags=["Chat History"])
async def get_chat_history(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """
    Lấy lịch sử chat của user đang đăng nhập.
    Yêu cầu JWT token (tự động xác thực qua Depends).
    """
    user_email = current_user["email"]

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
async def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """
    Xóa toàn bộ lịch sử chat của user đang đăng nhập.
    Yêu cầu JWT token (tự động xác thực qua Depends).
    """
    user_email = current_user["email"]

    with UserDB() as db:
        deleted = db.clear_chat_history(user_email)

    return ApiSuccess(
        message="Xóa lịch sử thành công",
        data={"deleted": deleted, "user_email": user_email}
    )


# ------------------------------------------------------------------
# Async Task Polling (skill_async_task_polling.md)
# Dùng cho các tác vụ AI nặng (background processing)
# ------------------------------------------------------------------
task_store: dict = {}  # In-memory store cho task status


class TaskRequest(BaseModel):
    """Schema cho yêu cầu tạo task bất đồng bộ."""
    question: str
    prompt: Optional[str] = None


def _heavy_chat_worker(task_id: str, question: str, prompt: str, user_email: str = None):
    """
    Worker chạy trong background thread cho tác vụ AI nặng.
    Hàm đồng bộ (def) để FastAPI chạy trong ThreadPool riêng,
    tránh gây nghẽn Event Loop.

    Args:
        task_id: UUID của task.
        question: Câu hỏi cần xử lý.
        prompt: Custom prompt (optional).
        user_email: Email user để lưu lịch sử.
    """
    try:
        bot = get_chatbot()
        start_time = time.time()

        input_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "prompt": prompt or "",
        }

        output_state = bot.compiled_workflow.invoke(input_state)

        elapsed = time.time() - start_time
        answer = output_state.get("generation", "Không thể tạo câu trả lời.")
        docs = output_state.get("documents", [])

        sources = []
        for doc in docs:
            sources.append({
                "content": doc.page_content[:500],
                "source": doc.metadata.get("source", "Không rõ nguồn"),
            })

        # Cập nhật store
        task_store[task_id] = {
            "status": "done",
            "result": {
                "answer": answer,
                "sources": sources,
                "response_time": round(elapsed, 2),
                "num_docs": len(docs),
            }
        }

        # Lưu lịch sử nếu có user
        if user_email:
            try:
                with UserDB() as db:
                    db.save_chat_message(user_email=user_email, role="user", content=question)
                    db.save_chat_message(
                        user_email=user_email, role="bot", content=answer,
                        sources=sources, response_time=round(elapsed, 2), num_docs=len(docs)
                    )
            except Exception as db_err:
                logger.warning(f"Không thể lưu lịch sử task: {db_err}")

        logger.info(f"Task {task_id} hoàn thành sau {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Task {task_id} thất bại: {e}", exc_info=True)
        task_store[task_id] = {
            "status": "failed",
            "error": str(e),
        }


@app.post("/api/task/chat", tags=["Async Task"])
async def start_chat_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(default=None),
):
    """
    Khởi tạo tác vụ chat bất đồng bộ (background).
    Trả về task_id ngay lập tức, frontend polling để lấy kết quả.

    Dùng cho các câu hỏi phức tạp cần xử lý lâu (>30s).
    """
    get_chatbot()  # Kiểm tra chatbot sẵn sàng

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Câu hỏi không được để trống.",
                error_code="EMPTY_QUESTION"
            ).model_dump()
        )

    task_id = str(uuid.uuid4())
    user_email = get_user_email_from_token(authorization)

    # Đánh dấu trạng thái đang xử lý
    task_store[task_id] = {"status": "processing", "start_time": time.time()}

    # Đẩy vào background task
    background_tasks.add_task(
        _heavy_chat_worker, task_id, request.question, request.prompt, user_email
    )

    return ApiSuccess(
        message="Tác vụ đã được khởi tạo",
        data={"task_id": task_id, "status": "processing"}
    )


@app.get("/api/task/{task_id}", tags=["Async Task"])
async def get_task_status(task_id: str):
    """
    Kiểm tra trạng thái tác vụ bất đồng bộ.
    Frontend gọi API này mỗi 2-3 giây để polling kết quả.
    """
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Task không tồn tại.",
                error_code="TASK_NOT_FOUND"
            ).model_dump()
        )

    response_data = {"task_id": task_id, "status": task["status"]}

    if task["status"] == "done":
        response_data["result"] = task["result"]
        # Xóa khỏi store sau khi trả kết quả (tiết kiệm memory)
        del task_store[task_id]
    elif task["status"] == "failed":
        response_data["error"] = task.get("error", "Lỗi không xác định")
        del task_store[task_id]

    return ApiSuccess(data=response_data)


# ------------------------------------------------------------------
# Serve Frontend (static files)
# ------------------------------------------------------------------
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", tags=["Frontend"])
    async def serve_frontend():
        """Serve trang chủ frontend."""
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
        workers=1,  # 1 worker vì model embedding dùng chung
    )
