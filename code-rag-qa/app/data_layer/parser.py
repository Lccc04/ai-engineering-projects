"""
代码文件解析器 — 支持 .py 源码、.md/.rst 文档、.toml/.cfg 配置
输出统一的 ParsedDocument
"""
import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """解析后的文档统一结构"""
    file_path: str          # 相对路径
    file_name: str          # 文件名
    file_type: str          # python | markdown | rst | config
    content: str            # 全文内容
    module_path: str = ""   # 模块路径（如 fastapi.routing）
    lines: list[str] = field(default_factory=list)  # 按行存储


class CodeParser:
    """统一代码文件解析器"""

    # 支持的文件扩展名
    PYTHON_EXTS = {".py", ".pyx", ".pyi"}
    DOC_EXTS = {".md", ".markdown", ".rst", ".txt"}
    CONFIG_EXTS = {".toml", ".cfg", ".ini", ".yaml", ".yml"}

    def parse_file(self, file_path: Path, root_dir: Path) -> ParsedDocument | None:
        """
        解析单个文件

        Args:
            file_path: 文件绝对路径
            root_dir: 语料根目录

        Returns:
            ParsedDocument 或 None（不支持的文件类型）
        """
        suffix = file_path.suffix.lower()
        rel_path = file_path.relative_to(root_dir)

        if suffix in self.PYTHON_EXTS:
            return self._parse_python(file_path, rel_path)
        elif suffix in self.DOC_EXTS:
            return self._parse_document(file_path, rel_path, "markdown" if suffix in {".md", ".markdown"} else "rst")
        elif suffix in self.CONFIG_EXTS:
            return self._parse_config(file_path, rel_path)
        else:
            return None

    def _parse_python(self, file_path: Path, rel_path: Path) -> ParsedDocument:
        """解析 Python 源文件"""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.split("\n")
        module_path = self._infer_module_path(rel_path)

        return ParsedDocument(
            file_path=str(rel_path),
            file_name=file_path.name,
            file_type="python",
            content=content,
            module_path=module_path,
            lines=lines,
        )

    def _parse_document(self, file_path: Path, rel_path: Path, doc_type: str) -> ParsedDocument:
        """解析 Markdown/RST 文档"""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return ParsedDocument(
            file_path=str(rel_path),
            file_name=file_path.name,
            file_type=doc_type,
            content=content,
            lines=content.split("\n"),
        )

    def _parse_config(self, file_path: Path, rel_path: Path) -> ParsedDocument:
        """解析配置文件"""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return ParsedDocument(
            file_path=str(rel_path),
            file_name=file_path.name,
            file_type="config",
            content=content,
            lines=content.split("\n"),
        )

    @staticmethod
    def _infer_module_path(rel_path: Path) -> str:
        """从文件路径推断 Python 模块路径"""
        # fastapi/routing.py → fastapi.routing
        # fastapi/dependencies/utils.py → fastapi.dependencies.utils
        parts = list(rel_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]  # 去掉 .py
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def parse_directory(self, root_dir: Path) -> list[ParsedDocument]:
        """
        遍历目录，解析所有支持的文件

        Args:
            root_dir: 语料根目录

        Returns:
            ParsedDocument 列表
        """
        documents = []
        for file_path in root_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # 跳过 __pycache__、.git 等
                if any(p.startswith(".") or p == "__pycache__" for p in file_path.parts):
                    continue
                doc = self.parse_file(file_path, root_dir)
                if doc:
                    documents.append(doc)

        print(f"[Parser] 解析完成: {len(documents)} 个文件")
        return documents
