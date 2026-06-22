"""
语法感知分块器 — 使用 LangChain Language TextSplitter
按 Python 函数/类/模块边界切分，不截断语法单元

面试亮点：对比普通字符分块 vs 语法分块的召回率差异
"""
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
    PythonCodeTextSplitter,
    MarkdownTextSplitter,
    LatexTextSplitter,  # RST 最近似
)
from app.core.config import settings


class SyntaxAwareChunker:
    """
    语法感知分块器

    核心策略：
    - Python 文件 → PythonCodeTextSplitter（按函数/类切分）
    - Markdown 文件 → MarkdownTextSplitter（按标题/段落切分）
    - RST/Config → RecursiveCharacterTextSplitter（回退方案）
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        # Python 语法感知分块器
        self.python_splitter = PythonCodeTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        # Markdown 分块器
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        # 回退分块器（普通字符级递归分块）
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        # 用于消融实验的纯字符分块器
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk(self, text: str, file_type: str) -> list[str]:
        """
        根据文件类型选择分块策略

        Args:
            text: 文本内容
            file_type: python | markdown | rst | config

        Returns:
            分块文本列表
        """
        if file_type == "python":
            return self._chunk_with_splitter(self.python_splitter, text)
        elif file_type in ("markdown", "rst"):
            return self._chunk_with_splitter(self.markdown_splitter, text)
        else:
            return self._chunk_with_splitter(self.fallback_splitter, text)

    def chunk_char_only(self, text: str) -> list[str]:
        """
        纯字符分块（用于消融实验对照）

        Args:
            text: 文本内容

        Returns:
            分块文本列表
        """
        return self._chunk_with_splitter(self.char_splitter, text)

    @staticmethod
    def _chunk_with_splitter(splitter, text: str) -> list[str]:
        """安全调用分块器，处理空文本"""
        if not text or not text.strip():
            return []
        try:
            chunks = splitter.split_text(text)
            # 过滤空白块
            return [c for c in chunks if c.strip()]
        except Exception:
            # 极端情况降级为按行分块
            return [text[i:i+500] for i in range(0, len(text), 500)]
