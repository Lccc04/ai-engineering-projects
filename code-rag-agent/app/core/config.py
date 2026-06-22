"""
全局配置 — 复用 code-rag-qa 的配置体系
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env", override=False)


class AgentSettings:
    # LLM
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    # Sandbox
    sandbox_timeout: int = 30
    sandbox_max_memory_mb: int = 256
    workspace_dir: Path = ROOT_DIR / "workspace"

    # Agent
    max_iterations: int = 10
    max_retries: int = 3

    # RAG (指向已有索引)
    rag_index_dir: Path = ROOT_DIR.parent / "code-rag-qa" / "data" / "indexes"
    rag_raw_dir: Path = ROOT_DIR.parent / "code-rag-qa" / "data" / "raw"


settings = AgentSettings()
