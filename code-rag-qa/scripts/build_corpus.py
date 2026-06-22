#!/usr/bin/env python
"""
一键构建语料库脚本
用法: python scripts/build_corpus.py [--force] [--raw-dir PATH]
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from app.data_layer.corpus import CorpusBuilder
from app.retrieval.bm25 import BM25Retriever


def main():
    parser = argparse.ArgumentParser(description="构建代码 RAG 语料库")
    parser.add_argument("--force", action="store_true", help="强制重建索引")
    parser.add_argument("--raw-dir", type=str, default=None, help="原始文件目录")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir) if args.raw_dir else settings.data_raw

    print(f"\n{'='*60}")
    print(f"  代码 RAG 语料库构建")
    print(f"  源目录: {raw_dir}")
    print(f"  索引目录: {settings.data_indexes}")
    print(f"  分块策略: 语法感知 (chunk_size={settings.chunk_size}, overlap={settings.chunk_overlap})")
    print(f"  Embedding: {settings.embedding_model}")
    print(f"{'='*60}\n")

    # 构建语料库
    builder = CorpusBuilder()
    store = builder.build(raw_dir=raw_dir, force=args.force)

    # 构建 BM25 索引
    if store.chunks:
        bm25 = BM25Retriever()
        bm25.index(store.chunks)
        print(f"[BM25] 索引就绪: {len(store.chunks)} 个文档\n")

    print("[OK] 语料库构建完成! 可以启动 API 服务: python main.py")


if __name__ == "__main__":
    main()
