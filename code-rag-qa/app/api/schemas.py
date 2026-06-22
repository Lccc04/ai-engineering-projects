"""
API 数据模型 — 请求/响应定义
所有字段描述均使用中文，方便非技术人员理解
"""
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
# 请求模型
# ═══════════════════════════════════════════

class CodeQARequest(BaseModel):
    """代码问答请求"""
    query: str = Field(
        ...,
        description="您想问的代码问题，比如：FastAPI 的路由注册是怎么实现的？",
        min_length=1,
        max_length=5000,
        examples=["FastAPI 中 APIRouter 的 add_api_route 方法是怎么实现的？"],
    )
    mode: str | None = Field(
        None,
        description="问答模式选择。不填则由系统自动识别。可选值：code_gen(代码生成)、code_explain(代码解释)、code_debug(代码排错)",
        examples=["code_gen"],
    )
    top_k: int | None = Field(
        None,
        description="召回文档数量，范围 1-10，默认 3。值越大回答越全面但速度越慢",
        ge=1,
        le=10,
    )
    use_cache: bool = Field(
        True,
        description="是否启用缓存。相同问题缓存命中后秒级返回，建议开启",
    )


# ═══════════════════════════════════════════
# 响应模型
# ═══════════════════════════════════════════

class SourceInfo(BaseModel):
    """答案引用来源"""
    file_path: str = Field(..., description="来源文件路径")
    file_name: str = Field(..., description="来源文件名")
    module_path: str = Field("", description="Python 模块路径，如 fastapi.routing")
    function_name: str = Field("", description="相关函数名")
    class_name: str = Field("", description="相关类名")
    chunk_type: str = Field("", description="代码块类型：source_code(源码) / doc_page(文档) / config(配置)")
    line_range: str = Field("", description="代码行号范围，格式：起始行-结束行")
    relevance_score: float = Field(0.0, description="相关度评分 (0-1)，越高越相关")


class CodeQAResponse(BaseModel):
    """代码问答响应"""
    query: str = Field(..., description="您提出的原始问题")
    answer: str = Field(..., description="系统生成的回答（基于检索到的上下文）")
    mode: str = Field(..., description="实际使用的问答模式")
    sources: list[SourceInfo] = Field(default_factory=list, description="回答引用的文档来源列表")
    hallucination_check: dict | None = Field(None, description="幻觉检测结果：包含 risk(风险等级) 和 verdict(判断结论)")
    cached: bool = Field(False, description="是否命中缓存。true 表示从缓存直接返回，速度极快")
    response_time_ms: float = Field(0.0, description="总响应耗时（毫秒）")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态：ok=正常")
    model: str = Field(..., description="当前使用的 LLM 模型名称")
    index_size: int = Field(0, description="知识库索引中的文档数量")


class StatsResponse(BaseModel):
    """系统统计响应"""
    index_size: int = Field(..., description="FAISS 索引中的向量总数")
    chunk_count: int = Field(..., description="知识库分块总数")
    cache_size: int = Field(..., description="当前缓存的问答对数")
    cache_hit_rate: float = Field(..., description="缓存命中率 (0-1)")
    avg_response_time_ms: float = Field(..., description="最近 100 次请求的平均响应耗时（毫秒）")
