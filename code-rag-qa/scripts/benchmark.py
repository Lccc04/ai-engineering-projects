#!/usr/bin/env python
"""
性能压测 — 计算 P50/P95/P99 延迟 + 吞吐量
用法: python scripts/benchmark.py [--concurrent 5] [--rounds 20]
"""
import sys
import json
import time
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

API_BASE = "http://localhost:8000"
BENCHMARK_QUERIES = [
    "FastAPI 的路由注册是怎么实现的？",
    "Pandas 的 DataFrame groupby 原理是什么？",
    "FastAPI 依赖注入怎么用？",
    "如何处理 Pandas 中的缺失值？",
    "FastAPI 中间件机制是什么？",
]


def send_query(query: str) -> dict:
    """发送单次查询，返回耗时和状态"""
    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{API_BASE}/api/v1/code_qa",
            json={"query": query, "use_cache": False},
            timeout=60,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "query": query[:40],
            "status": resp.status_code,
            "elapsed_ms": elapsed,
            "cached": resp.json().get("cached", False) if resp.status_code == 200 else False,
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "query": query[:40],
            "status": 0,
            "elapsed_ms": elapsed,
            "error": str(e),
        }


def run_benchmark(concurrent: int = 3, rounds: int = 15):
    """运行压测"""
    print(f"\n{'='*60}")
    print(f"  性能压测: {concurrent} 并发, {rounds} 轮")
    print(f"  API: {API_BASE}")
    print(f"{'='*60}\n")

    # 预热
    print("预热中...")
    for _ in range(2):
        try:
            requests.get(f"{API_BASE}/health", timeout=5)
            break
        except Exception:
            time.sleep(1)
    else:
        print("[ERROR] API 服务未启动！请先运行 python main.py")
        return

    all_results = []

    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = []
        for round_num in range(rounds):
            for q in BENCHMARK_QUERIES:
                futures.append(executor.submit(send_query, q))

        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
            status = "[OK]" if result["status"] == 200 else "[FAIL]"
            cached = "♻️" if result.get("cached") else ""
            print(f"  {status} {result['query']:<45} {result['elapsed_ms']:>8.1f}ms {cached}")

    # 统计
    latencies = sorted([r["elapsed_ms"] for r in all_results if r["status"] == 200])
    errors = [r for r in all_results if r["status"] != 200]

    if not latencies:
        print("[ERROR] 所有请求均失败！")
        return

    def percentile(data: list[float], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(data) - 1)
        return data[f] + (k - f) * (data[c] - data[f])

    print(f"\n{'='*60}")
    print(f"  压测报告")
    print(f"{'='*60}")
    print(f"  总请求数:    {len(all_results)}")
    print(f"  成功:        {len(latencies)}")
    print(f"  失败:        {len(errors)}")
    print(f"  P50 延迟:    {percentile(latencies, 50):.1f} ms")
    print(f"  P95 延迟:    {percentile(latencies, 95):.1f} ms")
    print(f"  P99 延迟:    {percentile(latencies, 99):.1f} ms")
    print(f"  平均延迟:    {statistics.mean(latencies):.1f} ms")
    print(f"  最小/最大:   {min(latencies):.1f} / {max(latencies):.1f} ms")
    print(f"{'='*60}\n")

    # 保存报告
    report = {
        "config": {"concurrent": concurrent, "rounds": rounds},
        "total_requests": len(all_results),
        "success": len(latencies),
        "errors": len(errors),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
    }
    report_path = Path(__file__).parent.parent / "data" / "benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {report_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrent", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=15)
    args = parser.parse_args()
    run_benchmark(args.concurrent, args.rounds)
