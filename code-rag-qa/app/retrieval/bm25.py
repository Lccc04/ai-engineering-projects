"""
BM25 关键词检索 — 基于 jieba 分词 + rank_bm25
提供稀疏检索能力，与向量检索互补
"""
import jieba
from rank_bm25 import BM25Okapi
from app.core.config import settings


class BM25Retriever:
    """
    BM25 关键词检索器

    分词策略（代码场景适配）:
    - jieba 分词作为基础
    - 额外保留下划线连接的标识符（如 fastapi_routing → [fastapi, routing]）
    - 保留驼峰命名分割（APIRouter → [api, router]）
    """

    def __init__(self):
        self._corpus: list[list[str]] = []  # 分词后的文档列表
        self._chunks: list[dict] = []       # chunk 元数据
        self._bm25: BM25Okapi | None = None

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """
        代码感知分词

        策略:
        1. jieba 基础分词
        2. 识别 snake_case / camelCase 标识符并拆分
        3. 保留 Python 关键字和操作符
        """
        # jieba 分词
        tokens = list(jieba.cut(text.lower()))

        # 过滤空白和纯标点
        tokens = [t.strip() for t in tokens if t.strip() and not all(c in '.,;:()[]{}<>=' for c in t)]

        # 拆分下划线连接的复合词
        expanded = []
        for token in tokens:
            if '_' in token and len(token) > 3:
                parts = token.split('_')
                expanded.extend(p for p in parts if p)
            else:
                expanded.append(token)

        return expanded

    def index(self, chunks: list[dict]):
        """
        构建 BM25 索引

        Args:
            chunks: chunk 列表，每个包含 "text" 字段
        """
        self._chunks = chunks
        self._corpus = [self.tokenize(c["text"]) for c in chunks]
        self._bm25 = BM25Okapi(self._corpus)
        print(f"[BM25] 索引构建完成: {len(self._corpus)} 个文档")

    def search(self, query: str, k: int | None = None) -> list[dict]:
        """
        BM25 检索

        Args:
            query: 查询文本
            k: 返回 Top-K

        Returns:
            [{"chunk": {...}, "score": float}, ...]
        """
        if self._bm25 is None:
            return []

        k = k or settings.bm25_top_k
        query_tokens = self.tokenize(query)

        scores = self._bm25.get_scores(query_tokens)

        # 取 Top-K
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:min(k, len(scores))]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 过滤完全不匹配的
                results.append({
                    "chunk": self._chunks[idx],
                    "score": float(scores[idx]),
                })

        return results

    def get_scores(self, query: str) -> list[float]:
        """获取所有文档的 BM25 分数（用于融合）"""
        if self._bm25 is None:
            return []
        query_tokens = self.tokenize(query)
        return [float(s) for s in self._bm25.get_scores(query_tokens)]
