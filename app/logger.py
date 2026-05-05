"""
Module logger chuan cho toan bo du an.
Moi module goi get_logger(__name__) de co logger rieng, de loc log.

Tham chieu: docs/DOCS-main/skill_logging_monitoring.md
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def get_logger(name: str) -> logging.Logger:
    """
    Tao va tra ve mot logger da duoc cau hinh chuan.
    Moi module goi ham nay voi __name__ de co logger rieng, de loc log.

    Args:
        name: Ten logger, thuong truyen __name__ cua module goi.

    Returns:
        Logger da cau hinh voi console handler va file handler.
    """
    logger = logging.getLogger(name)

    # Tranh them handler trung lap neu ham duoc goi nhieu lan
    if logger.handlers:
        return logger

    log_level = logging.DEBUG if os.getenv("ENV", "production") == "development" else logging.INFO
    logger.setLevel(log_level)

    # Format chuan: thoi gian - ten module - muc do - noi dung
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1: In ra console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler 2: Ghi ra file (tu dong xoay vong khi qua 5MB, giu toi da 3 file)
    # Tim DIR_ROOT tu config hoac dung thu muc hien tai
    dir_root = os.getenv("DIR_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(dir_root, "utils", "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB moi file
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
