"""
文件管理工具 — 安全读写本地文件
Function Calling 定义: 读取/保存/列出工作目录下的文件
"""
from pathlib import Path
from app.tools.base import BaseTool
from app.core.config import settings


class FileManagerTool(BaseTool):
    """
    文件管理器

    用法示例（LLM 调用）：
    file_manager(action="read", path="data.csv")
    file_manager(action="save", path="result.txt", content="...")
    file_manager(action="list")
    """

    def __init__(self):
        self.workspace = settings.workspace_dir
        self.workspace.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return (
            "管理本地工作目录中的文件。支持读取文件内容、保存新文件、列出已有文件。"
            "文件操作限制在工作目录内，无法访问系统文件。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "action": {
                "type": "string",
                "enum": ["read", "save", "list"],
                "description": "操作类型: read=读取文件, save=保存文件, list=列出文件",
            },
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录）。read/save 时必填。",
            },
            "content": {
                "type": "string",
                "description": "文件内容。save 操作时必填。",
            },
        }

    def execute(self, action: str = "", path: str = "", content: str = "") -> str:
        try:
            if action == "list":
                return self._list_files()

            if action == "read":
                return self._read_file(path)

            if action == "save":
                return self._save_file(path, content)

            return f"[错误] 未知操作: {action}，支持 read/save/list"
        except Exception as e:
            return f"[错误] 文件操作失败: {e}"

    def _resolve_path(self, path: str) -> Path:
        """安全路径解析 —— 防止路径穿越攻击"""
        safe_path = self.workspace / path.lstrip("/\\")
        safe_path = safe_path.resolve()
        if not str(safe_path).startswith(str(self.workspace.resolve())):
            raise PermissionError(f"禁止访问工作目录以外的文件: {path}")
        return safe_path

    def _list_files(self) -> str:
        files = list(self.workspace.glob("*"))
        if not files:
            return "工作目录为空"
        lines = ["工作目录文件:"]
        for f in sorted(files):
            if f.is_file():
                size = f.stat().st_size
                lines.append(f"  {f.name} ({size:,} bytes)")
        return "\n".join(lines)

    def _read_file(self, path: str) -> str:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            return f"[错误] 文件不存在: {path}"
        if file_path.stat().st_size > 10 * 1024 * 1024:
            return f"[错误] 文件过大 (>10MB): {path}"
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return f"=== {path} ===\n{content}"

    def _save_file(self, path: str, content: str) -> str:
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"[已保存] {path} ({len(content)} 字符)"
