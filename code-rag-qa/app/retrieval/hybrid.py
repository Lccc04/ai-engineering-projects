"""
混合检索 — 向量检索 + BM25 加权融合
使用 Min-Max 归一化 + 加权求和
"""
from app.core.config import settings


class HybridRetriever:
    """
    混合检索器

    融合策略: Min-Max 归一化后加权求和
    hybrid_score = α × vector_score_norm + (1-α) × bm25_score_norm

    权重: 向量 0.6, BM25 0.4（经验值，向量检索在语义相关上更优）
    """

    def __init__(
        self,
        vector_weight: float | None = None,
        bm25_weight: float | None = None,
    ):
        self.vector_weight = vector_weight or settings.hybrid_weight_vector
        self.bm25_weight = bm25_weight or settings.hybrid_weight_bm25

    def fuse(
        self,
        vector_results: list[dict],
        bm25_results: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """
        融合向量和 BM25 检索结果

        Args:
            vector_results: [{"chunk": {...}, "score": float}, ...]
            bm25_results: [{"chunk": {...}, "score": float}, ...]
            top_k: 融合后返回 Top-K

        Returns:
            排序后的融合结果
        """
        top_k = top_k or settings.hybrid_top_k

        # 构建 chunk_id → 归一化得分 映射
        scores = {}

        # 向量得分归一化
        if vector_results:
            vec_scores = [r["score"] for r in vector_results]
            vec_min, vec_max = min(vec_scores), max(vec_scores)
            vec_range = vec_max - vec_min if vec_max != vec_min else 1.0
            for r in vector_results:
                chunk_id = r["chunk"].get("label", r["chunk"]["text"][:50])
                norm_score = (r["score"] - vec_min) / vec_range
                scores[chunk_id] = {
                    "chunk": r["chunk"],
                    "vector_score_raw": r["score"],
                    "vector_score_norm": norm_score,
                    "bm25_score_raw": 0.0,
                    "bm25_score_norm": 0.0,
                    "fused_score": self.vector_weight * norm_score,
                }

        # BM25 得分归一化
        if bm25_results:
            bm_scores = [r["score"] for r in bm25_results]
            bm_min, bm_max = min(bm_scores), max(bm_scores)
            bm_range = bm_max - bm_min if bm_max != bm_min else 1.0
            for r in bm25_results:
                chunk_id = r["chunk"].get("label", r["chunk"]["text"][:50])
                norm_score = (r["score"] - bm_min) / bm_range
                if chunk_id in scores:
                    scores[chunk_id]["bm25_score_raw"] = r["score"]
                    scores[chunk_id]["bm25_score_norm"] = norm_score
                    scores[chunk_id]["fused_score"] += self.bm25_weight * norm_score
                else:
                    scores[chunk_id] = {
                        "chunk": r["chunk"],
                        "vector_score_raw": 0.0,
                        "vector_score_norm": 0.0,
                        "bm25_score_raw": r["score"],
                        "bm25_score_norm": norm_score,
                        "fused_score": self.bm25_weight * norm_score,
                    }

        # 按融合分数排序
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["fused_score"],
            reverse=True,
        )

        return sorted_results[:top_k]
