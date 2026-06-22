"""
重排序器 — 基于 Embedding 余弦相似度精排
不依赖额外 Cross-Encoder 模型，使用已有 Embedding 模型
对混合检索的 Top-20 做精排，只取 Top-3 传入 LLM
"""
import numpy as np


class Reranker:
    """
    Embedding 重排序器

    策略: 使用已有的 Embedding 模型，计算 query 与每个候选 chunk 的余弦相似度
    相当于对混合检索的粗排结果做一次更精准的重排序

    效果: 对 Top-20 做更精细的相关性打分，取 Top-3 减少 LLM 上下文噪音
    """

    def __init__(self, embedding_model=None):
        """
        Args:
            embedding_model: CodeEmbedding 实例，如果为 None 则延迟获取
        """
        self._embedding = embedding_model

    def set_embedding(self, embedding_model):
        """注入 Embedding 模型"""
        self._embedding = embedding_model

    @property
    def embedding(self):
        if self._embedding is None:
            # 延迟导入避免循环依赖
            from app.retrieval.embedding import CodeEmbedding
            self._embedding = CodeEmbedding()
        return self._embedding

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """
        重排序候选 chunk

        Args:
            query: 用户查询
            candidates: 候选 chunk 列表 [{"chunk": {...}, ...}, ...]
            top_k: 精排后保留 Top-K，默认 3

        Returns:
            重排序后的结果，附带 rerank_score
        """
        if not candidates:
            return []

        from app.core.config import settings
        top_k = top_k or settings.rerank_top_k

        # 获取 query embedding
        query_emb = self.embedding.encode_query(query)

        # 获取所有候选 chunk 的 text
        texts = [c["chunk"]["text"] for c in candidates]

        # 批量编码（用 document 编码模式，不加 query 前缀）
        chunk_embs = self.embedding.encode_documents(texts)

        # 计算余弦相似度（向量已 L2 归一化，内积 = 余弦）
        similarities = np.dot(chunk_embs, query_emb)

        # 附加分数并排序
        for i, score in enumerate(similarities):
            candidates[i]["rerank_score"] = float(score)

        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return candidates[:top_k]
