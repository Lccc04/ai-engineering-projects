"""
代码专用 Embedding — 使用 BAAI/bge-code-v1.5
1024 维向量，支持批量编码 + 指令前缀
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class CodeEmbedding:
    """
    代码 Embedding 模型封装

    模型: BAAI/bge-code-v1.5
    特点:
    - 专为代码检索优化
    - 支持 query 指令前缀提升检索精度
    - 1024 维输出，batch_size 可调
    """

    # BGE 系列模型的 query 指令前缀
    QUERY_PREFIX = "为这段代码生成向量表示:"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self.dim = settings.embedding_dim

    @property
    def model(self) -> SentenceTransformer:
        """延迟加载模型"""
        if self._model is None:
            print(f"[Embedding] 加载模型 {self.model_name} ...")
            self._model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True,
            )
            print(f"[Embedding] 模型加载完成，维度: {self._model.get_sentence_embedding_dimension()}")
        return self._model

    def encode_documents(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        编码文档（不需要前缀）

        Args:
            texts: 文档文本列表
            batch_size: 批量大小

        Returns:
            numpy array, shape=(len(texts), 1024)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=True,  # L2 归一化，支持内积搜索
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """
        编码查询（加指令前缀提升精度）

        Args:
            query: 用户查询文本

        Returns:
            numpy array, shape=(1024,)
        """
        # BGE 系列建议 query 加前缀
        embedding = self.model.encode(
            [self.QUERY_PREFIX + query],
            normalize_embeddings=True,
        )
        return np.array(embedding[0], dtype=np.float32)

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        """批量编码查询"""
        prefixed = [self.QUERY_PREFIX + q for q in queries]
        embeddings = self.model.encode(
            prefixed,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)
