#!/usr/bin/env python
"""
消融实验 — 对比三种检索方案的准确率
1. 纯向量检索 (baseline)
2. 向量 + BM25 混合检索
3. 向量 + BM25 + Cross-BERT 重排 (full pipeline)

面试核心: 量化每层优化带来的提升，说明你的选型依据
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from app.data_layer.corpus import CorpusBuilder
from app.retrieval.embedding import CodeEmbedding
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import Reranker


# ─── 测试问题集（至少 10 条，用于量化评估） ───
# 格式: {"query": "...", "relevant_files": ["file1.py", ...], "relevant_keywords": ["..."]}
TEST_QUERIES = [
    {
        "query": "FastAPI 中路由是如何注册的？",
        "relevant_keywords": ["APIRouter", "add_api_route", "route", "routing"],
    },
    {
        "query": "Pandas 中 DataFrame 的 groupby 操作原理是什么？",
        "relevant_keywords": ["groupby", "DataFrame", "aggregate", "split-apply-combine"],
    },
    {
        "query": "FastAPI 的依赖注入系统是怎么实现的？",
        "relevant_keywords": ["Depends", "dependency", "injection", "params"],
    },
    {
        "query": "如何使用 FastAPI 处理文件上传？",
        "relevant_keywords": ["UploadFile", "file", "upload", "multipart"],
    },
    {
        "query": "Pandas 中如何处理缺失值？",
        "relevant_keywords": ["fillna", "dropna", "isna", "missing"],
    },
    {
        "query": "FastAPI 的中间件机制是如何工作的？",
        "relevant_keywords": ["middleware", "add_middleware", "request", "response"],
    },
    {
        "query": "Pandas 的 merge 和 join 有什么区别？",
        "relevant_keywords": ["merge", "join", "concat", "DataFrame"],
    },
    {
        "query": "FastAPI 中如何定义请求体和响应模型？",
        "relevant_keywords": ["BaseModel", "pydantic", "schema", "body"],
    },
    {
        "query": "Pandas 中 DataFrame 索引如何工作？",
        "relevant_keywords": ["index", "loc", "iloc", "set_index"],
    },
    {
        "query": "FastAPI 的异常处理机制是怎样的？",
        "relevant_keywords": ["HTTPException", "exception_handler", "error", "status"],
    },
]


def evaluate_recall(results: list[dict], relevant_keywords: list[str]) -> float:
    """
    评估召回率：检查 Top-K 结果中包含多少相关关键词
    简化版 MRR (Mean Reciprocal Rank) 风格评估
    """
    if not results or not relevant_keywords:
        return 0.0

    hit_count = 0
    for kw in relevant_keywords:
        for r in results:
            text = r["chunk"]["text"].lower()
            if kw.lower() in text:
                hit_count += 1
                break

    return hit_count / len(relevant_keywords)


def run_ablation():
    """运行消融实验"""
    print("\n" + "=" * 70)
    print("  消融实验: 检索方案对比")
    print("=" * 70)

    # 加载索引
    builder = CorpusBuilder()
    index_dir = settings.data_indexes
    if not (index_dir / "faiss.index").exists():
        print("[ERROR] 索引不存在，请先运行 python scripts/build_corpus.py")
        return

    builder.store.load(index_dir)
    bm25 = BM25Retriever()
    bm25.index(builder.store.chunks)
    embedding = CodeEmbedding()
    hybrid = HybridRetriever()
    reranker = Reranker()

    print(f"\n语料规模: {builder.store.size} 个 chunk, {len(TEST_QUERIES)} 条测试查询\n")

    results = {
        "vector_only": {"recalls": [], "times": [], "avg_recall": 0, "avg_time": 0},
        "hybrid": {"recalls": [], "times": [], "avg_recall": 0, "avg_time": 0},
        "hybrid_rerank": {"recalls": [], "times": [], "avg_recall": 0, "avg_time": 0},
    }

    for i, test in enumerate(TEST_QUERIES):
        query = test["query"]
        keywords = test["relevant_keywords"]
        print(f"\n[{i+1}/{len(TEST_QUERIES)}] Q: {query}")

        # ─── 方案 1: 纯向量检索 ───
        t0 = time.perf_counter()
        q_emb = embedding.encode_query(query)
        vec_results = builder.store.search(q_emb, k=10)
        t1 = (time.perf_counter() - t0) * 1000
        recall = evaluate_recall(vec_results, keywords)
        results["vector_only"]["recalls"].append(recall)
        results["vector_only"]["times"].append(t1)
        print(f"  纯向量:    召回率={recall:.2f}, 耗时={t1:.1f}ms")

        # ─── 方案 2: 混合检索 ───
        t0 = time.perf_counter()
        bm25_results = bm25.search(query, k=settings.bm25_top_k)
        fused = hybrid.fuse(vec_results, bm25_results, top_k=10)
        t1 = (time.perf_counter() - t0) * 1000
        recall = evaluate_recall(fused, keywords)
        results["hybrid"]["recalls"].append(recall)
        results["hybrid"]["times"].append(t1)
        print(f"  混合检索:  召回率={recall:.2f}, 耗时={t1:.1f}ms")

        # ─── 方案 3: 混合 + 重排 ───
        t0 = time.perf_counter()
        reranked = reranker.rerank(query, fused, top_k=3)
        t1 = (time.perf_counter() - t0) * 1000
        recall = evaluate_recall(reranked, keywords)
        results["hybrid_rerank"]["recalls"].append(recall)
        results["hybrid_rerank"]["times"].append(t1)
        print(f"  混合+重排:  召回率={recall:.2f}, 耗时={t1:.1f}ms")

    # ─── 汇总报告 ───
    for name in results:
        recs = results[name]["recalls"]
        times = results[name]["times"]
        results[name]["avg_recall"] = sum(recs) / len(recs) if recs else 0
        results[name]["avg_time"] = sum(times) / len(times) if times else 0

    print("\n" + "=" * 70)
    print("  消融实验结果汇总")
    print("=" * 70)
    print(f"{'方案':<20} {'平均召回率':<12} {'平均耗时(ms)':<15} {'提升':<10}")
    print("-" * 57)

    baseline_recall = results["vector_only"]["avg_recall"]
    for name, label in [("vector_only", "纯向量"), ("hybrid", "混合检索"), ("hybrid_rerank", "混合+重排")]:
        rec = results[name]["avg_recall"]
        t = results[name]["avg_time"]
        improvement = f"+{(rec - baseline_recall) / baseline_recall * 100:.1f}%" if name != "vector_only" else "baseline"
        print(f"{label:<20} {rec:.4f}       {t:.1f}            {improvement:<10}")

    print("=" * 70)
    print("\n*** 面试要点: ***")
    print("  1. 纯向量在语义理解上占优，但关键词匹配弱")
    print("  2. 混合检索弥补了关键词死角，召回率提升明显")
    print("  3. Cross-BERT 重排进一步精炼 Top-3，确保传给 LLM 的是最相关的上下文")
    print("  4. 每一层都有独立的消融数据支撑，选型有理有据\n")

    # 保存结果
    report_path = Path(__file__).parent.parent / "data" / "ablation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {report_path}")


if __name__ == "__main__":
    run_ablation()
