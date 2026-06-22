"""
FastAPI 入口 — 代码 RAG 知识库问答系统
语法感知分块 + 混合检索 + Cross-BERT 重排 + DeepSeek 生成
"""
import uvicorn
import gradio as gr
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.middleware import TimerMiddleware
from app.core.config import settings

app = FastAPI(
    title="代码 RAG 知识库问答系统",
    description="""
## 项目简介

基于 **DeepSeek V4 Pro** 的企业级代码知识库问答系统，采用"语法感知分块 + 混合检索 + 重排"的技术方案，
为开发者提供准确、可溯源的代码问答服务。

### 核心技术栈

| 层级 | 技术方案 | 说明 |
|------|---------|------|
| **数据层** | LangChain 语法感知分块器 | 按 Python 函数/类边界切分，不截断语法单元 |
| **检索层** | bge-large-zh 向量 + BM25 关键词检索 | 语义理解和关键词匹配互补，加权融合 |
| **重排层** | Cross-BERT (bge-reranker-base) | 对 Top-20 候选做精排，取 Top-3 传给大模型 |
| **生成层** | DeepSeek V4 Pro + 专属 Prompt 模板 | 三套模板覆盖代码生成/解释/排错 |
| **安全层** | 幻觉校验 + 引用溯源 | 生成后反向验证关键实体是否在上下文中 |
| **工程层** | FastAPI + 缓存 + Docker + Gradio | 生产级 API 服务，支持一键部署 |

### 接口列表

| 方法 | 路径 | 功能 |
|------|------|------|
| **POST** | `/api/v1/code_qa` | 🔍 代码问答（核心接口） |
| **POST** | `/api/v1/upload_doc` | 📄 上传文档并更新知识库 |
| **GET** | `/api/v1/stats` | 📊 系统运行统计 |
| **GET** | `/api/v1/health` | 💚 健康检查 |
| **GET** | `/health` | 💚 根路径健康检查 |
""",
    version="2.0.0",
    contact={"name": "AI 研发工程师", "url": "https://github.com"},
    license_info={"name": "MIT"},
    openapi_tags=[
        {
            "name": "代码问答",
            "description": "核心问答接口 — 完整 RAG 管线：问题路由 → 缓存检查 → 向量检索 + BM25 → 混合融合 → 重排 → 压缩 → LLM 生成 → 幻觉校验",
        },
        {
            "name": "知识库管理",
            "description": "文档上传和索引管理 — 支持增量更新索引",
        },
        {
            "name": "系统监控",
            "description": "健康检查、性能统计、缓存命中率",
        },
    ],
)

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求计时中间件
app.add_middleware(TimerMiddleware)

# 注册路由
app.include_router(router)


@app.get("/", tags=["系统监控"], summary="系统首页")
async def root():
    """系统首页 — 展示可用接口和服务信息"""
    return {
        "服务名称": "代码 RAG 知识库问答系统",
        "版本": "2.0.0",
        "接口文档": "/docs",
        "Gradio界面": "/ui",
        "可用接口": {
            "代码问答": "POST /api/v1/code_qa",
            "文档上传": "POST /api/v1/upload_doc",
            "系统统计": "GET /api/v1/stats",
            "健康检查": "GET /health",
        },
    }


@app.get("/health", tags=["系统监控"], summary="健康检查")
async def health_check():
    """系统健康检查 — 返回服务状态和当前使用的模型"""
    return {
        "状态": "正常运行",
        "模型": settings.model,
        "status": "ok",
        "model": settings.model,
    }


# ═══════════════════════════════════════════════
# 挂载 Gradio 到 /ui
# ═══════════════════════════════════════════════
def _mount_gradio():
    """延迟导入 Gradio 界面，挂载到 FastAPI"""
    from frontend.gradio_app import create_rag_ui
    from frontend.theme import create_theme
    ui = create_rag_ui()
    gr.mount_gradio_app(app, ui, path="/ui", theme=create_theme())


_mount_gradio()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
    )
