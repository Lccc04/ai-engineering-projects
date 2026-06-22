"""
Python 代码执行工具 — 安全沙箱包装
Function Calling 定义: 输入 Python 代码字符串，在隔离环境中执行并返回结果
"""
from app.tools.base import BaseTool
from app.sandbox.executor import SandboxExecutor
from app.core.config import settings


class PythonRunnerTool(BaseTool):
    """
    安全 Python 代码执行器

    用法示例（LLM 调用）：
    python_runner(code="print(1+2)")

    特性：
    - 30秒超时自动终止
    - 禁止网络和系统调用
    - 捕获 stdout/stderr/traceback
    """

    @property
    def name(self) -> str:
        return "python_runner"

    @property
    def description(self) -> str:
        return (
            "在安全沙箱中执行 Python 代码。支持 print 输出、pandas/numpy 数据分析、"
            "matplotlib 图表生成。禁止网络访问、文件系统写入和系统命令。"
            "如果代码执行出错，会返回详细的错误信息和堆栈跟踪。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "code": {
                "type": "string",
                "description": "要执行的 Python 代码字符串。可以包含多条语句，使用 print() 输出结果。",
            },
        }

    def execute(self, code: str = "") -> str:
        if not code.strip():
            return "[错误] 代码为空"

        executor = SandboxExecutor(timeout=settings.sandbox_timeout)

        try:
            result = executor.execute(code.strip())
        except ValueError as e:
            return f"[安全拦截] {e}"

        if result["timed_out"]:
            return f"[超时] 代码执行超过 {settings.sandbox_timeout} 秒，已强制终止"

        if result["success"]:
            lines = [f"[执行成功] 耗时 {result['exec_time_ms']:.0f}ms"]
            if result["output"]:
                lines.append(result["output"])
            return "\n".join(lines)
        else:
            lines = [f"[执行失败] {result['error']}"]
            if result["output"]:
                lines.append(f"输出: {result['output']}")
            return "\n".join(lines)
