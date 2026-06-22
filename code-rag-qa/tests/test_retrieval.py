"""
检索层单元测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_layer.chunker import SyntaxAwareChunker
from app.data_layer.metadata import MetadataExtractor
from app.data_layer.parser import CodeParser, ParsedDocument
from app.retrieval.bm25 import BM25Retriever


def test_syntax_chunker():
    """测试语法感知分块器"""
    chunker = SyntaxAwareChunker(chunk_size=300, chunk_overlap=50)

    # Python 代码测试
    python_code = """
class APIRouter:
    def add_api_route(self, path, endpoint, methods=None):
        '''注册一个 API 路由'''
        if methods is None:
            methods = ["GET"]
        self.routes.append(Route(path, endpoint, methods))

    def include_router(self, router, prefix=""):
        '''包含子路由'''
        for route in router.routes:
            route.path = prefix + route.path
            self.routes.append(route)
"""

    chunks = chunker.chunk(python_code, "python")
    assert len(chunks) > 0, "Python 分块不应为空"
    # 验证不超过 chunk_size
    for c in chunks:
        assert len(c) <= 310, f"Chunk 过长: {len(c)}"
    print(f"[OK] 语法分块测试通过: {len(chunks)} 个 chunk")


def test_metadata_extraction():
    """测试元数据提取"""
    extractor = MetadataExtractor()

    doc = ParsedDocument(
        file_path="test/test_router.py",
        file_name="test_router.py",
        file_type="python",
        content="class APIRouter:\n    def add_api_route(self): pass",
        module_path="test.test_router",
        lines=["class APIRouter:", "    def add_api_route(self): pass"],
    )

    chunk_text = "class APIRouter:\n    def add_api_route(self, path, endpoint):\n        pass"
    meta = extractor.extract(chunk_text, doc)

    assert meta.file_type == "python"
    assert meta.module_path == "test.test_router"
    assert meta.class_name == "APIRouter"
    print(f"[OK] 元数据提取测试通过: {meta.to_label()}")


def test_bm25_tokenize():
    """测试 BM25 分词"""
    bm25 = BM25Retriever()

    tokens = bm25.tokenize("fastapi_routing get_user_by_id")
    assert "fastapi" in tokens or "routing" in tokens, f"下划线拆分失败: {tokens}"

    tokens = bm25.tokenize("APIRouter add_api_route")
    assert len(tokens) > 0
    print(f"[OK] BM25 分词测试通过: {tokens[:10]}")


def test_hybrid_fusion():
    """测试混合融合"""
    from app.retrieval.hybrid import HybridRetriever

    vector_results = [
        {"chunk": {"text": "aaa", "label": "a"}, "score": 0.9},
        {"chunk": {"text": "bbb", "label": "b"}, "score": 0.7},
        {"chunk": {"text": "ccc", "label": "c"}, "score": 0.3},
    ]
    bm25_results = [
        {"chunk": {"text": "bbb", "label": "b"}, "score": 8.0},
        {"chunk": {"text": "ddd", "label": "d"}, "score": 6.0},
    ]

    hybrid = HybridRetriever()
    fused = hybrid.fuse(vector_results, bm25_results, top_k=3)

    assert len(fused) == 3
    # b 在两个检索中都出现，融合后应排第一
    assert fused[0]["chunk"]["label"] == "b", f"错误: 期望 b 排第一，实际 {fused[0]['chunk']['label']}"
    print(f"[OK] 混合融合测试通过: Top-3 = {[f['chunk']['label'] for f in fused]}")


if __name__ == "__main__":
    print("\n=== Retrieval Unit Tests ===\n")
    test_syntax_chunker()
    test_metadata_extraction()
    test_bm25_tokenize()
    test_hybrid_fusion()
    print("\n[OK] All tests passed!\n")
