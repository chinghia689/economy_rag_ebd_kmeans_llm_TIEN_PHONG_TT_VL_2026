"""
Module logger chuẩn cho toàn bộ dự án.
Mỗi module gọi get_logger(__name__) để có logger riêng, dễ lọc log.

Tham chiếu: docs/DOCS-main/skill_logging_monitoring.md
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def get_logger(name: str) -> logging.Logger:
    """
    Tạo và trả về một logger đã được cấu hình chuẩn.
    Mỗi module gọi hàm này với __name__ để có logger riêng, dễ lọc log.

    Args:
        name: Tên logger, thường truyền __name__ của module gọi.

    Returns:
        Logger đã cấu hình với console handler và file handler.
    """
    logger = logging.getLogger(name)

    # Tránh thêm handler trùng lặp nếu hàm được gọi nhiều lần
    if logger.handlers:
        return logger

    log_level = logging.DEBUG if os.getenv("ENV", "production") == "development" else logging.INFO
    logger.setLevel(log_level)

    # Format chuẩn: thời gian - tên module - mức độ - nội dung
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1: In ra console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler 2: Ghi ra file (tự động xoay vòng khi quá 5MB, giữ tối đa 3 file)
    dir_root = os.getenv("DIR_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(dir_root, "utils", "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB mỗi file
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
