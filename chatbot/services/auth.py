"""
Authentication Router - Google OAuth 2.0 + Cloud-Sync Polling.

Endpoints:
    POST /auth/login-session          - Tạo phiên chờ đăng nhập
    GET  /auth/login-session/{id}     - Polling kiểm tra trạng thái
    GET  /auth/google/login/flutter   - Redirect đến Google OAuth
    GET  /auth/google/callback/flutter - Google callback -> JWT -> DB
    POST /auth/verify                 - Xác thực JWT token

Tham chiếu:
    - docs/DOCS-main/skill_hybrid_app_login.md
    - docs/DOCS-main/skill_google_oauth_redirect.md
    - docs/DOCS-main/skill_security_authentication.md
"""

from html import escape
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from chatbot.utils.base_db import UserDB
from chatbot.utils.jwt_utils import create_jwt_token, verify_jwt_token
from app.config import settings
from app.models.schemas import ApiSuccess, ApiError
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ------------------------------------------------------------------
# Google OAuth 2.0 Config
# ------------------------------------------------------------------
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
OAUTH_REDIRECT_URI = settings.OAUTH_REDIRECT_URI

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ------------------------------------------------------------------
# 1. Tạo phiên chờ đăng nhập
# ------------------------------------------------------------------
@router.post("/login-session")
async def create_login_session(session_id: str = Form(...)):
    """
    Tạo phiên chờ đăng nhập mới.

    Frontend gọi API này với một session_id ngẫu nhiên (UUID)
    trước khi bắt đầu polling và mở trình duyệt đăng nhập.
    """
    with UserDB() as db:
        db.cleanup_old_sessions()
        success = db.create_login_session(session_id)
        if not success:
            raise HTTPException(
                status_code=409,
                detail=ApiError(
                    message="Session ID đã tồn tại.",
                    error_code="SESSION_CONFLICT"
                ).model_dump()
            )

    return ApiSuccess(
        message="Tạo phiên đăng nhập thành công",
        data={"status": "created", "session_id": session_id}
    )


# ------------------------------------------------------------------
# 2. Polling kiểm tra trạng thái đăng nhập
# ------------------------------------------------------------------
@router.get("/login-session/{session_id}")
async def get_login_session(session_id: str):
    """
    Kiểm tra trạng thái phiên đăng nhập.

    Frontend gọi API này mỗi 2 giây để kiểm tra xem người dùng
    đã hoàn tất đăng nhập Google chưa.

    Nếu status == 'completed', trả về token và thông tin user.
    Session sẽ bị XÓA NGAY (one-time use) sau khi trả token.
    """
    with UserDB() as db:
        session = db.get_login_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Session không tồn tại hoặc đã hết hạn.",
                error_code="SESSION_NOT_FOUND"
            ).model_dump()
        )

    result = {"status": session["status"]}

    if session["status"] == "completed" and session["token"]:
        result["token"] = session["token"]
        result["user"] = {
            "email": session.get("user_email"),
            "name": session.get("user_name"),
            "picture": session.get("user_picture"),
        }

    return result


# ------------------------------------------------------------------
# 3. Redirect đến Google OAuth
# ------------------------------------------------------------------
@router.get("/google/login/flutter")
async def google_login_flutter(session_id: str):
    """
    Redirect người dùng đến trang đăng nhập Google.

    session_id được truyền qua tham số 'state' của OAuth
    để callback có thể liên kết kết quả với phiên đúng.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message="GOOGLE_CLIENT_ID chưa được cấu hình trong .env",
                error_code="MISSING_CONFIG"
            ).model_dump()
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": session_id,
        "access_type": "offline",
        "prompt": "select_account consent",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    return RedirectResponse(url=auth_url)


# ------------------------------------------------------------------
# 4. Google OAuth Callback
# ------------------------------------------------------------------
@router.get("/google/callback/flutter")
async def google_callback_flutter(code: str, state: str):
    """
    Callback từ Google sau khi người dùng đăng nhập thành công.

    1. Exchange authorization code -> access token
    2. Lấy thông tin user từ Google
    3. Tạo JWT token
    4. Cập nhật vào DB ứng với session_id (state)
    5. Trả về trang HTML thông báo thành công
    """
    session_id = state

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail=ApiError(
                message="Google OAuth credentials chưa được cấu hình.",
                error_code="MISSING_CONFIG"
            ).model_dump()
        )

    # Verify session tồn tại và còn hiệu lực TRƯỚC khi dùng code Google
    with UserDB() as db:
        session = db.get_login_session(session_id)
    if not session:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
                error_code="INVALID_SESSION"
            ).model_dump()
        )

    # Step 1: Exchange code -> access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        logger.error(f"Google token exchange thất bại: {token_response.text}")
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không thể lấy token từ Google.",
                error_code="GOOGLE_TOKEN_ERROR"
            ).model_dump()
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không nhận được access token từ Google.",
                error_code="NO_ACCESS_TOKEN"
            ).model_dump()
        )

    # Step 2: Lấy thông tin user
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không thể lấy thông tin user từ Google.",
                error_code="GOOGLE_USERINFO_ERROR"
            ).model_dump()
        )

    user_info = userinfo_response.json()
    logger.info(f"Đăng nhập thành công: {user_info.get('email')}")

    # Step 3: Tạo JWT token
    jwt_token = create_jwt_token({
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
    })

    # Step 4: Cập nhật DB
    with UserDB() as db:
        db.update_login_session(
            session_id=session_id,
            token=jwt_token,
            user_email=user_info.get("email"),
            user_name=user_info.get("name"),
            user_picture=user_info.get("picture"),
        )

    # Step 5: Trả về trang HTML thành công (không dùng emoji)
    user_name = escape(user_info.get("name") or "bạn")
    success_html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Đăng nhập thành công</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: #0a0e1a;
                color: #e8ecf4;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .card {{
                text-align: center;
                padding: 3rem 2.5rem;
                background: rgba(26, 31, 53, 0.9);
                border: 1px solid #1e2a4a;
                border-radius: 20px;
                backdrop-filter: blur(20px);
                max-width: 420px;
                animation: fadeIn 0.5s ease;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .icon {{
                width: 64px; height: 64px;
                margin: 0 auto 1rem;
                border-radius: 50%;
                background: linear-gradient(135deg, #34d399, #059669);
                display: flex; align-items: center; justify-content: center;
            }}
            .icon svg {{ stroke: white; }}
            h2 {{
                font-size: 1.5rem;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.75rem;
            }}
            p {{
                color: #8892a8;
                font-size: 0.95rem;
                line-height: 1.6;
            }}
            .name {{
                color: #667eea;
                font-weight: 600;
            }}
            .hint {{
                margin-top: 1.5rem;
                font-size: 0.8rem;
                color: #5a6478;
                padding: 0.75rem;
                border: 1px solid #1e2a4a;
                border-radius: 10px;
                background: rgba(102, 126, 234, 0.05);
            }}
        </style>
        <script>
            window.setTimeout(function () {{
                window.close();
            }}, 1200);
        </script>
    </head>
    <body>
        <div class="card">
            <div class="icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <h2>Đăng nhập thành công!</h2>
            <p>Xin chào, <span class="name">{user_name}</span>!</p>
            <p>Bạn đã đăng nhập vào Chatbot Kinh Tế thành công.</p>
            <div class="hint">
                Hãy <strong>đóng Tab này</strong> và quay lại ứng dụng.<br>
                Hệ thống sẽ tự động đăng nhập cho bạn.
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=success_html)


# ------------------------------------------------------------------
# 5. Xác thực JWT Token
# ------------------------------------------------------------------
@router.post("/verify")
async def verify_token(token: str = Form(...)):
    """
    Xác thực JWT token.

    Frontend gọi API này khi load trang để kiểm tra token
    lưu trong localStorage có còn hợp lệ không.
    """
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Token không hợp lệ hoặc đã hết hạn.",
                error_code="INVALID_TOKEN"
            ).model_dump()
        )

    return ApiSuccess(
        message="Token hợp lệ",
        data={
            "valid": True,
            "user": {
                "email": payload.get("email"),
                "name": payload.get("name"),
                "picture": payload.get("picture"),
            }
        }
    )
