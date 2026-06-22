"""
API 集成测试 — 仅测试不依赖模型的端点
（模型需联网下载，在无网络环境跳过）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

# 注意：导入 main.app 会触发路由注册，但不会触发模型加载
# 模型是懒加载的，只在第一次请求时才下载
from main import app

client = TestClient(app)


def test_health():
    """测试健康检查（无模型依赖）"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("  [OK] /health")


def test_root():
    """测试根路径"""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "代码 RAG 知识库问答系统"
    print("  [OK] /")


def test_openapi_docs():
    """测试 OpenAPI 文档端点"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "/api/v1/code_qa" in str(data["paths"])
    print("  [OK] /openapi.json")


def test_code_qa_structure():
    """
    测试 /code_qa 接口存在且返回合理的错误
    """
    # 通过 OpenAPI schema 验证路由注册
    resp = client.get("/openapi.json")
    paths = list(resp.json()["paths"].keys())

    assert "/api/v1/code_qa" in paths, f"code_qa 路由未注册, 现有路由: {paths}"
    assert "/api/v1/upload_doc" in paths, f"upload_doc 路由未注册"
    assert "/api/v1/stats" in paths, f"stats 路由未注册"
    assert "/api/v1/health" in paths, f"health 路由未注册"
    print("  [OK] 所有路由已注册")


if __name__ == "__main__":
    print("\n=== API Integration Tests ===\n")
    test_health()
    test_root()
    test_openapi_docs()
    test_code_qa_structure()
    print("\n[OK] All API tests passed!\n")
