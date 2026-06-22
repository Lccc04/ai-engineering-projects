"""
人机协同模块 — 高风险操作前要求人工确认
"""
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"        # 无需确认
    MEDIUM = "medium"   # 提示但自动执行
    HIGH = "high"      # 必须确认
    CRITICAL = "critical"  # 禁止执行


@dataclass
class ConfirmRequest:
    """确认请求"""
    tool_name: str
    action: str
    details: str
    risk_level: RiskLevel
    risk_reason: str = ""


class HumanInTheLoop:
    """
    人机协同风控

    原则：
    - 读操作：LOW，无需确认
    - 写操作(新建)：MEDIUM，提示即可
    - 写操作(覆盖)：HIGH，需确认
    - 删除/系统调用：CRITICAL，禁止
    """

    # 工具操作风险分级
    RISK_MAP = {
        # python_runner
        ("python_runner", "print"): RiskLevel.LOW,
        ("python_runner", "import os"): RiskLevel.CRITICAL,
        ("python_runner", "subprocess"): RiskLevel.CRITICAL,
        # file_manager
        ("file_manager", "read"): RiskLevel.LOW,
        ("file_manager", "list"): RiskLevel.LOW,
        ("file_manager", "save"): RiskLevel.MEDIUM,
        # kb_search
        ("kb_search", "query"): RiskLevel.LOW,
    }

    @classmethod
    def assess(cls, tool_name: str, arguments: dict) -> ConfirmRequest:
        """
        评估是否需要确认

        Returns:
            ConfirmRequest (risk_level=HIGH 时需要前端弹窗)
        """
        action = arguments.get("action", "")

        # 特例：file_manager save 时检查是否覆盖已有文件
        if tool_name == "file_manager" and action == "save":
            path = arguments.get("path", "")
            from app.core.config import settings
            full_path = settings.workspace_dir / path
            if full_path.exists():
                return ConfirmRequest(
                    tool_name=tool_name,
                    action="save",
                    details=f"将覆盖已有文件: {path} (大小: {full_path.stat().st_size} bytes)",
                    risk_level=RiskLevel.HIGH,
                    risk_reason="文件将被覆盖，原有内容不可恢复",
                )

        # 通用风险判定
        risk = cls.RISK_MAP.get((tool_name, action), RiskLevel.LOW)
        return ConfirmRequest(
            tool_name=tool_name,
            action=action,
            details=str(arguments)[:200],
            risk_level=risk,
        )
