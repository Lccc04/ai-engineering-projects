"""
元数据标注器 — 给每个 chunk 打标签
提取：模块名、函数名、类名、文档类型、行号范围
"""
import re
import ast
from dataclasses import dataclass, field


@dataclass
class ChunkMetadata:
    """Chunk 元数据"""
    file_path: str           # 来源文件路径
    file_name: str           # 文件名
    file_type: str           # python | markdown | rst | config
    module_path: str = ""    # 模块路径
    function_name: str = ""  # 函数名（Python）
    class_name: str = ""     # 类名（Python）
    chunk_type: str = ""     # source_code | doc_page | config | docstring
    line_start: int = 0      # 起始行号
    line_end: int = 0        # 结束行号

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "module_path": self.module_path,
            "function_name": self.function_name,
            "class_name": self.class_name,
            "chunk_type": self.chunk_type,
            "line_range": f"{self.line_start}-{self.line_end}",
        }

    def to_label(self) -> str:
        """生成人类可读标签"""
        parts = [self.file_name]
        if self.module_path:
            parts.append(self.module_path)
        if self.class_name:
            parts.append(self.class_name)
        if self.function_name:
            parts.append(self.function_name)
        if self.line_start or self.line_end:
            parts.append(f"L{self.line_start}-{self.line_end}")
        return " | ".join(parts)


class MetadataExtractor:
    """
    元数据提取器

    策略：
    - Python 文件：AST 解析，提取函数/类/方法定义位置
    - Markdown 文件：正则匹配标题
    - 其他：基于文本特征推断
    """

    # 匹配 Python 函数/类定义的正则（用于 chunk 级别匹配）
    FUNC_PATTERN = re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE)
    CLASS_PATTERN = re.compile(r'^\s*class\s+(\w+)\s*[:\(]', re.MULTILINE)
    # Markdown 标题
    HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)

    def extract(self, chunk_text: str, doc) -> ChunkMetadata:
        """
        从 chunk 文本中提取元数据

        Args:
            chunk_text: 分块后的文本
            doc: 原始 ParsedDocument

        Returns:
            ChunkMetadata
        """
        meta = ChunkMetadata(
            file_path=doc.file_path,
            file_name=doc.file_name,
            file_type=doc.file_type,
            module_path=doc.module_path,
        )

        # 推断 chunk 类型
        meta.chunk_type = self._infer_chunk_type(chunk_text, doc.file_type)

        if doc.file_type == "python":
            meta = self._extract_python_meta(chunk_text, doc, meta)
        elif doc.file_type in ("markdown", "rst"):
            meta = self._extract_doc_meta(chunk_text, doc, meta)

        # 估算行号范围（从原始文档中搜索）
        meta.line_start, meta.line_end = self._find_line_range(chunk_text, doc)

        return meta

    def _extract_python_meta(self, chunk_text: str, doc, meta: ChunkMetadata) -> ChunkMetadata:
        """Python chunk 元数据提取"""
        # 提取类名
        class_matches = self.CLASS_PATTERN.findall(chunk_text)
        if class_matches:
            meta.class_name = class_matches[0]  # 取第一个类定义

        # 提取函数名
        func_matches = self.FUNC_PATTERN.findall(chunk_text)
        if func_matches:
            # 找到最相关的函数（chunk 中最长的函数定义）
            meta.function_name = max(func_matches, key=len) if len(func_matches) > 1 else func_matches[0]

        # AST 级提取（更精确）
        try:
            tree = ast.parse(chunk_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not meta.function_name:
                    meta.function_name = node.name
                elif isinstance(node, ast.ClassDef) and not meta.class_name:
                    meta.class_name = node.name
        except SyntaxError:
            pass  # 不完整代码片段 AST 解析失败是正常的

        return meta

    def _extract_doc_meta(self, chunk_text: str, doc, meta: ChunkMetadata) -> ChunkMetadata:
        """Markdown/RST chunk 元数据提取"""
        heading_matches = self.HEADING_PATTERN.findall(chunk_text)
        if heading_matches:
            meta.function_name = heading_matches[0]  # 用标题作为标识
        return meta

    @staticmethod
    def _infer_chunk_type(chunk_text: str, file_type: str) -> str:
        """推断 chunk 类型"""
        if file_type == "python":
            # 检测是否是 docstring
            stripped = chunk_text.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                return "docstring"
            return "source_code"
        elif file_type in ("markdown", "rst"):
            return "doc_page"
        elif file_type == "config":
            return "config"
        return "unknown"

    @staticmethod
    def _find_line_range(chunk_text: str, doc) -> tuple[int, int]:
        """在原始文档中查找 chunk 的行号范围"""
        # 取 chunk 前 80 字符作为搜索锚点
        anchor = chunk_text.strip()[:80]
        if not anchor:
            return 0, 0

        for i, line in enumerate(doc.lines):
            if anchor in line:
                # 粗略估算：chunk 行数 ≈ chunk 字符数 / 平均行长
                avg_line_len = max(1, sum(len(l) for l in doc.lines) // max(1, len(doc.lines)))
                chunk_lines = len(chunk_text) // max(1, avg_line_len)
                return i + 1, i + chunk_lines + 1

        return 0, 0
