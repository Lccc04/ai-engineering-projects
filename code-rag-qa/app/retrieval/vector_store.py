"""
FAISS 向量库封装 — IndexFlatIP（内积搜索，精度最高）
支持增量添加、批量检索、持久化
"""
import json
import pickle
from pathlib import Path
import numpy as np
import faiss
from app.core.config import settings


class FAISSStore:
    """
    FAISS 向量存储

    索引类型: IndexFlatIP (内积 = 余弦相似度，因为向量已 L2 归一化)
    优势: 精确搜索，无精度损失，适合 10 万级文档
    """

    def __init__(self):
        self.index: faiss.IndexFlatIP | None = None
        self.chunks: list[dict] = []  # 存储 chunk 元数据
        self.dim = settings.embedding_dim

    def build(self, embeddings: np.ndarray, chunks_meta: list[dict]):
        """
        构建索引

        Args:
            embeddings: shape=(N, 1024), L2 归一化后的向量
            chunks_meta: chunk 元数据列表，与 embeddings 一一对应
        """
        if len(embeddings) == 0:
            print("[FAISS] 警告: 空 embedding，跳过索引构建")
            return

        self.dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(embeddings.astype(np.float32))
        self.chunks = chunks_meta

        print(f"[FAISS] 索引构建完成: {self.index.ntotal} 条向量")

    def search(self, query_embedding: np.ndarray, k: int | None = None) -> list[dict]:
        """
        向量检索

        Args:
            query_embedding: shape=(1024,)
            k: 返回 Top-K

        Returns:
            [{"chunk": {...}, "score": float}, ...]
        """
        if self.index is None:
            return []

        k = k or settings.vector_top_k
        query_vec = query_embedding.reshape(1, -1).astype(np.float32)

        distances, indices = self.index.search(query_vec, min(k, self.index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append({
                    "chunk": self.chunks[idx],
                    "score": float(dist),  # 内积分数 (0~1，越高越相似)
                })

        return results

    def add(self, embeddings: np.ndarray, chunks_meta: list[dict]):
        """增量添加向量和元数据"""
        if self.index is None:
            self.build(embeddings, chunks_meta)
        else:
            self.index.add(embeddings.astype(np.float32))
            self.chunks.extend(chunks_meta)
            print(f"[FAISS] 增量添加: +{len(chunks_meta)} 条, 总计 {self.index.ntotal} 条")

    def save(self, index_dir: Path):
        """持久化索引和元数据"""
        index_dir.mkdir(parents=True, exist_ok=True)

        # 保存 FAISS 索引
        index_path = index_dir / "faiss.index"
        faiss.write_index(self.index, str(index_path))

        # 保存 chunk 元数据
        chunks_path = index_dir / "chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        print(f"[FAISS] 已保存: {index_path}, {chunks_path}")

    def load(self, index_dir: Path):
        """加载持久化的索引和元数据"""
        index_path = index_dir / "faiss.index"
        chunks_path = index_dir / "chunks.json"

        if not index_path.exists() or not chunks_path.exists():
            raise FileNotFoundError(f"索引文件不存在: {index_path} 或 {chunks_path}")

        self.index = faiss.read_index(str(index_path))
        self.dim = self.index.d

        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        print(f"[FAISS] 已加载: {self.index.ntotal} 条向量, {len(self.chunks)} 个 chunk")

    @property
    def size(self) -> int:
        return self.index.ntotal if self.index else 0
