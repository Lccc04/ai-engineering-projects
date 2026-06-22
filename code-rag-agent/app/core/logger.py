"""
统一日志模块 — loguru 全链路追踪
覆盖：请求日志、模型调用、工具执行、异常记录
"""
import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 移除默认 handler
logger.remove()

# 控制台输出（彩色）
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 全量日志文件（按天轮转）
logger.add(
    LOG_DIR / "agent_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)

# 错误日志单独文件
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name} | {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
)

# 工具调用日志
tool_logger = logger.bind(category="tool")
api_logger = logger.bind(category="api")
agent_logger = logger.bind(category="agent")


def log_tool_call(tool_name: str, args: str, result: str, elapsed_ms: float, success: bool):
    """工具调用专用日志"""
    status = "OK" if success else "FAIL"
    tool_logger.info(f"[{tool_name}] ({elapsed_ms:.0f}ms) [{status}] args={args[:100]} result={result[:100]}")


def log_api_call(messages_count: int, model: str, elapsed_ms: float, success: bool):
    """API 调用专用日志"""
    status = "OK" if success else "FAIL"
    api_logger.info(f"API[{model}] msgs={messages_count} ({elapsed_ms:.0f}ms) [{status}]")


def log_agent_phase(phase: str, detail: str = ""):
    """Agent 阶段日志"""
    agent_logger.info(f"Phase.{phase} {detail}")


__all__ = ["logger", "tool_logger", "api_logger", "agent_logger",
           "log_tool_call", "log_api_call", "log_agent_phase"]
