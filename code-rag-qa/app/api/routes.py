"""
API 路由 — /upload_doc, /code_qa, /health, /stats
完整检索管线: 向量检索 → BM25 → 混合融合 → 重排 → 压缩 → LLM 生成 → 幻觉校验
"""
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.api.schemas import (
    CodeQARequest,
    CodeQAResponse,
    HealthResponse,
    StatsResponse,
    SourceInfo,
)
from app.cache.cache import cache, cache_key
from app.core.config import settings
from app.data_layer.corpus import CorpusBuilder
from app.retrieval.embedding import CodeEmbedding
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import Reranker
from app.retrieval.compressor import ContextCompressor
from app.generation.llm import llm_client
from app.generation.prompt import build_messages, route_query, QueryMode
from app.generation.hallucination_guard import HallucinationGuard

router = APIRouter(prefix="/api/v1")

# ─── 全局组件（延迟初始化，首次请求时加载模型） ───
_corpus_builder: CorpusBuilder | None = None
_embedding: CodeEmbedding | None = None
_bm25: BM25Retriever | None = None
_hybrid: HybridRetriever | None = None
_reranker: Reranker | None = None
_compressor: ContextCompressor | None = None
_hallucination_guard: HallucinationGuard | None = None

# 性能统计（记录每次请求耗时用于计算 P99）
_request_times: list[float] = []


def _get_components():
    """延迟初始化所有组件 — 首次请求时加载模型到内存"""
    global _corpus_builder, _embedding, _bm25, _hybrid, _reranker, _compressor, _hallucination_guard

    if _embedding is None:
        _embedding = CodeEmbedding()
        _bm25 = BM25Retriever()
        _hybrid = HybridRetriever()
        _reranker = Reranker()
        _compressor = ContextCompressor()
        _hallucination_guard = HallucinationGuard()
        _corpus_builder = CorpusBuilder()

        # 加载已有的 FAISS 和 BM25 索引
        index_dir = settings.data_indexes
        if (index_dir / "faiss.index").exists():
            _corpus_builder.store.load(index_dir)
            _bm25.index(_corpus_builder.store.chunks)

    return {
        "embedding": _embedding,
        "bm25": _bm25,
        "hybrid": _hybrid,
        "reranker": _reranker,
        "compressor": _compressor,
        "hallucination_guard": _hallucination_guard,
        "corpus_builder": _corpus_builder,
    }


# ═══════════════════════════════════════════
# 端点
# ═══════════════════════════════════════════

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["系统监控"],
    summary="系统健康检查",
    description="返回服务运行状态、当前模型和知识库索引规模。用于确认系统是否正常启动。",
)
async def health():
    """系统健康检查"""
    comps = _get_components()
    return HealthResponse(
        status="ok",
        model=settings.model,
        index_size=comps["corpus_builder"].store.size,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    tags=["系统监控"],
    summary="系统运行统计",
    description="返回知识库规模、分块数量、缓存命中率和平均响应耗时。可用于性能监控。",
)
async def stats():
    """系统运行统计"""
    comps = _get_components()
    avg_time = sum(_request_times[-100:]) / max(len(_request_times[-100:]), 1)
    return StatsResponse(
        index_size=comps["corpus_builder"].store.size,
        chunk_count=len(comps["corpus_builder"].store.chunks),
        cache_size=cache.size,
        cache_hit_rate=cache.hit_rate,
        avg_response_time_ms=round(avg_time, 2),
    )


@router.post(
    "/code_qa",
    response_model=CodeQAResponse,
    tags=["代码问答"],
    summary="代码问答（核心接口）",
    description="""
## 完整的 RAG 检索增强生成管线

这个接口会依次执行以下步骤：

1. **问题路由** — 自动识别你的问题是「代码生成」「代码解释」还是「代码排错」
2. **缓存检查** — 相同问题如果之前问过，直接从缓存返回（秒级响应）
3. **向量检索** — 用 bge-large-zh 语义搜索知识库，召回 Top-30
4. **BM25 关键词检索** — 用 jieba 分词做关键词匹配，召回 Top-30
5. **混合融合** — 将两种检索结果按 0.6:0.4 加权合并，取 Top-20
6. **Cross-BERT 重排** — 用 bge-reranker-base 对候选逐一打分，精排取 Top-3
7. **上下文压缩** — 只保留与问题强相关的句子，减少无效信息干扰
8. **LLM 生成** — DeepSeek V4 Pro 基于检索上下文生成回答
9. **幻觉校验** — 反向检查回答中的关键信息是否在上下文中存在

## 使用示例

```json
{
  "query": "FastAPI 中 APIRouter 的 add_api_route 是怎么实现的？",
  "use_cache": true
}
```
    """,
)
async def code_qa(req: CodeQARequest):
    """
    代码问答接口 — 完整 RAG 管线

    管线流程:
    问题路由 → 缓存检查 → 向量检索 + BM25 → 混合融合 →
    重排 → 上下文压缩 → LLM 生成 → 幻觉校验
    """
    t_start = time.perf_counter()
    comps = _get_components()

    # ── Step 0: 问题路由（自动识别问答模式） ──
    if req.mode is None:
        bm25_hits = comps["bm25"].search(req.query, k=5)
        mode = route_query(req.query, len(bm25_hits))
    else:
        mode = QueryMode(req.mode)

    # ── Step 1: 缓存检查 ──
    ck = cache_key(req.query, mode.value)
    if req.use_cache:
        cached_result = cache.get(ck)
        if cached_result:
            elapsed = (time.perf_counter() - t_start) * 1000
            cached_result["cached"] = True
            cached_result["response_time_ms"] = round(elapsed, 2)
            _record_time(elapsed)
            return CodeQAResponse(**cached_result)

    # ── Step 2: 向量检索 ──
    query_emb = comps["embedding"].encode_query(req.query)
    vector_results = comps["corpus_builder"].store.search(
        query_emb, k=settings.vector_top_k
    )

    # ── Step 3: BM25 关键词检索 ──
    bm25_results = comps["bm25"].search(req.query, k=settings.bm25_top_k)

    # ── Step 4: 混合融合 ──
    fused_results = comps["hybrid"].fuse(vector_results, bm25_results)

    # ── Step 5: Cross-BERT 重排 ──
    reranked = comps["reranker"].rerank(
        req.query, fused_results, top_k=req.top_k or settings.rerank_top_k
    )

    # ── Step 6: 上下文压缩 ──
    context_text = comps["compressor"].compress(req.query, reranked)

    # ── Step 7: LLM 生成 ──
    messages = build_messages(req.query, context_text, mode)
    answer = llm_client.chat(messages)

    # ── Step 8: 幻觉校验 ──
    context_texts = [r["chunk"]["text"] for r in reranked]
    hallucination_result = comps["hallucination_guard"].check(answer, context_texts)

    # ── Step 9: 构建来源信息 ──
    sources = []
    for r in reranked:
        c = r["chunk"]
        sources.append(SourceInfo(
            file_path=c.get("file_path", ""),
            file_name=c.get("file_name", ""),
            module_path=c.get("module_path", ""),
            function_name=c.get("function_name", ""),
            class_name=c.get("class_name", ""),
            chunk_type=c.get("chunk_type", ""),
            line_range=c.get("line_range", ""),
            relevance_score=round(r.get("rerank_score", r.get("fused_score", 0)), 4),
        ))

    # ── 组装响应 ──
    elapsed = (time.perf_counter() - t_start) * 1000
    _record_time(elapsed)

    response_data = {
        "query": req.query,
        "answer": answer,
        "mode": mode.value,
        "sources": [s.model_dump() for s in sources],
        "hallucination_check": hallucination_result,
        "cached": False,
        "response_time_ms": round(elapsed, 2),
    }

    # 写入缓存
    cache.set(ck, response_data)

    return CodeQAResponse(**response_data)


@router.post(
    "/upload_doc",
    tags=["知识库管理"],
    summary="上传文档并更新知识库",
    description="""
上传代码或文档文件，系统会自动：

1. 保存文件到 data/raw/ 目录
2. 重新解析所有文件
3. 按语法边界重新分块
4. 重新生成向量
5. 更新 FAISS 和 BM25 索引

**支持的文件类型**: Python(.py)、Markdown(.md)、RST(.rst)、文本(.txt)、TOML(.toml)、YAML(.yaml)
    """,
)
async def upload_doc(file: UploadFile = File(..., description="要上传的代码或文档文件")):
    """
    上传文档并更新向量库

    接收单个文件，保存到 data/raw/，触发增量索引重建
    """
    comps = _get_components()

    # 验证文件类型
    allowed_exts = {".py", ".md", ".rst", ".txt", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".markdown"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            400,
            f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_exts)}",
        )

    # 保存文件
    save_dir = settings.data_raw
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 重建索引
    comps["corpus_builder"].build(force=True)
    comps["bm25"].index(comps["corpus_builder"].store.chunks)

    return {
        "状态": "成功",
        "消息": f"文件 {file.filename} 已上传并完成索引更新",
        "文件名": file.filename,
        "知识库大小": comps["corpus_builder"].store.size,
        "status": "ok",
        "message": f"文件 {file.filename} 已上传，索引已更新",
        "file_name": file.filename,
        "index_size": comps["corpus_builder"].store.size,
    }


def _record_time(elapsed_ms: float):
    """记录请求耗时（用于计算 P50/P95/P99）"""
    _request_times.append(elapsed_ms)
    if len(_request_times) > 10000:
        _request_times.pop(0)
