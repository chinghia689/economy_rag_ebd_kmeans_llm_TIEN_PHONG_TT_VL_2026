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

import asyncio
import os
import sys
import time
from pathlib import Path
from threading import RLock
from typing import Optional
from contextlib import asynccontextmanager, suppress

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uuid

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from chatbot.main import ChatbotRunner
from chatbot.utils.base_db import UserDB
from chatbot.utils.greeting_handler import get_greeting_response
from chatbot.utils.token_counter import count_tokens
from app.runtime_config import get_runtime_setting, get_runtime_signature
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
    conversation_id: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: str


class ConversationMessageRequest(BaseModel):
    question: str
    prompt: Optional[str] = None


class ChatResponseData(BaseModel):
    """Dữ liệu trả về trong response chat."""
    answer: str
    sources: list[dict]
    response_time: float
    num_docs_retrieved: int
    num_docs_graded: int
    token_used: int = 0
    conversation_id: Optional[str] = None
    balance: Optional[int] = None


class HealthData(BaseModel):
    """Dữ liệu trả về trong response health check."""
    status: str
    llm_provider: str
    vector_store: str
    model_loaded: bool


# ------------------------------------------------------------------
# Helper: Lấy user email từ JWT token
# ------------------------------------------------------------------
# Global state
# ------------------------------------------------------------------
VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
LLM_RUNTIME_KEYS = [
    "DEFAULT_LLM",
    "KEY_API_OPENAI",
    "OPENAI_LLM_MODEL_NAME",
    "GOOGLE_API_KEY",
    "GOOGLE_LLM_MODEL_NAME",
    "GROQ_API_KEY",
    "GROQ_LLM_MODEL_NAME",
]
chatbot_instance: ChatbotRunner = None
chatbot_config_signature: tuple[tuple[str, str], ...] | None = None
is_ready = False
chatbot_lock = RLock()
payment_cleanup_task: asyncio.Task | None = None


def get_default_llm() -> str:
    return get_runtime_setting("DEFAULT_LLM", "openai")


def get_runtime_int(key: str, default: int) -> int:
    try:
        return int(get_runtime_setting(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_allow_origins() -> list[str]:
    raw = get_runtime_setting("ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8001")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:5173", "http://localhost:8001"]


def get_max_question_chars() -> int:
    return get_runtime_int("MAX_QUESTION_CHARS", 4000)


def get_task_config() -> dict[str, int]:
    return {
        "result_ttl": get_runtime_int("TASK_RESULT_TTL_SECONDS", 600),
        "processing_timeout": get_runtime_int("TASK_PROCESSING_TIMEOUT_SECONDS", 1800),
        "cleanup_interval": get_runtime_int("TASK_CLEANUP_INTERVAL_SECONDS", 60),
    }


async def cleanup_expired_payments_loop() -> None:
    """Tu dong xoa payment pending qua han 5 phut."""
    while True:
        try:
            with UserDB() as db:
                deleted = db.delete_expired_pending_payments()
            if deleted:
                logger.info(f"Da xoa {deleted} payment pending qua 5 phut.")
        except Exception as exc:
            logger.warning(f"Khong the cleanup payment pending qua han: {exc}")
        await asyncio.sleep(30)


def get_chatbot() -> ChatbotRunner:
    """Lấy chatbot instance, khởi tạo lazy để server start không bị kẹt model/network."""
    global chatbot_instance, chatbot_config_signature, is_ready

    current_signature = get_runtime_signature(LLM_RUNTIME_KEYS)
    if chatbot_instance is not None and chatbot_config_signature == current_signature:
        return chatbot_instance

    with chatbot_lock:
        current_signature = get_runtime_signature(LLM_RUNTIME_KEYS)
        if chatbot_instance is not None and chatbot_config_signature == current_signature:
            return chatbot_instance

        if chatbot_instance is not None:
            logger.info("Runtime LLM config changed; recreating chatbot instance.")
            chatbot_instance = None
            is_ready = False

        if not os.path.exists(VECTOR_STORE_PATH):
            raise HTTPException(
                status_code=503,
                detail=ApiError(
                    message="Vector store không tìm thấy. Vui lòng ingest dữ liệu trước.",
                    error_code="VECTOR_STORE_NOT_FOUND"
                ).model_dump()
            )

        try:
            llm_provider = get_default_llm()
            logger.info(f"Đang khởi tạo chatbot lazy với LLM: {llm_provider}")
            chatbot_instance = ChatbotRunner(
                path_vector_store=VECTOR_STORE_PATH,
                llm_provider=llm_provider,
            )
            chatbot_config_signature = current_signature
            is_ready = True
            logger.info(f"Chatbot đã sẵn sàng! LLM: {llm_provider}")
            return chatbot_instance
        except Exception as e:
            is_ready = False
            logger.error(f"Lỗi khởi tạo chatbot: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=ApiError(
                    message="Chatbot chưa sẵn sàng, vui lòng thử lại sau.",
                    error_code="SERVICE_UNAVAILABLE"
                ).model_dump()
            )


def validate_question(question: str) -> str:
    clean_question = question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Câu hỏi không được để trống.",
                error_code="EMPTY_QUESTION"
            ).model_dump()
        )
    max_question_chars = get_max_question_chars()
    if len(clean_question) > max_question_chars:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message=f"Câu hỏi quá dài. Tối đa {max_question_chars} ký tự.",
                error_code="QUESTION_TOO_LONG"
            ).model_dump()
        )
    return clean_question


def get_chat_token_count(text: str) -> int:
    model = get_runtime_setting("OPENAI_LLM_MODEL_NAME", "gpt-5-mini")
    return max(1, count_tokens(text, model))


def run_chat_workflow(question: str, prompt: str = "") -> tuple[str, list[dict], float, int]:
    bot = get_chatbot()
    start_time = time.time()

    input_state = {
        "question": question,
        "generation": "",
        "documents": [],
        # "prompt": prompt or "",
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

    return answer, sources, round(elapsed, 2), len(docs)


def build_free_greeting_response(
    *,
    answer: str,
    saved: dict,
    conversation_id: str,
) -> ApiSuccess:
    response_data = ChatResponseData(
        answer=answer,
        sources=[],
        response_time=0.0,
        num_docs_retrieved=0,
        num_docs_graded=0,
        token_used=0,
        conversation_id=conversation_id,
        balance=saved["balance"],
    ).model_dump()
    response_data.update({
        "user_message": saved["user_message"],
        "bot_message": saved["bot_message"],
        "conversation": saved["conversation"],
        "is_free_greeting": True,
    })
    return ApiSuccess(
        message="Phản hồi chào hỏi miễn phí",
        data=response_data,
    )


def raise_insufficient_tokens(message: str = "Bạn đã hết token. Vui lòng nạp thêm token để tiếp tục."):
    raise HTTPException(
        status_code=402,
        detail=ApiError(
            message=message,
            error_code="INSUFFICIENT_TOKENS"
        ).model_dump()
    )


@asynccontextmanager
async def lifespan(app):
    """Khởi động server; chatbot được lazy-load ở request đầu tiên."""
    global payment_cleanup_task

    logger.info("Đang khởi tạo Chatbot Server...")

    if not os.path.exists(VECTOR_STORE_PATH):
        logger.error(f"Vector store không tìm thấy tại: {VECTOR_STORE_PATH}")
        logger.info("Chạy: python ingestion/vector_data_builder.py")
    else:
        logger.info("Vector store đã sẵn sàng; chatbot sẽ được tải khi có request đầu tiên.")

    payment_cleanup_task = asyncio.create_task(cleanup_expired_payments_loop())

    try:
        yield
    finally:
        if payment_cleanup_task:
            payment_cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await payment_cleanup_task
            payment_cleanup_task = None

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

# CORS — đọc từ DB-backed runtime settings, không phụ thuộc .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allow_origins(),
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
# Payment Router
# ------------------------------------------------------------------
from app.routers.payment import router as payment_router
app.include_router(payment_router, prefix="/api/v1")

# ------------------------------------------------------------------
# Admin Router
# ------------------------------------------------------------------
from app.routers.admin import router as admin_router
app.include_router(admin_router, prefix="/api/v1")


# ------------------------------------------------------------------
# /auth/me - Xac thuc token khi app khoi dong
# (skill_frontend_architecture.md Muc 4.2)
# ------------------------------------------------------------------
@app.get("/api/v1/auth/me", tags=["Authentication"])
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Tra ve thong tin user hien tai tu JWT token.
    Frontend goi API nay khi app khoi dong de xac minh token con hop le.
    """
    return ApiSuccess(
        data={
            "email": current_user.get("email"),
            "name": current_user.get("name"),
            "picture": current_user.get("picture"),
            "is_admin": current_user.get("is_admin", False),
        }
    )


@app.get("/api/v1/me/balance", tags=["User"])
async def get_current_user_balance(current_user: dict = Depends(get_current_user)):
    """Tra ve token balance cua user hien tai."""
    email = current_user["email"]
    with UserDB() as db:
        balance = db.get_token_balance(email)
        transactions = db.get_token_transactions(email, limit=20)

    return ApiSuccess(
        data={
            "user_email": email,
            "token_balance": balance,
            "transactions": transactions,
        }
    )


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------
@app.get("/api/health", tags=["System"])
async def health_check():
    """Kiểm tra trạng thái server."""
    return ApiSuccess(
        data=HealthData(
            status="ready" if is_ready else "initializing",
            llm_provider=get_default_llm(),
            vector_store=VECTOR_STORE_PATH,
            model_loaded=is_ready,
        ).model_dump()
    )


@app.get("/api/internal/health", tags=["System"])
async def internal_health_check(current_user: dict = Depends(get_current_user)):
    """Health chi tiet cho van hanh noi bo."""
    checks = {
        "db": False,
        "vector_store": os.path.exists(VECTOR_STORE_PATH),
        "llm_configured": False,
        "sepay_configured": False,
    }
    with UserDB() as db:
        db.cursor.execute("SELECT 1")
        checks["db"] = True
        checks["llm_configured"] = bool((db.get_app_setting("KEY_API_OPENAI", "") or "").strip())
        checks["sepay_configured"] = bool((db.get_app_setting("SEPAY_API_KEY", "") or "").strip() and (db.get_app_setting("SEPAY_ACCOUNT_NUMBER", "") or "").strip())
    return ApiSuccess(data={"checks": checks, "ok": all(checks.values())})


@app.get("/api/v1/chat/conversations", tags=["Conversations"])
async def list_chat_conversations(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Danh sách hội thoại của tài khoản đang đăng nhập."""
    with UserDB() as db:
        conversations = db.list_conversations(current_user["email"], limit=limit, offset=offset)
    return ApiSuccess(data={"conversations": conversations})


@app.post("/api/v1/chat/conversations", tags=["Conversations"])
async def create_chat_conversation(
    request: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Tạo hội thoại mới cho tài khoản đang đăng nhập."""
    with UserDB() as db:
        conversation = db.create_conversation(current_user["email"], title=request.title)
    return ApiSuccess(data={"conversation": conversation})


@app.get("/api/v1/chat/conversations/{conversation_id}/messages", tags=["Conversations"])
async def get_chat_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lấy messages của một hội thoại thuộc user."""
    with UserDB() as db:
        messages = db.get_conversation_messages(current_user["email"], conversation_id)
    if messages is None:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Cuộc hội thoại không tồn tại.",
                error_code="CONVERSATION_NOT_FOUND"
            ).model_dump()
        )
    return ApiSuccess(data={"messages": messages})


@app.patch("/api/v1/chat/conversations/{conversation_id}", tags=["Conversations"])
async def update_chat_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Đổi title hội thoại."""
    with UserDB() as db:
        conversation = db.update_conversation_title(
            current_user["email"], conversation_id, request.title
        )
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Cuộc hội thoại không tồn tại.",
                error_code="CONVERSATION_NOT_FOUND"
            ).model_dump()
        )
    return ApiSuccess(data={"conversation": conversation})


@app.delete("/api/v1/chat/conversations/{conversation_id}", tags=["Conversations"])
async def delete_chat_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Xóa hội thoại thuộc user."""
    with UserDB() as db:
        deleted = db.delete_conversation(current_user["email"], conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Cuộc hội thoại không tồn tại.",
                error_code="CONVERSATION_NOT_FOUND"
            ).model_dump()
        )
    return ApiSuccess(message="Đã xóa hội thoại", data={"deleted": True})


@app.post("/api/v1/chat/conversations/{conversation_id}/messages", tags=["Conversations"])
async def send_chat_conversation_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Gửi message; câu chào thuần túy được xử lý miễn phí."""
    question = validate_question(request.question)
    user_email = current_user["email"]
    greeting_answer = get_greeting_response(question)

    with UserDB() as db:
        if not db.get_conversation(user_email, conversation_id):
            raise HTTPException(
                status_code=404,
                detail=ApiError(
                    message="Cuộc hội thoại không tồn tại.",
                    error_code="CONVERSATION_NOT_FOUND"
                ).model_dump()
            )

        if greeting_answer:
            saved = db.save_free_chat_exchange(
                user_email=user_email,
                conversation_id=conversation_id,
                question=question,
                answer=greeting_answer,
            )
            return build_free_greeting_response(
                answer=greeting_answer,
                saved=saved,
                conversation_id=conversation_id,
            )

        if db.get_token_balance(user_email) <= 0:
            raise_insufficient_tokens()

    try:
        answer, sources, response_time, num_docs = run_chat_workflow(question, request.prompt or "")
        input_tokens = get_chat_token_count(question)
        output_tokens = get_chat_token_count(answer)

        with UserDB() as db:
            saved = db.save_chat_exchange_and_debit(
                user_email=user_email,
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                sources=sources,
                response_time=response_time,
                num_docs=num_docs,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        if not saved:
            raise_insufficient_tokens("Không đủ token để lưu câu trả lời này.")

        response_data = ChatResponseData(
            answer=answer,
            sources=sources,
            response_time=response_time,
            num_docs_retrieved=num_docs,
            num_docs_graded=num_docs,
            token_used=saved["token_used"],
            conversation_id=conversation_id,
            balance=saved["balance"],
        ).model_dump()
        response_data.update({
            "user_message": saved["user_message"],
            "bot_message": saved["bot_message"],
            "conversation": saved["conversation"],
        })

        return ApiSuccess(message="Trả lời thành công", data=response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý chat conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message="Lỗi xử lý yêu cầu. Vui lòng thử lại sau.",
                error_code="CHAT_PROCESSING_ERROR"
            ).model_dump()
        )


@app.post("/api/chat", tags=["Chat"])
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Gửi câu hỏi và nhận câu trả lời từ chatbot.
    Yêu cầu đăng nhập (JWT token).
    """
    question = validate_question(request.question)
    user_email = current_user["email"]
    greeting_answer = get_greeting_response(question)

    try:
        with UserDB() as db:
            if not greeting_answer and db.get_token_balance(user_email) <= 0:
                raise_insufficient_tokens()

            conversation = (
                db.get_conversation(user_email, request.conversation_id)
                if request.conversation_id else
                db.create_conversation(user_email, title=question[:40])
            )

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail=ApiError(
                        message="Cuộc hội thoại không tồn tại.",
                        error_code="CONVERSATION_NOT_FOUND"
                    ).model_dump()
                )

            if greeting_answer:
                saved = db.save_free_chat_exchange(
                    user_email=user_email,
                    conversation_id=conversation["id"],
                    question=question,
                    answer=greeting_answer,
                )
                return build_free_greeting_response(
                    answer=greeting_answer,
                    saved=saved,
                    conversation_id=conversation["id"],
                )

        answer, sources, response_time, num_docs = run_chat_workflow(question)
        input_tokens = get_chat_token_count(question)
        output_tokens = get_chat_token_count(answer)

        with UserDB() as db:
            saved = db.save_chat_exchange_and_debit(
                user_email=user_email,
                conversation_id=conversation["id"],
                question=question,
                answer=answer,
                sources=sources,
                response_time=response_time,
                num_docs=num_docs,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        if not saved:
            raise_insufficient_tokens("Không đủ token để lưu câu trả lời này.")

        response_data = ChatResponseData(
            answer=answer,
            sources=sources,
            response_time=response_time,
            num_docs_retrieved=num_docs,
            num_docs_graded=num_docs,
            token_used=saved["token_used"],
            conversation_id=conversation["id"],
            balance=saved["balance"],
        )
        data = response_data.model_dump()
        data.update({
            "user_message": saved["user_message"],
            "bot_message": saved["bot_message"],
            "conversation": saved["conversation"],
        })

        return ApiSuccess(message="Trả lời thành công", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message="Lỗi xử lý yêu cầu. Vui lòng thử lại sau.",
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

task_store: dict[str, dict] = {}  # In-memory store cho task status
task_store_lock = RLock()
last_task_cleanup = 0.0


def _set_task_status(task_id: str, values: dict) -> None:
    """Cập nhật task store có lock để tránh race giữa worker và polling."""
    with task_store_lock:
        current = task_store.get(task_id, {})
        task_store[task_id] = {
            **current,
            **values,
            "updated_at": time.time(),
        }


def _cleanup_task_store(force: bool = False) -> None:
    """Dọn task cũ theo TTL để tránh leak RAM."""
    global last_task_cleanup

    now = time.time()
    task_config = get_task_config()
    if not force and now - last_task_cleanup < task_config["cleanup_interval"]:
        return

    with task_store_lock:
        last_task_cleanup = now

        for task_id, task in list(task_store.items()):
            status = task.get("status")
            updated_at = float(task.get("updated_at", task.get("start_time", now)))
            start_time = float(task.get("start_time", updated_at))

            if status == "processing" and now - start_time > task_config["processing_timeout"]:
                task_store[task_id] = {
                    **task,
                    "status": "failed",
                    "error": "Task quá thời gian xử lý.",
                    "updated_at": now,
                }
                continue

            if status in {"done", "failed"} and now - updated_at > task_config["result_ttl"]:
                del task_store[task_id]


class TaskRequest(BaseModel):
    """Schema cho yêu cầu tạo task bất đồng bộ."""
    question: str
    prompt: Optional[str] = None


def _heavy_chat_worker(
    task_id: str,
    question: str,
    prompt: str,
    user_email: str,
):
    """
    Worker chạy trong background thread cho tác vụ AI nặng.
    Hàm đồng bộ (def) để FastAPI chạy trong ThreadPool riêng,
    tránh gây nghẽn Event Loop.
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

        input_tokens = get_chat_token_count(question)
        output_tokens = get_chat_token_count(answer)
        actual_tokens = input_tokens + output_tokens
        token_used = 1

        with UserDB() as db:
            balance = db.debit_user_tokens(user_email, token_used, f"async_chat:{task_id}:actual_tokens={actual_tokens}")
        if balance is None:
            _set_task_status(task_id, {
                "status": "failed",
                "error": "INSUFFICIENT_TOKENS",
            })
            return

        # Cập nhật store
        _set_task_status(task_id, {
            "status": "done",
            "result": {
                "answer": answer,
                "sources": sources,
                "response_time": round(elapsed, 2),
                "num_docs": len(docs),
                "token_used": token_used,
            }
        })

        # Lưu lịch sử nếu có user
        if user_email:
            try:
                with UserDB() as db:
                    db.save_chat_message(
                        user_email=user_email, role="user", content=question,
                        token_used=input_tokens
                    )
                    db.save_chat_message(
                        user_email=user_email, role="bot", content=answer,
                        sources=sources, response_time=round(elapsed, 2),
                        num_docs=len(docs), token_used=output_tokens
                    )
            except Exception as db_err:
                logger.warning(f"Không thể lưu lịch sử task: {db_err}")

        logger.info(f"Task {task_id} hoàn thành sau {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Task {task_id} thất bại: {e}", exc_info=True)
        _set_task_status(task_id, {
            "status": "failed",
            "error": str(e),
        })


@app.post("/api/task/chat", tags=["Async Task"])
async def start_chat_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Khởi tạo tác vụ chat bất đồng bộ (background).
    Trả về task_id ngay lập tức, frontend polling để lấy kết quả.
    Yêu cầu đăng nhập (JWT token).
    """
    question = validate_question(request.question)
    task_id = str(uuid.uuid4())
    user_email = current_user["email"]
    greeting_answer = get_greeting_response(question)

    if greeting_answer:
        with UserDB() as db:
            balance = db.get_token_balance(user_email)
            db.save_chat_message(
                user_email=user_email,
                role="user",
                content=question,
                token_used=0,
            )
            db.save_chat_message(
                user_email=user_email,
                role="bot",
                content=greeting_answer,
                sources=[],
                response_time=0.0,
                num_docs=0,
                token_used=0,
            )

        _cleanup_task_store()
        _set_task_status(task_id, {
            "status": "done",
            "result": {
                "answer": greeting_answer,
                "sources": [],
                "response_time": 0.0,
                "num_docs": 0,
                "token_used": 0,
                "balance": balance,
                "is_free_greeting": True,
            },
        })
        return ApiSuccess(
            message="Phản hồi chào hỏi miễn phí",
            data={"task_id": task_id, "status": "done"},
        )

    with UserDB() as db:
        if db.get_token_balance(user_email) <= 0:
            raise_insufficient_tokens()

    get_chatbot()  # Kiểm tra chatbot sẵn sàng sau khi token hợp lệ

    # Đánh dấu trạng thái đang xử lý
    _cleanup_task_store()
    _set_task_status(task_id, {"status": "processing", "start_time": time.time()})

    # Đẩy vào background task
    background_tasks.add_task(
        _heavy_chat_worker, task_id, question, request.prompt, user_email
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
    _cleanup_task_store()
    with task_store_lock:
        task = task_store.get(task_id)
        task = dict(task) if task else None

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
    elif task["status"] == "failed":
        response_data["error"] = task.get("error", "Lỗi không xác định")

    return ApiSuccess(data=response_data)


# ------------------------------------------------------------------
# Safe File Download (skill_security_authentication.md Muc 4)
# Chong Path Traversal voi os.path.basename()
# ------------------------------------------------------------------
SAFE_DOWNLOAD_DIR = PROJECT_ROOT / "utils" / "download"


@app.get("/api/v1/download/{filename}", tags=["File"])
async def download_file(filename: str):
    """
    Tai file tu thu muc an toan (utils/download/).
    Chong Path Traversal: Loai bo moi ky tu '../' bang os.path.basename().
    """
    # 1. Triet tieu cac chuoi "../" nguy hiem
    safe_filename = os.path.basename(filename)

    # 2. Rap vao duong dan goc mot cach an toan
    file_path = SAFE_DOWNLOAD_DIR / safe_filename

    # 3. Kiem tra file ton tai
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="File khong ton tai.",
                error_code="FILE_NOT_FOUND"
            ).model_dump()
        )

    return FileResponse(str(file_path))


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

    port = get_runtime_int("PORT", 8001)
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    logger.info(f"API Docs: http://localhost:{port}/docs")

    uvicorn.run(
        "chatbot.services.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,  # 1 worker vì model embedding dùng chung
    )
