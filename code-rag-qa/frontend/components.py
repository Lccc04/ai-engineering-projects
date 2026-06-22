"""
共享 UI 组件 — 来源卡片 / 幻觉检测指示器 / 状态徽章 / 代码块
三个 Gradio 项目共用
"""
import html
from theme import COLORS


# ═══════════════════════════════════════════════
# 来源引用卡片
# ═══════════════════════════════════════════════

def render_source_card(source: dict, index: int) -> str:
    """
    渲染单个来源引用卡片

    Args:
        source: {"file_path", "file_name", "function_name", "class_name",
                 "chunk_type", "line_range", "relevance_score"}
        index: 来源序号 (1-based)
    """
    file_name = source.get("file_name", source.get("file_path", "unknown"))
    func = source.get("function_name", "")
    cls = source.get("class_name", "")
    lines = source.get("line_range", "")
    score = source.get("relevance_score", 0)
    module = source.get("module_path", "")
    ctype = source.get("chunk_type", "")

    # 构建标题
    title_parts = [file_name]
    if cls:
        title_parts.append(f"class {cls}")
    if func:
        title_parts.append(f"def {func}")
    title = " · ".join(title_parts)

    # 副标题
    subtitle_parts = []
    if ctype:
        subtitle_parts.append(ctype)
    if lines:
        subtitle_parts.append(f"line {lines}")
    if module:
        subtitle_parts.append(module)
    subtitle = "  ".join(subtitle_parts)

    # 分数颜色
    if score >= 0.9:
        score_color = COLORS["success"]
    elif score >= 0.7:
        score_color = COLORS["primary"]
    else:
        score_color = COLORS["text_secondary"]

    return f"""
    <div style="
        background: {COLORS['surface_2']};
        border: 1px solid {COLORS['border_default']};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
        font-size: 13px;
        transition: background 150ms ease;
    " onmouseenter="this.style.background='{COLORS['surface_3']}'"
       onmouseleave="this.style.background='{COLORS['surface_2']}'">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span style="
                display:inline-flex;align-items:center;justify-content:center;
                min-width:18px;height:18px;border-radius:50%;
                background:{COLORS['primary']};color:#fff;
                font-size:10px;font-weight:600;line-height:1;
            ">{index}</span>
            <span style="
                color:{COLORS['text_primary']};font-weight:600;font-size:13px;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
            ">{html.escape(title)}</span>
            <span style="
                margin-left:auto;font-size:12px;font-weight:600;
                color:{score_color};white-space:nowrap;
            ">▸ {score:.2f}</span>
        </div>
        <div style="
            color:{COLORS['text_tertiary']};font-size:11px;
            font-family:'JetBrains Mono','Fira Code',Consolas,monospace;
        ">{html.escape(subtitle)}</div>
    </div>
    """


def render_sources_section(sources: list[dict]) -> str:
    """渲染完整来源引用区块"""
    if not sources:
        return ""

    cards = [render_source_card(s, i + 1) for i, s in enumerate(sources)]
    return f"""
    <div style="margin-top:12px;">
        <div style="
            color:{COLORS['text_secondary']};font-size:12px;
            font-weight:600;text-transform:uppercase;letter-spacing:0.05em;
            margin-bottom:8px;
        ">📄 检索来源 · Top {len(sources)}</div>
        {''.join(cards)}
    </div>
    """


# ═══════════════════════════════════════════════
# 幻觉检测指示器
# ═══════════════════════════════════════════════

def render_hallucination_badge(result: dict) -> str:
    """
    渲染幻觉检测结果徽章

    Args:
        result: 来自 HallucinationGuard.check() 的输出
            {"hallucination_risk", "match_rate", "found_entities", "missing_entities", "verdict"}
    """
    risk = result.get("hallucination_risk", False)
    match_rate = result.get("match_rate", 1.0)
    verdict = result.get("verdict", "")

    if not risk and match_rate >= 0.9:
        bg = "rgba(16,185,129,0.12)"
        border = COLORS["success"]
        icon = "✅"
        label = "高可信"
    elif not risk and match_rate >= 0.6:
        bg = "rgba(16,185,129,0.08)"
        border = COLORS["success"]
        icon = "✅"
        label = "可信"
    elif risk and match_rate >= 0.4:
        bg = "rgba(245,158,11,0.12)"
        border = COLORS["warning"]
        icon = "⚠️"
        label = "中等幻觉风险"
    else:
        bg = "rgba(239,68,68,0.12)"
        border = COLORS["error"]
        icon = "🚨"
        label = "高幻觉风险"

    return f"""
    <div style="
        background:{bg};
        border:1px solid {border};
        border-radius:6px;
        padding:8px 14px;
        margin-top:10px;
        font-size:12px;
        display:flex;align-items:center;gap:8px;
    ">
        <span style="font-size:14px;">{icon}</span>
        <span style="color:{COLORS['text_primary']};font-weight:500;">{label}</span>
        <span style="color:{COLORS['text_secondary']};">
            实体匹配率 {match_rate:.0%}
        </span>
        <span style="margin-left:auto;color:{COLORS['text_tertiary']};font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{html.escape(verdict)}">
            {html.escape(verdict[:50])}
        </span>
    </div>
    """


# ═══════════════════════════════════════════════
# 缓存命中 Badge
# ═══════════════════════════════════════════════

def render_cache_badge(response_time_ms: float) -> str:
    """渲染缓存命中指示器"""
    return f"""
    <div style="
        display:inline-flex;align-items:center;gap:6px;
        background:rgba(6,182,212,0.12);
        border:1px solid {COLORS['accent_ai']};
        border-radius:6px;
        padding:4px 10px;
        font-size:12px;
        color:{COLORS['accent_ai']};
        margin-top:6px;
    ">
        <span>⚡</span>
        <span>缓存命中</span>
        <span style="font-weight:600;">{response_time_ms:.0f}ms</span>
    </div>
    """


# ═══════════════════════════════════════════════
# 状态徽章
# ═══════════════════════════════════════════════

def render_status_badge(label: str, status: str = "ok") -> str:
    """
    状态小徽章

    Args:
        label: 显示文本
        status: "ok" / "warning" / "error" / "info" / "pending"
    """
    color_map = {
        "ok": (COLORS["success"], "rgba(16,185,129,0.12)"),
        "warning": (COLORS["warning"], "rgba(245,158,11,0.12)"),
        "error": (COLORS["error"], "rgba(239,68,68,0.12)"),
        "info": (COLORS["accent_ai"], "rgba(6,182,212,0.12)"),
        "pending": (COLORS["text_tertiary"], COLORS["surface_3"]),
    }
    border, bg = color_map.get(status, color_map["pending"])

    return f"""
    <span style="
        display:inline-flex;align-items:center;gap:4px;
        background:{bg};
        border:1px solid {border};
        border-radius:4px;
        padding:2px 8px;
        font-size:11px;
        font-weight:500;
        color:{border};
        white-space:nowrap;
    ">{html.escape(label)}</span>
    """


# ═══════════════════════════════════════════════
# 工具调用卡片 (Agent 用)
# ═══════════════════════════════════════════════

def render_tool_call_card(
    tool_name: str,
    arguments: str,
    result: str,
    success: bool,
    elapsed_ms: float,
    tool_type: str = "general",
) -> str:
    """
    渲染工具调用结果卡片

    Args:
        tool_name: 工具名称
        arguments: 调用参数 (JSON string, trunc to 200)
        result: 执行结果 (trunc to 500)
        success: 是否成功
        elapsed_ms: 耗时 ms
        tool_type: "general" / "search" / "code" / "file"
    """
    # 左侧色条颜色
    accent_map = {
        "search": COLORS["primary"],
        "code": COLORS["accent_ai"],
        "file": COLORS["warning"],
        "general": COLORS["primary"],
    }
    accent = accent_map.get(tool_type, COLORS["primary"])

    # 状态
    if success:
        status_icon = "✅"
        status_text = "成功"
        status_color = COLORS["success"]
    else:
        status_icon = "❌"
        status_text = "失败"
        status_color = COLORS["error"]

    # 工具图标
    icon_map = {"search": "🔍", "code": "💻", "file": "📁", "general": "🔧"}
    tool_icon = icon_map.get(tool_type, "🔧")

    # 截断
    args_short = html.escape(str(arguments)[:200])
    result_short = html.escape(str(result)[:500])

    return f"""
    <div style="
        background:{COLORS['surface_2']};
        border-left:2px solid {accent};
        border-radius:8px;
        padding:12px 16px;
        margin:8px 0;
        font-size:13px;
    ">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:16px;">{tool_icon}</span>
            <span style="color:{COLORS['text_primary']};font-weight:600;">{html.escape(tool_name)}</span>
            <span style="
                color:{status_color};font-size:12px;margin-left:auto;
            ">{status_icon} {status_text} ({elapsed_ms:.0f}ms)</span>
        </div>
        <div style="
            color:{COLORS['text_secondary']};font-size:11px;
            font-family:'JetBrains Mono','Fira Code',Consolas,monospace;
            background:{COLORS['surface_3']};border-radius:4px;
            padding:8px;margin:6px 0;white-space:pre-wrap;word-break:break-all;
        ">Args: {args_short}</div>
        <div style="
            color:{COLORS['text_primary']};font-size:12px;
            max-height:120px;overflow-y:auto;
            white-space:pre-wrap;word-break:break-word;
        ">{result_short}</div>
    </div>
    """


# ═══════════════════════════════════════════════
# 代码块
# ═══════════════════════════════════════════════

def render_code_block(code: str, language: str = "python") -> str:
    """渲染语法高亮的代码块"""
    return f"""
    <div style="
        background:{COLORS['surface_3']};
        border:1px solid {COLORS['border_default']};
        border-radius:8px;
        overflow:hidden;
        margin:8px 0;
    ">
        <div style="
            display:flex;align-items:center;justify-content:space-between;
            padding:6px 16px;
            background:{COLORS['surface_4']};
            border-bottom:1px solid {COLORS['border_default']};
        ">
            <span style="
                color:{COLORS['text_secondary']};font-size:11px;font-weight:500;
                text-transform:uppercase;letter-spacing:0.05em;
            ">{html.escape(language)}</span>
            <span style="
                color:{COLORS['text_tertiary']};font-size:11px;cursor:pointer;
            " onclick="navigator.clipboard.writeText(this.parentElement.parentElement.querySelector('pre').textContent)">
                📋 Copy
            </span>
        </div>
        <pre style="
            color:{COLORS['text_primary']};font-size:13px;line-height:1.6;
            padding:14px 16px;margin:0;overflow-x:auto;
            font-family:'JetBrains Mono','Fira Code',Consolas,monospace;
        "><code>{html.escape(code)}</code></pre>
    </div>
    """


# ═══════════════════════════════════════════════
# 统计指标卡片
# ═══════════════════════════════════════════════

def render_stat_card(
    label: str, value: str, accent_color: str = COLORS["primary"]
) -> str:
    """渲染单个统计卡片"""
    return f"""
    <div style="
        background:{COLORS['surface_2']};
        border:1px solid {COLORS['border_default']};
        border-left:3px solid {accent_color};
        border-radius:8px;
        padding:14px 16px;
        text-align:center;
    ">
        <div style="
            color:{COLORS['text_secondary']};font-size:11px;
            font-weight:500;text-transform:uppercase;letter-spacing:0.05em;
            margin-bottom:4px;
        ">{html.escape(label)}</div>
        <div style="
            color:{COLORS['text_primary']};font-size:24px;font-weight:700;
        ">{html.escape(str(value))}</div>
    </div>
    """


# ═══════════════════════════════════════════════
# 阶段时间线节点 (Agent 用)
# ═══════════════════════════════════════════════

def render_phase_dot(
    phase_name: str, status: str = "pending", sub_steps: list = None
) -> str:
    """
    渲染阶段节点（垂直时间线的一部分）

    Args:
        phase_name: "Plan" / "Execute" / "Verify"
        status: "done" / "active" / "pending"
        sub_steps: ["步骤1", "步骤2", ...]
    """
    if status == "done":
        dot_color = COLORS["success"]
        dot_bg = COLORS["success"]
        dot_glow = f"0 0 8px {COLORS['success']}"
        text_color = COLORS["success"]
        dot_char = "●"
    elif status == "active":
        dot_color = COLORS["accent_ai"]
        dot_bg = COLORS["accent_ai"]
        dot_glow = f"0 0 12px {COLORS['accent_ai']}"
        text_color = COLORS["accent_ai"]
        dot_char = "◉"
    else:
        dot_color = COLORS["border_subtle"]
        dot_bg = "transparent"
        dot_glow = "none"
        text_color = COLORS["text_tertiary"]
        dot_char = "○"

    sub_html = ""
    if sub_steps:
        items = "".join(
            f'<div style="color:{COLORS["text_secondary"]};font-size:12px;padding:2px 0;">{html.escape(s)}</div>'
            for s in sub_steps
        )
        sub_html = f"""
        <div style="margin-left:20px;margin-top:4px;">{items}</div>"""

    return f"""
    <div style="display:flex;gap:10px;padding:6px 0;">
        <div style="
            width:10px;height:10px;border-radius:50%;
            background:{dot_bg};
            border:2px solid {dot_color};
            box-shadow:{dot_glow};
            margin-top:4px;flex-shrink:0;
            transition:all 300ms ease-in-out;
        "></div>
        <div>
            <div style="
                color:{text_color};font-weight:600;font-size:13px;
            ">{dot_char} Phase: {html.escape(phase_name)}</div>
            {sub_html}
        </div>
    </div>
    """
