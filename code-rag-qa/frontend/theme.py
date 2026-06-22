"""
共享 Gradio 主题配置 — 三个项目共用

设计哲学: Clarity-First Minimalism
参考: Linear 极简克制 + Claude 温暖色调 + Perplexity 透明可溯
"""
import gradio as gr

# ═══════════════════════════════════════════════════════
# 色彩常量（暗色模式 — 默认）
# ═══════════════════════════════════════════════════════
COLORS = {
    # -- 品牌主色 --
    "primary": "#6366f1",
    "primary_hover": "#818cf8",
    "accent_ai": "#06b6d4",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",

    # -- 暗色表面层级 --
    "surface_base": "#0a0a0f",
    "surface_1": "#111118",
    "surface_2": "#18181f",
    "surface_3": "#1e1e26",
    "surface_4": "#25252d",
    "surface_input": "#1a1a22",

    # -- 文字 --
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_tertiary": "#64748b",

    # -- 边框 --
    "border_default": "#1e1e26",
    "border_subtle": "#27272f",
    "border_strong": "#3f3f4a",
    "border_focus": "#6366f1",
}

# ═══════════════════════════════════════════════════════
# Gradio 5 主题构建
# ═══════════════════════════════════════════════════════

def create_theme() -> gr.Theme:
    """创建统一的暗色主题"""
    return gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("JetBrains Mono"),
    ).set(
        # ── 页面底色 ──
        body_background_fill=COLORS["surface_base"],
        body_background_fill_dark=COLORS["surface_base"],
        block_background_fill=COLORS["surface_2"],
        block_background_fill_dark=COLORS["surface_2"],
        block_label_background_fill=COLORS["surface_1"],
        block_label_background_fill_dark=COLORS["surface_1"],
        block_title_background_fill=COLORS["surface_1"],
        block_title_background_fill_dark=COLORS["surface_1"],
        background_fill_primary=COLORS["surface_1"],
        background_fill_primary_dark=COLORS["surface_1"],
        background_fill_secondary=COLORS["surface_base"],
        background_fill_secondary_dark=COLORS["surface_base"],

        # ── 文字 ──
        body_text_color=COLORS["text_primary"],
        body_text_color_dark=COLORS["text_primary"],
        body_text_color_subdued=COLORS["text_secondary"],
        body_text_color_subdued_dark=COLORS["text_secondary"],
        block_label_text_color=COLORS["text_secondary"],
        block_label_text_color_dark=COLORS["text_secondary"],
        block_title_text_color=COLORS["text_primary"],
        block_title_text_color_dark=COLORS["text_primary"],

        # ── 边框 ──
        border_color_primary=COLORS["border_default"],
        border_color_primary_dark=COLORS["border_default"],
        border_color_accent=COLORS["border_focus"],
        border_color_accent_dark=COLORS["border_focus"],
        block_border_color=COLORS["border_default"],
        block_border_color_dark=COLORS["border_default"],
        block_border_width="1px",
        block_border_width_dark="1px",

        # ── 输入框 ──
        input_background_fill=COLORS["surface_input"],
        input_background_fill_dark=COLORS["surface_input"],
        input_border_color=COLORS["border_strong"],
        input_border_color_dark=COLORS["border_strong"],
        input_border_color_focus=COLORS["border_focus"],
        input_border_color_focus_dark=COLORS["border_focus"],
        input_text_color=COLORS["text_primary"],
        input_text_color_dark=COLORS["text_primary"],
        input_placeholder_color=COLORS["text_tertiary"],
        input_placeholder_color_dark=COLORS["text_tertiary"],

        # ── 主按钮 (Indigo) ──
        button_primary_background_fill=COLORS["primary"],
        button_primary_background_fill_dark=COLORS["primary"],
        button_primary_background_fill_hover=COLORS["primary_hover"],
        button_primary_background_fill_hover_dark=COLORS["primary_hover"],
        button_primary_text_color="#ffffff",
        button_primary_text_color_dark="#ffffff",
        button_primary_border=COLORS["primary"],
        button_primary_border_dark=COLORS["primary"],

        # ── 次按钮 ──
        button_secondary_background_fill=COLORS["surface_2"],
        button_secondary_background_fill_dark=COLORS["surface_2"],
        button_secondary_background_fill_hover=COLORS["surface_3"],
        button_secondary_background_fill_hover_dark=COLORS["surface_4"],
        button_secondary_text_color=COLORS["text_primary"],
        button_secondary_text_color_dark=COLORS["text_primary"],

        # ── 强调色/AI 色 ──
        slider_color=COLORS["accent_ai"],
        slider_color_dark=COLORS["accent_ai"],
        loader_color=COLORS["primary"],
        loader_color_dark=COLORS["primary"],

        # ── 状态色 ──
        error_text_color=COLORS["error"],
        error_text_color_dark=COLORS["error"],
        error_border_color=COLORS["error"],
        error_border_color_dark=COLORS["error"],

        # ── Tab ──
        tab_background_fill=COLORS["surface_1"],
        tab_background_fill_dark=COLORS["surface_1"],
        tab_text_color=COLORS["text_secondary"],
        tab_text_color_dark=COLORS["text_secondary"],
        tab_text_color_selected=COLORS["primary"],
        tab_text_color_selected_dark=COLORS["primary_hover"],

        # ── 表格 ──
        table_border_color=COLORS["border_default"],
        table_border_color_dark=COLORS["border_default"],
        table_even_background_fill=COLORS["surface_1"],
        table_even_background_fill_dark=COLORS["surface_1"],
        table_odd_background_fill=COLORS["surface_2"],
        table_odd_background_fill_dark=COLORS["surface_2"],

        # ── 圆角 ──
        block_radius="8px",
        block_radius_dark="8px",
        input_radius="8px",
        input_radius_dark="8px",
        button_primary_radius="8px",
        button_primary_radius_dark="8px",
        button_secondary_radius="8px",
        button_secondary_radius_dark="8px",
        checkbox_border_radius="4px",
        checkbox_border_radius_dark="4px",
        table_radius="8px",
        table_radius_dark="8px",
        panel_radius="8px",
        panel_radius_dark="8px",

        # ── 阴影 ──
        shadow_drop="0 1px 3px rgba(0,0,0,0.3)",
        shadow_drop_dark="0 1px 3px rgba(0,0,0,0.3)",
        shadow_spread="6px",
        shadow_spread_dark="6px",
    )


# 全局主题单例
theme = create_theme()
