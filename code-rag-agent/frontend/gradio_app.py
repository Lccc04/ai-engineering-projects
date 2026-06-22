"""
ReAct 智能研发 Agent — Gradio 5 实时面板
Plan→Execute→Verify 三阶段可视化 · 工具调用卡片 · 垂直时间线
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import gradio as gr
import time

# 共享主题（从 code-rag-qa/frontend 导入）
QA_FRONTEND = _PROJECT_ROOT.parent / "code-rag-qa" / "frontend"
if str(QA_FRONTEND) not in sys.path:
    sys.path.insert(0, str(QA_FRONTEND))

from theme import create_theme, COLORS
from components import (
    render_tool_call_card,
    render_phase_dot,
    render_code_block,
    render_status_badge,
)

# ═══════════════════════════════════════════════
# 核心：流式 Agent 执行
# ═══════════════════════════════════════════════

def run_agent_stream(message: str, history: list):
    """
    Generator: 逐步执行 Agent，yield Gradio 对话格式

    每个 yield 返回完整的对话历史，Gradio 会自动 diff 渲染
    """
    if not message or not message.strip():
        yield history
        return

    # 添加用户消息
    history.append({"role": "user", "content": message})
    yield history

    # 初始化 Agent
    try:
        from app.agent.orchestrator import ReActAgent
        agent = ReActAgent(verbose=False)
    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Agent 初始化失败: {e}"})
        yield history
        return

    # ── 累积 AI 回复 ──
    bot_content = ""
    tool_calls_html = []
    phase_html = []
    current_phase = ""
    stats_info = {}

    try:
        for event in agent.run_stream(message):
            event_type = event.get("type", "")

            if event_type == "phase":
                phase_name = event.get("phase", "")
                attempt = event.get("attempt", 1)
                status_label = f"{phase_name.upper()} ({'重试' if attempt > 1 else '第' + str(attempt) + '轮'})"

                if phase_name == "plan":
                    current_phase = "plan"
                    phase_html.append(
                        render_phase_dot("Plan (规划)", "active" if attempt == 1 else "done",
                                        [f"分析需求: {message[:80]}..."])
                    )
                elif phase_name == "execute":
                    if current_phase == "plan":
                        phase_html[-1] = render_phase_dot("Plan (规划)", "done",
                                                         [f"分析需求: {message[:80]}..."])
                    current_phase = "execute"
                    phase_html.append(
                        render_phase_dot("Execute (执行)", "active",
                                        ["逐步调用工具..."])
                    )
                elif phase_name == "verify":
                    if current_phase == "execute":
                        phase_html[-1] = render_phase_dot("Execute (执行)", "done",
                                                         ["工具调用完成"])
                    current_phase = "verify"
                    phase_html.append(
                        render_phase_dot("Verify (校验)", "active",
                                        ["验证执行结果..."])
                    )

            elif event_type == "tool_start":
                tool_name = event.get("tool", "?")
                args = event.get("args", {})
                tool_calls_html.append(f"""
                <div style="
                    background:{COLORS['surface_2']};
                    border-left:2px solid {COLORS['accent_ai']};
                    border-radius:4px;
                    padding:8px 12px;
                    margin:4px 0;
                    font-size:12px;
                ">
                    <span style="color:{COLORS['accent_ai']};">⏳</span>
                    <span style="color:{COLORS['text_primary']};font-weight:600;">{tool_name}</span>
                    <span style="color:{COLORS['text_secondary']};margin-left:8px;font-family:monospace;font-size:11px;">
                        {str(args)[:120]}
                    </span>
                </div>
                """)

            elif event_type == "tool_result":
                tool_name = event.get("tool", "?")
                result = event.get("result", "")
                success = event.get("success", True)
                elapsed = event.get("elapsed_ms", 0)

                # 替换最后一条 pending 卡片
                if tool_calls_html:
                    icon = "✅" if success else "❌"
                    color = COLORS["success"] if success else COLORS["error"]
                    tool_calls_html[-1] = f"""
                    <div style="
                        background:{COLORS['surface_2']};
                        border-left:2px solid {color};
                        border-radius:4px;
                        padding:8px 12px;
                        margin:4px 0;
                        font-size:12px;
                    ">
                        <span>{icon}</span>
                        <span style="color:{COLORS['text_primary']};font-weight:600;">{tool_name}</span>
                        <span style="color:{COLORS['text_tertiary']};margin-left:8px;">{elapsed:.0f}ms</span>
                        <div style="
                            color:{COLORS['text_secondary']};font-size:11px;margin-top:4px;
                            max-height:80px;overflow-y:auto;
                        ">{str(result)[:300]}</div>
                    </div>
                    """

            elif event_type == "trace":
                # 不显示在对话中，仅记录
                pass

            elif event_type == "answer":
                bot_content = event.get("content", "")
                # 最终阶段完成
                if current_phase and phase_html:
                    phase_html[-1] = render_phase_dot(
                        {"plan": "Plan (规划)", "execute": "Execute (执行)", "verify": "Verify (校验)"}.get(current_phase, current_phase),
                        "done",
                        ["✅ 完成"]
                    )

            elif event_type == "stats":
                stats_info = {
                    "iterations": event.get("iterations", 0),
                    "tool_calls": event.get("tool_calls", 0),
                    "retries": event.get("retries", 0),
                    "elapsed_ms": event.get("elapsed_ms", 0),
                }

            elif event_type == "error":
                bot_content += f"\n\n❌ {event.get('message', '未知错误')}"
                break

    except Exception as e:
        bot_content += f"\n\n❌ Agent 执行异常: {str(e)[:300]}"

    # ── 组装最终回复 ──
    final_content = bot_content

    # 添加阶段时间线
    if phase_html:
        final_content += f"""
        <div style="margin-top:16px;padding:12px 16px;
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-radius:8px;">
            <div style="
                color:{COLORS['text_secondary']};font-size:11px;
                font-weight:600;text-transform:uppercase;letter-spacing:0.05em;
                margin-bottom:8px;
            ">📋 执行阶段</div>
            {"".join(phase_html)}
        </div>
        """

    # 添加工具调用记录
    if tool_calls_html:
        final_content += f"""
        <div style="margin-top:12px;padding:12px 16px;
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-radius:8px;">
            <div style="
                color:{COLORS['text_secondary']};font-size:11px;
                font-weight:600;text-transform:uppercase;letter-spacing:0.05em;
                margin-bottom:8px;
            ">🔧 工具调用记录</div>
            {"".join(tool_calls_html)}
        </div>
        """

    # 添加统计信息
    if stats_info:
        final_content += f"""
        <div style="
            margin-top:12px;display:flex;gap:12px;flex-wrap:wrap;
        ">
            {render_status_badge(f"工具: {stats_info.get('tool_calls', 0)}次", "info")}
            {render_status_badge(f"重试: {stats_info.get('retries', 0)}次", "warning" if stats_info.get('retries', 0) > 0 else "ok")}
            {render_status_badge(f"耗时: {stats_info.get('elapsed_ms', 0):.0f}ms", "ok")}
            {render_status_badge(f"迭代: {stats_info.get('iterations', 0)}轮", "info")}
        </div>
        """

    if not final_content:
        final_content = "Agent 未返回任何内容。"

    history.append({"role": "assistant", "content": final_content})
    yield history


# ═══════════════════════════════════════════════
# 构建 Gradio 界面
# ═══════════════════════════════════════════════

def create_agent_ui() -> gr.Blocks:
    theme = create_theme()

    custom_css = """
    .agent-chat { max-width: 900px; margin: 0 auto; }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="ReAct 智能研发 Agent",
        fill_height=True,
    ) as demo:

        # ── 顶部栏 ──
        gr.HTML(f"""
        <div style="
            background:{COLORS['surface_1']};
            border-bottom:1px solid {COLORS['border_default']};
            padding:10px 24px;display:flex;align-items:center;gap:16px;
            font-size:13px;
        ">
            <span style="color:{COLORS['accent_ai']};font-weight:700;font-size:15px;">🔧 ReAct 智能研发 Agent</span>
            <span style="color:{COLORS['text_tertiary']};">|</span>
            <span style="color:{COLORS['text_secondary']};font-size:12px;">
                Plan → Execute → Verify · DeepSeek V4 Pro · 安全沙箱
            </span>
            <span style="margin-left:auto;color:{COLORS['text_secondary']};font-size:12px;">
                🟢 Agent Ready
            </span>
        </div>
        """)

        # ── 说明区 ──
        gr.Markdown(f"""
        <div style="
            color:{COLORS['text_secondary']};font-size:13px;
            padding:8px 24px;background:{COLORS['surface_base']};
            border-bottom:1px solid {COLORS['border_subtle']};
        ">
        💡 支持：代码执行 (python_runner) · 知识检索 (kb_search) · 文件管理 (file_manager) |
        每次任务都会展示 Plan → Execute → Verify 的完整思考过程
        </div>
        """)

        # ── 主聊天区 ──
        chat = gr.ChatInterface(
            fn=run_agent_stream,
            chatbot=gr.Chatbot(height=650),
            textbox=gr.Textbox(
                placeholder="输入研发任务，例如：用 Python 读取 sales.csv 并生成月度销售趋势折线图",
                container=True,
                scale=7,
            ),
            title="",
            description="",
            examples=[
                "用 Python 计算 1 到 100 的和",
                "写一个快速排序函数并测试其性能",
                "用 Python 读取 sales.csv 分析月度销售趋势",
            ],
            cache_examples=False,
        )

        # ── 底部状态 ──
        gr.HTML(f"""
        <div style="
            background:{COLORS['surface_1']};
            border-top:1px solid {COLORS['border_default']};
            padding:8px 24px;text-align:center;
            font-size:11px;color:{COLORS['text_tertiary']};
        ">
            Model: deepseek-v4-pro · Sandbox timeout: 30s · Max retries: 3 · Max iterations: 10
        </div>
        """)

    return demo


# ═══════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    ui = create_agent_ui()
    ui.queue(default_concurrency_limit=3).launch(
        server_name="0.0.0.0",
        server_port=8502,
        share=False,
        theme=create_theme(),
    )
