"""
语料库构建器 — 编排完整的「解析→分块→元数据→向量化→索引」流水线
"""
import json
from pathlib import Path
import numpy as np
from app.core.config import settings
from app.data_layer.parser import CodeParser
from app.data_layer.chunker import SyntaxAwareChunker
from app.data_layer.metadata import MetadataExtractor
from app.retrieval.embedding import CodeEmbedding
from app.retrieval.vector_store import FAISSStore


class CorpusBuilder:
    """
    语料库构建器

    流水线:
    1. 遍历 data/raw/ 下所有文件 → 解析
    2. 按文件类型选择分块策略 → 语法感知分块
    3. 提取每个 chunk 的元数据标签
    4. bge-code-v1.5 生成向量
    5. 构建 FAISS 索引 + 持久化
    """

    def __init__(self):
        self.parser = CodeParser()
        self.chunker = SyntaxAwareChunker()
        self.meta_extractor = MetadataExtractor()
        self.embedding = CodeEmbedding()
        self.store = FAISSStore()

    def build(self, raw_dir: Path | None = None, force: bool = False) -> FAISSStore:
        """
        构建完整语料库

        Args:
            raw_dir: 原始文件目录，默认 data/raw/
            force: 是否强制重建（忽略已有索引）

        Returns:
            FAISSStore 实例
        """
        raw_dir = raw_dir or settings.data_raw
        index_dir = settings.data_indexes

        # 检查已有索引
        if not force and (index_dir / "faiss.index").exists():
            print("[Corpus] 发现已有索引，直接加载（使用 force=True 强制重建）")
            self.store.load(index_dir)
            return self.store

        # Step 1: 解析文件
        print(f"[Corpus] 开始解析目录: {raw_dir}")
        documents = self.parser.parse_directory(raw_dir)
        if not documents:
            print("[Corpus] 未找到任何文件！请在 data/raw/ 下放置代码和文档")
            return self.store

        # Step 2: 分块 + 元数据提取
        all_chunks = []
        for doc in documents:
            chunk_texts = self.chunker.chunk(doc.content, doc.file_type)
            for text in chunk_texts:
                meta = self.meta_extractor.extract(text, doc)
                all_chunks.append({
                    "text": text,
                    **meta.to_dict(),
                    "label": meta.to_label(),
                })

        print(f"[Corpus] 分块完成: {len(all_chunks)} 个 chunk")

        # 保存 chunks 到磁盘
        chunks_dir = settings.data_chunks
        chunks_dir.mkdir(parents=True, exist_ok=True)
        with open(chunks_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        # Step 3: 向量化
        texts = [c["text"] for c in all_chunks]
        print(f"[Corpus] 开始向量化: {len(texts)} 条文本 ...")
        embeddings = self.embedding.encode_documents(texts)

        # Step 4: 构建 FAISS 索引
        self.store.build(embeddings, all_chunks)
        self.store.save(index_dir)

        # 统计
        self._print_stats(all_chunks, documents)

        return self.store

    def _print_stats(self, chunks: list[dict], documents: list):
        """打印语料库统计信息"""
        file_types = {}
        chunk_types = {}
        for c in chunks:
            ft = c.get("file_type", "unknown")
            ct = c.get("chunk_type", "unknown")
            file_types[ft] = file_types.get(ft, 0) + 1
            chunk_types[ct] = chunk_types.get(ct, 0) + 1

        total_lines = sum(len(doc.content.split("\n")) for doc in documents)
        print(f"\n{'='*50}")
        print(f"  语料库构建完成")
        print(f"{'='*50}")
        print(f"  文件数:    {len(documents)}")
        print(f"  总行数:    {total_lines:,}")
        print(f"  Chunk 数:  {len(chunks)}")
        print(f"  文件类型:  {file_types}")
        print(f"  Chunk 类型: {chunk_types}")
        print(f"{'='*50}\n")
