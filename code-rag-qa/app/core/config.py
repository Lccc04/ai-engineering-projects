"""
全局配置 — 所有环境变量和超参数集中管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent

# 加载 .env
load_dotenv(ROOT_DIR / ".env", override=False)

# HuggingFace 镜像（国内加速）
_hf_endpoint = os.getenv("HF_ENDPOINT", "")
if _hf_endpoint:
    os.environ["HF_ENDPOINT"] = _hf_endpoint


class Settings:
    """全局配置单例"""

    # ─── DeepSeek API ───
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "sk-your-api-key-here")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    # ─── Embedding ───
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-code-v1.5")
    embedding_dim: int = 768  # text2vec-base-chinese 输出维度

    # ─── Reranker ───
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

    # ─── Chunking ───
    chunk_size: int = 600
    chunk_overlap: int = 80

    # ─── Retrieval ───
    vector_top_k: int = 30
    bm25_top_k: int = 30
    hybrid_top_k: int = 20
    rerank_top_k: int = 3
    hybrid_weight_vector: float = 0.6  # 向量权重
    hybrid_weight_bm25: float = 0.4    # BM25 权重

    # ─── Generation ───
    max_context_tokens: int = 4000
    temperature: float = 0.1  # 代码场景用低温，减少随机性

    # ─── Cache ───
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))

    # ─── Server ───
    api_port: int = int(os.getenv("API_PORT", "8000"))
    streamlit_port: int = int(os.getenv("STREAMLIT_PORT", "8501"))

    # ─── Paths ───
    @property
    def data_raw(self) -> Path:
        return ROOT_DIR / "data" / "raw"

    @property
    def data_chunks(self) -> Path:
        return ROOT_DIR / "data" / "chunks"

    @property
    def data_indexes(self) -> Path:
        return ROOT_DIR / "data" / "indexes"


# 全局单例
settings = Settings()
