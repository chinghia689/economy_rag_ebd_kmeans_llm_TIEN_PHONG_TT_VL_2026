"""Definitions for editable public privacy, terms, and support content."""

PRIVACY_TITLE_KEY = "PUBLIC_PRIVACY_TITLE"
PRIVACY_CONTENT_KEY = "PUBLIC_PRIVACY_CONTENT"
SUPPORT_TITLE_KEY = "PUBLIC_SUPPORT_TITLE"
SUPPORT_CONTENT_KEY = "PUBLIC_SUPPORT_CONTENT"
SUPPORT_EMAIL_KEY = "PUBLIC_SUPPORT_EMAIL"
TERMS_TITLE_KEY = "PUBLIC_TERMS_TITLE"
TERMS_CONTENT_KEY = "PUBLIC_TERMS_CONTENT"

PUBLIC_CONTENT_SETTING_KEYS = {
    PRIVACY_TITLE_KEY,
    PRIVACY_CONTENT_KEY,
    SUPPORT_TITLE_KEY,
    SUPPORT_CONTENT_KEY,
    SUPPORT_EMAIL_KEY,
    TERMS_TITLE_KEY,
    TERMS_CONTENT_KEY,
}

PUBLIC_CONTENT_SETTING_DEFINITIONS = [
    {
        "key": PRIVACY_TITLE_KEY,
        "default": "Chính sách bảo mật",
        "is_secret": 0,
        "description": "Tiêu đề trang chính sách bảo mật hiển thị công khai.",
    },
    {
        "key": PRIVACY_CONTENT_KEY,
        "default": (
            "Chúng tôi chỉ thu thập dữ liệu cần thiết để vận hành tài khoản và cung cấp dịch vụ.\n\n"
            "## Dữ liệu được lưu\n\n"
            "- Email và thông tin hồ sơ dùng để xác thực tài khoản.\n"
            "- Hội thoại, lịch sử credit và thanh toán dùng để cung cấp và đối soát dịch vụ.\n\n"
            "## Cách dữ liệu được sử dụng\n\n"
            "Dữ liệu được dùng để trả lời câu hỏi, lưu lịch sử, quản lý credit, hỗ trợ người dùng và bảo vệ hệ thống. "
            "Hội thoại không được công khai giữa các tài khoản.\n\n"
            "## Quyền của người dùng\n\n"
            "Bạn có thể tự xóa tài khoản trong giao diện hoặc liên hệ bộ phận hỗ trợ. Sau khi xóa, "
            "hệ thống chỉ giữ email trong danh sách chặn để ngăn tài khoản đó đăng nhập lại."
        ),
        "is_secret": 0,
        "description": "Nội dung Markdown của trang chính sách bảo mật.",
    },
    {
        "key": TERMS_TITLE_KEY,
        "default": "Điều khoản sử dụng",
        "is_secret": 0,
        "description": "Tiêu đề trang điều khoản sử dụng hiển thị công khai.",
    },
    {
        "key": TERMS_CONTENT_KEY,
        "default": (
            "Dịch vụ phục vụ tra cứu và nghiên cứu thông tin kinh tế, không thay thế tư vấn "
            "tài chính hoặc pháp lý chuyên nghiệp.\n\n"
            "## Trách nhiệm của người dùng\n\n"
            "- Kiểm chứng nguồn trước khi ra quyết định.\n"
            "- Không sử dụng hệ thống cho hành vi vi phạm pháp luật.\n"
            "- Bảo vệ thông tin đăng nhập và chịu trách nhiệm cho hoạt động trên tài khoản.\n\n"
            "## Credit và tài khoản\n\n"
            "Credit đã sử dụng không được hoàn lại. Khi tài khoản bị xóa, email đã dùng sẽ bị "
            "chặn và không thể đăng nhập lại."
        ),
        "is_secret": 0,
        "description": "Nội dung Markdown của trang điều khoản sử dụng.",
    },
    {
        "key": SUPPORT_TITLE_KEY,
        "default": "Hỗ trợ",
        "is_secret": 0,
        "description": "Tiêu đề trang hỗ trợ hiển thị công khai.",
    },
    {
        "key": SUPPORT_CONTENT_KEY,
        "default": (
            "Nếu gặp vấn đề khi đăng nhập, sử dụng chatbot, nạp credit hoặc xem lịch sử giao dịch, "
            "hãy gửi mô tả chi tiết cho bộ phận hỗ trợ.\n\n"
            "## Thông tin nên cung cấp\n\n"
            "- Email tài khoản đang sử dụng.\n"
            "- Thời điểm xảy ra sự cố.\n"
            "- Ảnh chụp màn hình hoặc mã giao dịch, nếu có.\n\n"
            "Không gửi mật khẩu, API key hoặc mã xác thực trong yêu cầu hỗ trợ."
        ),
        "is_secret": 0,
        "description": "Nội dung Markdown của trang hỗ trợ.",
    },
    {
        "key": SUPPORT_EMAIL_KEY,
        "default": "",
        "is_secret": 0,
        "description": "Email hỗ trợ công khai; để trống nếu chưa sử dụng email hỗ trợ.",
    },
]


def public_content_from_settings(values: dict[str, str]) -> dict:
    """Convert flat runtime settings into the public API response shape."""
    return {
        "privacy": {
            "title": values.get(PRIVACY_TITLE_KEY, "Chính sách bảo mật"),
            "content": values.get(PRIVACY_CONTENT_KEY, ""),
        },
        "terms": {
            "title": values.get(TERMS_TITLE_KEY, "Điều khoản sử dụng"),
            "content": values.get(TERMS_CONTENT_KEY, ""),
        },
        "support": {
            "title": values.get(SUPPORT_TITLE_KEY, "Hỗ trợ"),
            "content": values.get(SUPPORT_CONTENT_KEY, ""),
            "email": values.get(SUPPORT_EMAIL_KEY, ""),
        },
    }
