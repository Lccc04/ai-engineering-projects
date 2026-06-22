"""
ReAct 研发 Agent — Streamlit 可视化界面
支持上传文件、实时展示思考过程、工具调用、代码执行结果
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import time
import json

# ─── 页面配置 ───
st.set_page_config(
    page_title="ReAct 研发 Agent",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 样式 ───
st.markdown("""
<style>
.thought-panel { background: #f5f7fa; border-radius: 8px; padding: 12px; margin: 4px 0; font-size: 0.9rem; }
.thought-panel .label { font-weight: bold; font-size: 0.75rem; color: #666; text-transform: uppercase; }
.thought-panel code { background: #e8ecf1; padding: 2px 6px; border-radius: 3px; }
.tool-call { border-left: 3px solid #4a90d9; }
.tool-result-ok { border-left: 3px solid #4caf50; }
.tool-result-err { border-left: 3px solid #f44336; }
.answer-box { background: #e8f5e9; border-radius: 8px; padding: 16px; margin: 8px 0; }
.metrics-box { font-size: 0.85rem; color: #555; }
</style>
""", unsafe_allow_html=True)


# ─── 侧边栏 ───
with st.sidebar:
    st.markdown("## 📁 工作目录")
    uploaded_file = st.file_uploader(
        "上传文件（CSV/JSON/文本）",
        type=["csv", "json", "txt", "py"],
    )
    if uploaded_file:
        from app.core.config import settings
        save_path = settings.workspace_dir / uploaded_file.name
        save_path.write_bytes(uploaded_file.getvalue())
        st.success(f"已上传: {uploaded_file.name}")

    # 显示已有文件
    from app.core.config import settings
    workspace_files = list(settings.workspace_dir.glob("*"))
    if workspace_files:
        st.markdown("**已有文件:**")
        for f in sorted(workspace_files):
            if f.is_file():
                st.caption(f"📄 {f.name}")

    st.divider()
    st.markdown("## 📊 任务统计")
    if "task_stats" not in st.session_state:
        st.session_state.task_stats = {"tasks": 0, "tools": 0, "retries": 0}

    st.metric("已完成任务", st.session_state.task_stats["tasks"])
    st.metric("工具调用总次数", st.session_state.task_stats["tools"])
    st.metric("错误重试总次数", st.session_state.task_stats["retries"])

    st.divider()
    st.markdown("## 🎯 示例问题")
    st.button("分析 sales.csv 销量趋势", on_click=lambda: None)
    st.button("写一个快速排序函数并测试", on_click=lambda: None)
    st.button("修复这段代码的 Bug", on_click=lambda: None)

    st.divider()
    st.caption("基于 DeepSeek V4 Pro + RAG 知识库")

# ─── 主区域 ───
st.title("🔧 ReAct 智能研发 Agent")
st.caption("代码执行 · 知识检索 · 文件管理 · 错误自动修复")

# 历史消息
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thought_steps" not in st.session_state:
    st.session_state.thought_steps = []

# 渲染历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("steps"):
            with st.expander("🔍 查看思考过程"):
                for step in msg["steps"]:
                    _render_step(step)

# 输入框
if prompt := st.chat_input("输入研发任务，例如: 写一个冒泡排序函数并测试性能"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.thought_steps = []

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 容器用于实时更新思考过程
        thought_expander = st.expander("🔍 思考过程 (实时)", expanded=True)
        answer_placeholder = st.empty()

        try:
            from app.agent.orchestrator import ReActAgent

            agent = ReActAgent(verbose=False)
            result = agent.run(prompt)

            answer = result["answer"]
            steps = result["steps"]
            stats = result["stats"]

            # 渲染答案
            with answer_placeholder.container():
                st.markdown(answer)

            # 渲染思考过程
            with thought_expander:
                for i, step in enumerate(steps):
                    _render_step(step)

            # 更新统计
            st.session_state.task_stats["tasks"] += 1
            st.session_state.task_stats["tools"] += stats.get("total_tool_calls", 0)
            st.session_state.task_stats["retries"] += stats.get("total_retries", 0)

            # 底部指标
            st.caption(
                f"⏱️ {result['iterations']} 轮 | "
                f"🔧 {stats.get('total_tool_calls', 0)} 次工具调用 | "
                f"🔄 {stats.get('total_retries', 0)} 次重试"
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "steps": steps,
            })

        except Exception as e:
            st.error(f"Agent 执行失败: {e}")


def _render_step(step):
    """渲染单个思考步骤"""
    if step.step_type == "user":
        st.markdown('<div class="thought-panel"><span class="label">👤 用户</span><br>' +
                     step.content[:200] + '</div>', unsafe_allow_html=True)

    elif step.step_type == "tool_result":
        is_error = "[执行失败]" in step.tool_output or "[错误]" in step.tool_output
        cls = "tool-result-err" if is_error else "tool-result-ok"
        st.markdown(
            f'<div class="thought-panel {cls}">'
            f'<span class="label">🔧 {step.tool_name}</span><br>'
            f'<pre style="white-space:pre-wrap;font-size:0.8rem;">{step.tool_output[:500]}</pre>'
            f'</div>',
            unsafe_allow_html=True,
        )

    elif step.step_type == "answer":
        st.markdown(
            f'<div class="thought-panel">'
            f'<span class="label">✅ 完成</span><br>{step.content[:300]}</div>',
            unsafe_allow_html=True,
        )

    elif step.step_type == "tool_call" and not step.success:
        st.markdown(
            f'<div class="thought-panel tool-result-err">'
            f'<span class="label">🔄 重试修复</span><br>{step.content[:200]}</div>',
            unsafe_allow_html=True,
        )
