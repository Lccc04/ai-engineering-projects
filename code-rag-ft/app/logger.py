"""
统一日志模块（共用）— loguru
"""
import sys
from pathlib import Path
from loguru import logger

_LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

logger.add(
    _LOG_DIR / "ft_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {name}:{function} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)

logger.add(
    _LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
)
