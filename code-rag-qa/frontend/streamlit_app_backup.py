"""
代码 RAG 知识库 — Streamlit 可视化问答界面
支持文档上传、聊天对话、代码高亮、来源溯源、系统状态监控
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import requests
import time

# ═══════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════
st.set_page_config(
    page_title="代码 RAG 知识库问答系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "基于 DeepSeek V4 Pro 的企业级代码知识库问答系统\n\n"
                 "技术栈: 语法感知分块 + bge-large-zh + FAISS + BM25 + Cross-BERT 重排",
    },
)

# ═══════════════════════════════════════════
# 自定义样式 — 简洁专业、中文友好
# ═══════════════════════════════════════════
st.markdown("""
<style>
    /* ─── 全局字体 ─── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }

    /* ─── 主标题 ─── */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .main-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* ─── 特性标签 ─── */
    .feature-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 1.5rem;
    }
    .feature-tag {
        background: linear-gradient(135deg, #667eea15, #764ba215);
        border: 1px solid #667eea30;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        color: #667eea;
        font-weight: 500;
    }

    /* ─── 来源引用卡片 ─── */
    .source-card {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        transition: all 0.2s;
    }
    .source-card:hover {
        border-color: #667eea40;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.08);
    }
    .source-card .file-name {
        font-weight: 600;
        color: #1e293b;
        font-size: 0.9rem;
    }
    .source-card .meta {
        color: #64748b;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .source-card .score {
        display: inline-block;
        background: #667eea15;
        color: #667eea;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* ─── 答案区域 ─── */
    .answer-container {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 12px 0;
    }

    /* ─── 缓存提示 ─── */
    .cache-badge {
        display: inline-block;
        background: #10b98115;
        color: #059669;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* ─── 幻觉警告 ─── */
    .hallucination-warning {
        background: linear-gradient(135deg, #fef3c7, #fde68a);
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 10px 16px;
        margin: 8px 0;
        color: #92400e;
        font-size: 0.9rem;
    }

    /* ─── 侧边栏 ─── */
    .sidebar-section {
        background: #f8fafc;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .sidebar-section h4 {
        color: #1e293b;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 8px;
    }

    /* ─── 统计卡片 ─── */
    .stat-card {
        text-align: center;
        padding: 12px 8px;
    }
    .stat-card .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #667eea;
    }
    .stat-card .stat-label {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 2px;
    }

    /* ─── 聊天输入框优化 ─── */
    .stChatInput > div {
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        transition: border-color 0.2s;
    }
    .stChatInput > div:focus-within {
        border-color: #667eea !important;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8000"

# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
with st.sidebar:
    # Logo 和标题
    st.markdown("### 🔍 代码 RAG 知识库")
    st.caption("基于 DeepSeek V4 Pro · 企业级检索增强生成")

    st.divider()

    # ── 文档上传区 ──
    st.markdown("#### 📄 上传新文档")
    st.caption("支持 Python 源码、Markdown 文档、配置文件等")
    uploaded_file = st.file_uploader(
        "选择文件",
        type=["py", "md", "rst", "txt", "toml", "cfg", "yaml", "yml"],
        help="上传后系统会自动解析、分块、生成向量并更新检索索引",
        label_visibility="collapsed",
    )
    if uploaded_file:
        with st.spinner("正在解析文档并更新索引..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            try:
                resp = requests.post(f"{API_BASE}/api/v1/upload_doc", files=files, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"「{uploaded_file.name}」已加入知识库（共 {data.get('index_size', '?')} 条）")
                else:
                    st.error(f"上传失败：{resp.text}")
            except Exception:
                st.error("无法连接 API 服务，请确认服务已启动")

    st.divider()

    # ── 问答设置区 ──
    st.markdown("#### ⚙️ 问答设置")

    mode_labels = {
        "auto": "🤖 自动识别（推荐）",
        "code_gen": "💻 代码生成",
        "code_explain": "📖 代码解释",
        "code_debug": "🔧 代码排错",
    }
    mode_choice = st.selectbox(
        "回答模式",
        list(mode_labels.keys()),
        format_func=lambda x: mode_labels[x],
        index=0,
        help="自动识别会根据问题内容判断是生成/解释还是排错",
    )
    selected_mode = None if mode_choice == "auto" else mode_choice

    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider(
            "参考文档数",
            min_value=1, max_value=5, value=3,
            help="越多回答越全面，但速度略慢",
        )
    with col2:
        use_cache = st.toggle(
            "启用缓存加速",
            value=True,
            help="相同问题秒级返回",
        )

    st.divider()

    # ── 系统状态区 ──
    st.markdown("#### 📊 系统状态")
    status_col1, status_col2, status_col3 = st.columns(3)

    try:
        health_resp = requests.get(f"{API_BASE}/health", timeout=3)
        api_online = health_resp.status_code == 200
    except Exception:
        api_online = False

    try:
        stats_resp = requests.get(f"{API_BASE}/api/v1/stats", timeout=3)
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
        else:
            stats = None
    except Exception:
        stats = None

    with status_col1:
        st.metric(
            "API 状态",
            "🟢 在线" if api_online else "🔴 离线",
        )
    with status_col2:
        idx = stats["index_size"] if stats else 0
        st.metric("知识库文档", f"{idx:,} 条")
    with status_col3:
        hit_rate = f"{stats['cache_hit_rate']:.0%}" if stats else "--"
        st.metric("缓存命中率", hit_rate)

    if stats:
        st.progress(min(stats["cache_hit_rate"], 1.0), text="缓存效率")
        st.caption(
            f"总块数: {stats['chunk_count']} · "
            f"缓存条目: {stats['cache_size']} · "
            f"平均延迟: {stats['avg_response_time_ms']:.0f}ms"
        )
    else:
        st.warning("API 服务未连接 — 请先运行 `python main.py`")

    st.divider()

    # ── 示例问题 ──
    st.markdown("#### 💡 试试这些问题")
    example_queries = [
        "FastAPI 的路由注册是怎么实现的？",
        "Pandas 中 DataFrame 的 groupby 原理是什么？",
        "FastAPI 依赖注入怎么用？",
        "如何处理 Pandas 中的缺失值？",
    ]
    for q in example_queries:
        if st.button(q, use_container_width=True, key=f"ex_{q[:20]}"):
            st.session_state.pending_query = q

    st.divider()
    st.caption("技术栈：语法感知分块 · bge-large-zh · FAISS · BM25 · Cross-BERT · DeepSeek V4 Pro")

# ═══════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════

# ── 页面头部 ──
st.markdown('<p class="main-title">代码 RAG 知识库问答系统</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">基于 DeepSeek V4 Pro — 语法感知分块 + 向量混合检索 + Cross-BERT 重排 + 幻觉校验</p>', unsafe_allow_html=True)

# 特性标签
st.markdown("""
<div class="feature-tags">
    <span class="feature-tag">语法感知分块</span>
    <span class="feature-tag">向量+BM25 混合检索</span>
    <span class="feature-tag">Cross-BERT 重排</span>
    <span class="feature-tag">上下文压缩</span>
    <span class="feature-tag">幻觉自动检测</span>
    <span class="feature-tag">代码高亮</span>
    <span class="feature-tag">来源溯源</span>
</div>
""", unsafe_allow_html=True)

# ── 聊天历史 ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # 回答内容
        if msg["role"] == "assistant":
            st.markdown(msg["content"])
            # 来源引用
            if msg.get("sources"):
                with st.expander("📎 查看引用来源（点击展开）"):
                    for src in msg["sources"]:
                        func_info = src.get("function_name") or src.get("class_name") or ""
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="file-name">📄 {src['file_name']}</div>
                            <div class="meta">
                                模块: {src.get('module_path', '-')} &nbsp;|&nbsp;
                                位置: {func_info} &nbsp;|&nbsp;
                                行号: {src.get('line_range', '-')} &nbsp;
                                <span class="score">相关度 {src.get('relevance_score', 0):.3f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            # 幻觉检测
            if msg.get("hallucination"):
                h = msg["hallucination"]
                if h.get("hallucination_risk"):
                    st.markdown(f'<div class="hallucination-warning">⚠️ 幻觉风险提示：{h.get("verdict", "")}</div>', unsafe_allow_html=True)
            # 底部信息
            cache_badge = '<span class="cache-badge">♻ 缓存命中</span>' if msg.get("cached") else ""
            st.caption(f"⏱ {msg.get('response_time', '')}ms · 模式: {msg.get('mode', '')} {cache_badge}")
        else:
            st.markdown(msg["content"])

# ── 待发送的问题 ──
if st.session_state.pending_query:
    prompt = st.session_state.pending_query
    st.session_state.pending_query = None
else:
    prompt = st.chat_input("输入你的代码问题，例如：FastAPI 的路由注册是怎么实现的？")

if prompt:
    # 用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 API
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        status_placeholder.markdown("🔍 正在检索知识库 → 🎯 正在重排筛选 → 🤖 正在生成回答...")

        start = time.time()
        try:
            resp = requests.post(
                f"{API_BASE}/api/v1/code_qa",
                json={
                    "query": prompt,
                    "mode": selected_mode,
                    "top_k": top_k,
                    "use_cache": use_cache,
                },
                timeout=120,
            )
            status_placeholder.empty()

            if resp.status_code == 200:
                data = resp.json()
                answer = data["answer"]
                elapsed = data.get("response_time_ms", (time.time() - start) * 1000)
                sources = data.get("sources", [])
                hc = data.get("hallucination_check")
                is_cached = data.get("cached", False)

                # 渲染回答
                st.markdown(answer)

                # 幻觉警告
                if hc and hc.get("hallucination_risk"):
                    st.markdown(f'<div class="hallucination-warning">⚠️ 幻觉风险提示：{hc.get("verdict", "")}</div>', unsafe_allow_html=True)

                # 来源引用
                if sources:
                    with st.expander("📎 查看引用来源（点击展开）"):
                        for src in sources:
                            func_info = src.get("function_name") or src.get("class_name") or ""
                            st.markdown(f"""
                            <div class="source-card">
                                <div class="file-name">📄 {src['file_name']}</div>
                                <div class="meta">
                                    模块: {src.get('module_path', '-')} &nbsp;|&nbsp;
                                    位置: {func_info} &nbsp;|&nbsp;
                                    行号: {src.get('line_range', '-')} &nbsp;
                                    <span class="score">相关度 {src.get('relevance_score', 0):.3f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                # 底部状态
                cache_badge = '<span class="cache-badge">♻ 缓存命中</span>' if is_cached else ""
                response_mode = {
                    "code_gen": "代码生成", "code_explain": "代码解释", "code_debug": "代码排错"
                }.get(data.get("mode", ""), data.get("mode", ""))
                st.caption(f"⏱ {elapsed:.0f}ms · 模式: {response_mode} {cache_badge}")

                # 保存消息
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "hallucination": hc,
                    "response_time": f"{elapsed:.0f}",
                    "mode": response_mode,
                    "cached": is_cached,
                })
            else:
                st.error(f"API 返回错误 (HTTP {resp.status_code})：{resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("无法连接到 API 服务。请在终端运行 `python main.py` 启动服务后重试。")
        except requests.exceptions.Timeout:
            st.error("请求超时（>120秒），请检查网络或尝试简化问题。")
        except Exception as e:
            st.error(f"请求失败：{e}")
