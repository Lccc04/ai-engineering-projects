"""
工具基类 — 统一接口 + JSON Schema 生成
所有工具遵循 DeepSeek Function Calling 格式
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（LLM 用来判断何时调用）"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """参数 JSON Schema"""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具，返回字符串结果"""
        ...

    def to_openai_schema(self) -> dict:
        """生成 OpenAI / DeepSeek Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys()),
                },
            },
        }
