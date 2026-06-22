"""
对话记忆模块 — 保存多轮对话历史、工具调用记录
支持跨轮次上下文引用
"""
from dataclasses import dataclass, field
import time


@dataclass
class AgentStep:
    """Agent 执行的单个步骤"""
    step_type: str          # "thought" | "tool_call" | "tool_result" | "answer"
    content: str            # 文本内容
    tool_name: str = ""     # 工具名称（如果有）
    tool_input: str = ""    # 工具输入参数
    tool_output: str = ""   # 工具输出
    timestamp: float = field(default_factory=time.time)
    success: bool = True


class AgentMemory:
    """
    Agent 记忆模块

    存储:
    - 完整对话 messages（供 LLM 上下文使用）
    - 结构化步骤记录（供前端渲染思考过程）
    - 任务统计
    """

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.messages: list[dict] = []
        self.steps: list[AgentStep] = []
        self.stats = {
            "total_tasks": 0,
            "total_tool_calls": 0,
            "total_retries": 0,
        }

    def add_system(self, content: str):
        """添加系统消息"""
        self.messages.append({"role": "system", "content": content})

    def add_user(self, content: str):
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
        self.steps.append(AgentStep(step_type="user", content=content))
        self.stats["total_tasks"] += 1

    def add_assistant(self, content: str = "", tool_calls: list = None):
        """添加助手回复"""
        msg = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

        if content and not tool_calls:
            self.steps.append(AgentStep(step_type="answer", content=content[:500]))

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """添加工具执行结果"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })
        self.steps.append(AgentStep(
            step_type="tool_result",
            content=result[:500],
            tool_name=tool_name,
            tool_output=result[:500],
        ))
        self.stats["total_tool_calls"] += 1

    def add_retry(self, error: str, fix: str):
        """记录重试过程"""
        self.steps.append(AgentStep(
            step_type="tool_call",
            content=f"重试修复: {error[:100]} -> {fix[:100]}",
            success=False,
        ))
        self.stats["total_retries"] += 1

    def trim(self):
        """裁剪历史消息，保持在 max_history 以内"""
        if len(self.messages) > self.max_history:
            # 保留 system prompt + 最近的消息
            reserved = [m for m in self.messages if m["role"] == "system"]
            recent = self.messages[-(self.max_history - len(reserved)):]
            self.messages = reserved + recent

    def get_stats(self) -> dict:
        return self.stats
