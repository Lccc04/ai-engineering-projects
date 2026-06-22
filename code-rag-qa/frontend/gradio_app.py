"""
代码 RAG 知识库问答 — Gradio 5 界面
暗色主题 · 来源引用 · 幻觉检测 · 流式输出
"""
import sys
from pathlib import Path

# 确保可以导入项目模块
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 确保本目录也在 path 中（被 main.py 导入时需要）
_FRONTEND_ROOT = Path(__file__).parent
if str(_FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRONTEND_ROOT))

import gradio as gr
import requests
import time
import json

from theme import create_theme, COLORS
from components import (
    render_sources_section,
    render_hallucination_badge,
    render_cache_badge,
)

# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════
API_BASE = "http://localhost:8000"


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def fetch_stats() -> str:
    """获取系统统计信息"""
    try:
        r = requests.get(f"{API_BASE}/api/v1/stats", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return (
                f"🟢 API Online · 索引: {data.get('index_size', '?')} docs · "
                f"缓存命中率: {data.get('cache_hit_rate', 0)*100:.0f}% · "
                f"平均延迟: {data.get('avg_response_time_ms', '?')}ms"
            )
    except Exception:
        pass
    return "🔴 API Offline"


def fetch_health() -> dict:
    """获取健康状态"""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"status": "offline", "model": "N/A", "index_size": 0}


# ═══════════════════════════════════════════════
# 核心：流式问答
# ═══════════════════════════════════════════════

def stream_qa(query: str, mode: str, top_k: int, use_cache: bool):
    """
    Generator: 逐步调用非流式 API，返回对话更新

    Gradio 5 ChatInterface 期望 generator yield 格式:
    - 字符串 → 更新 bot 回复
    - 或完整的 message list
    """
    if not query or not query.strip():
        yield "请输入您的问题。"
        return

    t_start = time.perf_counter()

    # 构建请求
    payload = {
        "query": query.strip(),
        "mode": None if mode == "自动识别" else mode,
        "top_k": top_k,
        "use_cache": use_cache,
    }

    try:
        # 调用 API（非流式 — 后端不支持 SSE，用非流式 + 模拟打字机）
        r = requests.post(
            f"{API_BASE}/api/v1/code_qa",
            json=payload,
            timeout=120,
        )

        if r.status_code != 200:
            yield f"❌ API 返回错误 ({r.status_code}): {r.text[:300]}"
            return

        data = r.json()
        answer = data.get("answer", "")
        cached = data.get("cached", False)
        sources = data.get("sources", [])
        hallucination = data.get("hallucination_check", {})
        elapsed = data.get("response_time_ms", 0)

        # ── 模拟打字机流式输出 ──
        displayed = ""
        chunk_size = max(1, len(answer) // 40)  # 约 40 步展示完
        for i in range(0, len(answer), chunk_size):
            displayed = answer[: i + chunk_size]
            time.sleep(0.02)  # 打字机节奏
            yield displayed + " ▌"

        # ── 完整答案 ──
        final = answer

        # ── 附加元数据 ──
        if cached:
            final += render_cache_badge(elapsed)

        if sources:
            final += render_sources_section(sources)

        if hallucination:
            final += render_hallucination_badge(hallucination)

        final += f'\n\n<span style="color:{COLORS["text_tertiary"]};font-size:11px;">⏱ {elapsed:.0f}ms · {data.get("mode", "")}</span>'

        yield final

    except requests.exceptions.ConnectionError:
        yield "❌ 无法连接到 API 服务。请确认已启动 `python main.py`，API 运行在 http://localhost:8000"
    except requests.exceptions.Timeout:
        yield "⏳ API 请求超时（120秒），请检查网络或简化问题重试。"
    except Exception as e:
        yield f"❌ 请求失败: {str(e)[:300]}"


# ═══════════════════════════════════════════════
# 文档上传
# ═══════════════════════════════════════════════

def upload_document(file) -> str:
    """上传文档到知识库并重建索引"""
    if file is None:
        return "⚠️ 请先选择文件"

    try:
        with open(file.name, "rb") as f:
            r = requests.post(
                f"{API_BASE}/api/v1/upload_doc",
                files={"file": (Path(file.name).name, f)},
                timeout=60,
            )
        if r.status_code == 200:
            data = r.json()
            return f"✅ 上传成功！文件 `{data.get('file_name', '?')}` 已加入知识库，索引已更新（共 {data.get('index_size', '?')} 个文档）。"
        else:
            return f"❌ 上传失败 ({r.status_code}): {r.text[:200]}"
    except Exception as e:
        return f"❌ 上传异常: {str(e)[:200]}"


# ═══════════════════════════════════════════════
# 构建 Gradio 界面
# ═══════════════════════════════════════════════

def create_rag_ui() -> gr.Blocks:
    """创建 RAG 知识库问答 Gradio 界面"""

    theme = create_theme()

    # 自定义 CSS 补充
    custom_css = """
    .main-chat { max-width: 800px; margin: 0 auto; }
    .status-bar {
        background: #111118;
        border-top: 1px solid #1e1e26;
        padding: 8px 20px;
        font-size: 12px;
        color: #94a3b8;
        text-align: center;
    }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="代码 RAG 知识库问答",
        fill_height=True,
    ) as demo:

        # ── 状态栏（顶部） ──
        gr.HTML(f"""
        <div style="
            background:{COLORS['surface_1']};
            border-bottom:1px solid {COLORS['border_default']};
            padding:10px 24px;display:flex;align-items:center;gap:16px;
            font-size:13px;
        ">
            <span style="
                color:{COLORS['primary']};font-weight:700;font-size:15px;
            ">🤖 代码 RAG 知识库问答</span>
            <span style="color:{COLORS['text_tertiary']};">|</span>
            <span style="color:{COLORS['text_secondary']};font-size:12px;" id="status-text">
                正在连接 API...
            </span>
            <span style="margin-left:auto;display:flex;gap:10px;">
                <a href="/docs" target="_blank" style="
                    color:{COLORS['primary']};text-decoration:none;font-size:12px;
                ">📖 API Docs</a>
                <a href="/api/v1/stats" target="_blank" style="
                    color:{COLORS['text_secondary']};text-decoration:none;font-size:12px;
                ">📊 Stats</a>
            </span>
        </div>
        """)

        # ── 侧边栏 + 聊天区 ──
        with gr.Row(equal_height=False):

            # ──── 侧边栏 ────
            with gr.Column(scale=1, min_width=260):
                gr.HTML(f"""
                <div style="padding:8px 0;">
                    <div style="
                        color:{COLORS['text_primary']};font-size:16px;font-weight:700;
                        margin-bottom:16px;
                    ">⚙️ 控制面板</div>
                </div>
                """)

                # 文档上传区
                gr.HTML(f"""
                <div style="
                    color:{COLORS['text_secondary']};font-size:11px;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:6px;font-weight:600;
                ">📁 上传文档</div>
                """)
                upload_file = gr.File(
                    label="",
                    file_types=[".py", ".md", ".rst", ".txt", ".toml", ".cfg", ".yaml", ".yml"],
                    height=80,
                )
                upload_btn = gr.Button("上传到知识库", variant="secondary", size="sm")
                upload_status = gr.Markdown("", visible=True)

                gr.HTML(f'<div style="height:12px;"></div>')

                # 问答模式
                gr.HTML(f"""
                <div style="
                    color:{COLORS['text_secondary']};font-size:11px;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:6px;font-weight:600;
                ">🎯 问答模式</div>
                """)
                mode_select = gr.Dropdown(
                    choices=["自动识别", "code_gen", "code_explain", "code_debug"],
                    value="自动识别",
                    label="",
                    interactive=True,
                )

                gr.HTML(f'<div style="height:8px;"></div>')

                # 高级设置
                gr.HTML(f"""
                <div style="
                    color:{COLORS['text_secondary']};font-size:11px;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:6px;font-weight:600;
                ">⚙️ 高级设置</div>
                """)
                topk_slider = gr.Slider(
                    minimum=1, maximum=5, value=3, step=1,
                    label="返回来源数 (Top-K)",
                    interactive=True,
                )
                cache_toggle = gr.Checkbox(
                    value=True, label="启用缓存",
                    interactive=True,
                )

                gr.HTML(f'<div style="height:12px;"></div>')

                # 系统状态
                gr.HTML(f"""
                <div style="
                    color:{COLORS['text_secondary']};font-size:11px;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:6px;font-weight:600;
                ">📊 系统状态</div>
                """)
                status_display = gr.Markdown(
                    fetch_stats(),
                    elem_classes=["status-display"],
                )
                refresh_btn = gr.Button("🔄 刷新状态", variant="secondary", size="sm")

                gr.HTML(f'<div style="height:16px;"></div>')

                # 示例问题
                gr.HTML(f"""
                <div style="
                    color:{COLORS['text_secondary']};font-size:11px;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:8px;font-weight:600;
                ">💬 试试这些</div>
                """)

                example_queries = [
                    "FastAPI 中 APIRouter 的 add_api_route 是怎么实现的？",
                    "DataFrame 的 groupby 底层 split-apply-combine 机制是什么？",
                    "FastAPI 中 middleware、dependency、exception_handler 的执行顺序？",
                ]
                for q in example_queries:
                    gr.Button(
                        q[:50] + "..." if len(q) > 50 else q,
                        variant="secondary",
                        size="sm",
                    ).click(
                        fn=lambda x=q: x,  # 点击填入输入框
                        outputs=[],
                    )

            # ──── 主聊天区 ────
            with gr.Column(scale=3):
                chat = gr.ChatInterface(
                    fn=stream_qa,
                    additional_inputs=[mode_select, topk_slider, cache_toggle],
                    chatbot=gr.Chatbot(height=600),
                    textbox=gr.Textbox(
                        placeholder="输入代码相关的问题，如：FastAPI 的路由注册是怎么实现的？",
                        container=True,
                        scale=7,
                    ),
                    title="",
                    description="",
                    examples=[
                        ["FastAPI 中 APIRouter 的 add_api_route 是怎么实现的？"],
                        ["Pandas DataFrame 的 groupby 底层 split-apply-combine 机制是什么？"],
                    ],
                    cache_examples=False,
                )

        # ── 底部状态栏 ──
        gr.HTML(f"""
        <div class="status-bar" id="bottom-status">
            {fetch_stats()}
        </div>
        """)

        # ── 事件绑定 ──
        upload_btn.click(
            fn=upload_document,
            inputs=[upload_file],
            outputs=[upload_status],
        )

        refresh_btn.click(
            fn=lambda: fetch_stats(),
            inputs=[],
            outputs=[status_display],
        )

    return demo


# ═══════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    ui = create_rag_ui()
    ui.queue(default_concurrency_limit=5).launch(
        server_name="0.0.0.0",
        server_port=8501,
        share=False,
        theme=create_theme(),
    )
