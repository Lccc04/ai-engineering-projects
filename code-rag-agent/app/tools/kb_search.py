"""
知识库检索工具 — 对接 code-rag-qa 的 RAG 检索管线
Function Calling 定义: 输入查询文本，返回代码库中最相关的文档片段
"""
import sys
from pathlib import Path

# 复用 code-rag-qa 模块
_RAG_ROOT = Path(__file__).parent.parent.parent.parent / "code-rag-qa"
if str(_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_RAG_ROOT))

from app.tools.base import BaseTool
from app.core.config import settings


class KBSearchTool(BaseTool):
    """
    RAG 代码知识库检索

    用法示例（LLM 调用）：
    kb_search(query="FastAPI 路由注册机制")

    两级检索：
    1. 向量检索 (bge-large-zh-v1.5) → Top-30
    2. Cross-BERT 重排 (bge-reranker-base) → Top-3
    """

    def __init__(self):
        self._corpus = None
        self._embedding = None
        self._bm25 = None
        self._hybrid = None
        self._reranker = None
        self._initialized = False

    def _lazy_init(self):
        """延迟初始化（避免启动时加载模型）"""
        if self._initialized:
            return

        try:
            from app.data_layer.corpus import CorpusBuilder
            from app.retrieval.embedding import CodeEmbedding
            from app.retrieval.bm25 import BM25Retriever
            from app.retrieval.hybrid import HybridRetriever
            from app.retrieval.reranker import Reranker

            index_dir = settings.rag_index_dir
            if not (index_dir / "faiss.index").exists():
                raise FileNotFoundError(f"索引不存在: {index_dir}，请先运行 code-rag-qa/scripts/build_corpus.py")

            # 加载索引
            builder = CorpusBuilder()
            builder.store.load(index_dir)
            self._corpus = builder

            self._bm25 = BM25Retriever()
            self._bm25.index(builder.store.chunks)

            self._embedding = CodeEmbedding()
            self._hybrid = HybridRetriever()
            self._reranker = Reranker()
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"RAG 知识库初始化失败: {e}")

    @property
    def name(self) -> str:
        return "kb_search"

    @property
    def description(self) -> str:
        return (
            "搜索代码知识库，获取 FastAPI、Pandas 等 Python 框架的 API 文档、"
            "源码实现和最佳实践。当用户询问如何使用某个框架功能，"
            "或代码执行出错需要查找解决方案时，应该使用此工具。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "query": {
                "type": "string",
                "description": "搜索查询，建议使用具体的技术关键词（如 'FastAPI Depends 依赖注入'）",
            },
        }

    def execute(self, query: str = "") -> str:
        if not query.strip():
            return "[错误] 搜索查询为空"

        try:
            self._lazy_init()
        except RuntimeError as e:
            return f"[知识库未就绪] {e}"

        # 完整检索管线
        query_emb = self._embedding.encode_query(query)
        vec_results = self._corpus.store.search(query_emb, k=30)
        bm25_results = self._bm25.search(query, k=30)
        fused = self._hybrid.fuse(vec_results, bm25_results, top_k=10)
        reranked = self._reranker.rerank(query, fused, top_k=3)

        if not reranked:
            return "[未找到] 知识库中没有相关文档"

        # 格式化结果
        lines = [f"找到 {len(reranked)} 条相关文档:\n"]
        for i, r in enumerate(reranked, 1):
            c = r["chunk"]
            label = c.get("label", c.get("file_name", "未知"))
            text = c["text"][:600]
            score = r.get("rerank_score", r.get("fused_score", 0))
            lines.append(f"[{i}] {label} (相关度: {score:.3f})\n{text}\n")

        return "\n".join(lines)
