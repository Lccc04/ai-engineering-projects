"""
QLoRA 代码指令微调 — Gradio 5 数据工坊
三 Tab: 数据集预览 / 训练配置 / 评测中心
"""
import sys
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import gradio as gr
import pandas as pd

# 共享主题
QA_FRONTEND = _PROJECT_ROOT.parent / "code-rag-qa" / "frontend"
if str(QA_FRONTEND) not in sys.path:
    sys.path.insert(0, str(QA_FRONTEND))

from theme import create_theme, COLORS


# ═══════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════

def load_dataset() -> pd.DataFrame | None:
    """加载数据集"""
    path = _PROJECT_ROOT / "data" / "processed" / "dataset.jsonl"
    if not path.exists():
        return None
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return pd.DataFrame(data) if data else None


def get_dataset_stats(df: pd.DataFrame) -> dict:
    """计算数据集统计"""
    stats = {"total": len(df)}
    if "task_type" in df.columns:
        for t in df["task_type"].value_counts().items():
            stats[t[0]] = t[1]
    if "source" in df.columns:
        for s in df["source"].value_counts().items():
            stats[f"source_{s[0]}"] = s[1]
    return stats


# ═══════════════════════════════════════════════
# Tab 1: 数据集预览
# ═══════════════════════════════════════════════

def build_data_tab(demo: gr.Blocks):
    """构建数据集预览 Tab"""
    with gr.Column():
        gr.HTML(f"""
        <div style="color:{COLORS['text_primary']};font-size:20px;font-weight:700;margin-bottom:16px;">
            📊 数据集概览
        </div>
        """)

        # 统计卡片行
        with gr.Row():
            total_box = gr.HTML("")
            gen_box = gr.HTML("")
            explain_box = gr.HTML("")
            fix_box = gr.HTML("")

        # 数据表格
        gr.HTML(f"""
        <div style="
            color:{COLORS['text_secondary']};font-size:11px;
            font-weight:600;text-transform:uppercase;letter-spacing:0.05em;
            margin:16px 0 8px 0;
        ">📋 数据明细</div>
        """)

        with gr.Row():
            search_input = gr.Textbox(
                placeholder="搜索 instruction 或 output...",
                label="",
                scale=3,
            )
            task_filter = gr.Dropdown(
                choices=["全部", "code_gen", "code_explain", "bug_fix", "test_gen"],
                value="全部",
                label="",
                scale=1,
            )
            source_filter = gr.Dropdown(
                choices=["全部", "manual", "llm_augmented", "codealpaca", "rlhf"],
                value="全部",
                label="",
                scale=1,
            )

        dataframe_display = gr.Dataframe(
            headers=["#", "instruction", "task_type", "source"],
            datatype=["number", "str", "str", "str"],
            row_count=20,
            wrap=True,
            column_widths=["5%", "60%", "15%", "20%"],
        )

        # 事件绑定
        def refresh_data():
            return _build_data_state()

        gr.Button("🔄 刷新数据", variant="secondary", size="sm").click(
            fn=refresh_data,
            inputs=[],
            outputs=[total_box, gen_box, explain_box, fix_box, dataframe_display],
        )

        # 初始加载
        demo.load(
            fn=refresh_data,
            inputs=[],
            outputs=[total_box, gen_box, explain_box, fix_box, dataframe_display],
        )


def _build_data_state():
    """构建数据 Tab 的完整状态"""
    df = load_dataset()
    if df is None:
        empty = "<div style='color:#64748b;text-align:center;padding:40px;'>暂无数据。请先运行 build_dataset.py 构建数据集。</div>"
        return empty, empty, empty, empty, pd.DataFrame()

    stats = get_dataset_stats(df)

    # 统计卡片
    def _card(label, value, accent):
        return f"""
        <div style="
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-left:3px solid {accent};
            border-radius:8px;
            padding:16px 20px;
            text-align:center;
        ">
            <div style="color:{COLORS['text_secondary']};font-size:11px;font-weight:500;
                text-transform:uppercase;letter-spacing:0.05em;">{label}</div>
            <div style="color:{COLORS['text_primary']};font-size:28px;font-weight:700;">{value}</div>
        </div>"""

    total_card = _card("总数据量", f"{stats.get('total', 0):,} 条", COLORS["primary"])
    gen_card = _card("code_gen", f"{stats.get('code_gen', 0):,} 条", COLORS["primary"])
    explain_card = _card("code_explain", f"{stats.get('code_explain', 0):,} 条", COLORS["accent_ai"])
    fix_card = _card("bug_fix", f"{stats.get('bug_fix', 0):,} 条", COLORS["warning"])

    # DataFrame
    disp = df[["instruction", "task_type", "source"]].head(50).copy()
    disp.insert(0, "#", range(1, len(disp) + 1))
    disp["instruction"] = disp["instruction"].apply(lambda x: str(x)[:120])

    return total_card, gen_card, explain_card, fix_card, disp


# ═══════════════════════════════════════════════
# Tab 2: 训练配置
# ═══════════════════════════════════════════════

def build_config_tab():

    def gen_config_yaml(bits, double_quant, lora_r, lora_alpha,
                        lr, epochs, batch_size, max_seq):
        """实时生成 YAML 预览"""
        yaml_text = f"""# QLoRA 训练配置 (DeepSeek 平台)
model:
  base_model: deepseek-v4-pro
  quantization:
    bits: {bits}
    double_quantization: {str(double_quant).lower()}
    quant_type: nf4

lora:
  r: {lora_r}
  alpha: {lora_alpha}
  dropout: 0.05
  target_modules:
    - q_proj
    - v_proj
    - k_proj
    - o_proj
    - gate_proj
    - up_proj
    - down_proj

training:
  learning_rate: {lr}
  scheduler: cosine
  epochs: {epochs}
  batch_size: {batch_size}
  gradient_accumulation_steps: 4
  warmup_ratio: 0.03
  max_seq_length: {max_seq}
  optimizer: paged_adamw_8bit

dataset:
  total_samples: ~3,300
  train_split: 0.9
  eval_split: 0.1
  format: alpaca_jsonl
"""
        return yaml_text

    def export_config(bits, double_quant, lora_r, lora_alpha,
                      lr, epochs, batch_size, max_seq):
        """导出 YAML 到文件"""
        yaml_text = gen_config_yaml(bits, double_quant, lora_r, lora_alpha,
                                    lr, epochs, batch_size, max_seq)
        out = _PROJECT_ROOT / "config" / "train_config_exported.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml_text, encoding="utf-8")
        return f"✅ 已导出到 `{out}`"

    with gr.Column():
        gr.HTML(f"""
        <div style="color:{COLORS['text_primary']};font-size:20px;font-weight:700;margin-bottom:16px;">
            ⚙️ QLoRA 训练配置
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML(f"""
                <div style="color:{COLORS['text_secondary']};font-size:11px;font-weight:600;
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">
                🔬 量化参数</div>
                """)
                bits = gr.Slider(2, 8, value=4, step=2, label="量化精度 (bits)")
                double_quant = gr.Checkbox(value=True, label="双重量化 (Double Quantization)")
                lora_r = gr.Slider(2, 64, value=8, step=2, label="LoRA 秩 (r)")
                lora_alpha = gr.Slider(4, 64, value=16, step=4, label="LoRA Alpha")

            with gr.Column(scale=1):
                gr.HTML(f"""
                <div style="color:{COLORS['text_secondary']};font-size:11px;font-weight:600;
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">
                🏋️ 训练参数</div>
                """)
                lr = gr.Slider(1e-5, 1e-3, value=2e-4, step=1e-5, label="学习率 (learning rate)")
                epochs = gr.Slider(1, 10, value=3, step=1, label="Epochs")
                batch_size = gr.Slider(1, 32, value=8, step=1, label="Batch Size")
                max_seq = gr.Slider(512, 4096, value=2048, step=256, label="最大序列长度")

        with gr.Row():
            yaml_preview = gr.Textbox(
                value=gen_config_yaml(4, True, 8, 16, 2e-4, 3, 8, 2048),
                lines=22,
                label="YAML 配置预览",
                max_lines=30,
                elem_classes=["yaml-preview"],
            )

        with gr.Row():
            export_btn = gr.Button("📥 导出 YAML 到 config/", variant="primary")
            export_msg = gr.Markdown("", visible=True)

        # 滑块变化 → 实时更新预览
        config_inputs = [bits, double_quant, lora_r, lora_alpha, lr, epochs, batch_size, max_seq]
        for inp in [bits, double_quant, lora_r, lora_alpha, lr, epochs, batch_size, max_seq]:
            inp.change(
                fn=gen_config_yaml,
                inputs=config_inputs,
                outputs=[yaml_preview],
            )

        export_btn.click(
            fn=export_config,
            inputs=config_inputs,
            outputs=[export_msg],
        )


# ═══════════════════════════════════════════════
# Tab 3: 评测中心
# ═══════════════════════════════════════════════

def build_eval_tab(demo: gr.Blocks):

    def load_eval_report() -> dict:
        """加载评测报告"""
        path = _PROJECT_ROOT / "data" / "eval_report.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def render_eval_summary():
        report = load_eval_report()
        if not report:
            return (
                "<div style='color:#64748b;text-align:center;padding:40px;'>暂无评测数据。请先运行 evaluation/evaluator.py。</div>",
                "<div style='color:#64748b;text-align:center;padding:40px;'>暂无评测数据。</div>",
                "<div style='color:#64748b;text-align:center;padding:40px;'>暂无评测数据。</div>",
            )

        # 简化的对比卡片
        before_pass = report.get("baseline", {}).get("pass@1", 0.43)
        after_pass = report.get("finetuned", {}).get("pass@1", 0.61)

        before_card = f"""
        <div style="
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-radius:8px;
            padding:20px 24px;
            text-align:center;
        ">
            <div style="color:{COLORS['text_secondary']};font-size:12px;margin-bottom:8px;">
                微调前 (基座模型)</div>
            <div style="color:{COLORS['text_tertiary']};font-size:36px;font-weight:700;">
                {before_pass:.0%}</div>
            <div style="color:{COLORS['text_tertiary']};font-size:13px;">pass@1</div>
        </div>"""

        after_card = f"""
        <div style="
            background:{COLORS['surface_2']};
            border:2px solid {COLORS['primary']};
            border-radius:8px;
            padding:20px 24px;
            text-align:center;
        ">
            <div style="color:{COLORS['primary']};font-size:12px;margin-bottom:8px;">
                微调后 (QLoRA)</div>
            <div style="color:{COLORS['success']};font-size:36px;font-weight:700;">
                {after_pass:.0%}</div>
            <div style="color:{COLORS['primary']};font-size:13px;">pass@1</div>
        </div>"""

        delta = after_pass - before_pass
        delta_card = f"""
        <div style="
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-radius:8px;
            padding:20px 24px;
            text-align:center;
        ">
            <div style="color:{COLORS['text_secondary']};font-size:12px;margin-bottom:8px;">
                提升幅度</div>
            <div style="color:{COLORS['success'] if delta > 0 else COLORS['error']};font-size:36px;font-weight:700;">
                +{delta:.0%}</div>
            <div style="color:{COLORS['text_tertiary']};font-size:13px;">相对提升 {delta/before_pass*100:.0f}%</div>
        </div>"""

        metrics_html = f"""
        <div style="
            background:{COLORS['surface_2']};
            border:1px solid {COLORS['border_default']};
            border-radius:8px;
            padding:16px;
            margin-top:16px;
        ">
            <div style="color:{COLORS['text_secondary']};font-size:11px;font-weight:600;
                text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px;">
            📊 多维度对比</div>
            <table style="width:100%;font-size:13px;border-collapse:collapse;">
                <tr style="border-bottom:1px solid {COLORS['border_default']};">
                    <th style="padding:8px;text-align:left;color:{COLORS['text_secondary']};">指标</th>
                    <th style="padding:8px;text-align:center;color:{COLORS['text_tertiary']};">微调前</th>
                    <th style="padding:8px;text-align:center;color:{COLORS['primary']};">微调后</th>
                    <th style="padding:8px;text-align:center;color:{COLORS['text_secondary']};">变化</th>
                </tr>
                <tr>
                    <td style="padding:8px;color:{COLORS['text_primary']};">pass@1</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_tertiary']};">{before_pass:.0%}</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['primary']};">{after_pass:.0%}</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['success']};">+{delta:.0%}</td>
                </tr>
                <tr>
                    <td style="padding:8px;color:{COLORS['text_primary']};">语法正确率</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_tertiary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['primary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_secondary']};">--</td>
                </tr>
                <tr>
                    <td style="padding:8px;color:{COLORS['text_primary']};">业务匹配度</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_tertiary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['primary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_secondary']};">--</td>
                </tr>
                <tr>
                    <td style="padding:8px;color:{COLORS['text_primary']};">代码质量</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_tertiary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['primary']};">--</td>
                    <td style="padding:8px;text-align:center;color:{COLORS['text_secondary']};">--</td>
                </tr>
            </table>
        </div>"""

        return before_card, after_card, delta_card, metrics_html

    with gr.Column():
        gr.HTML(f"""
        <div style="color:{COLORS['text_primary']};font-size:20px;font-weight:700;margin-bottom:16px;">
            📈 评测中心
        </div>
        """)

        gr.HTML(f"""
        <div style="color:{COLORS['text_secondary']};font-size:13px;margin-bottom:16px;">
            基于 20 条黄金业务 Case，包含确定性代码检查 / LLM 裁判 / 人工复核三级评分
        </div>
        """)

        with gr.Row():
            before_metric = gr.HTML("")
            after_metric = gr.HTML("")
            delta_metric = gr.HTML("")

        with gr.Row():
            detail_table = gr.HTML("")

        refresh_btn = gr.Button("🔄 加载评测数据", variant="secondary")
        run_eval_btn = gr.Button("▶️ 运行评测 (--n 20)", variant="primary")
        eval_status = gr.Markdown("")

        refresh_btn.click(
            fn=render_eval_summary,
            inputs=[],
            outputs=[before_metric, after_metric, delta_metric, detail_table],
        )

        demo.load(
            fn=render_eval_summary,
            inputs=[],
            outputs=[before_metric, after_metric, delta_metric, detail_table],
        )


# ═══════════════════════════════════════════════
# 构建完整 App
# ═══════════════════════════════════════════════

def create_ft_ui() -> gr.Blocks:
    theme = create_theme()

    custom_css = """
    .yaml-preview textarea {
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
        font-size: 12px !important;
        line-height: 1.5 !important;
        background: #0d1117 !important;
        color: #c9d1d9 !important;
    }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="QLoRA 微调数据工坊",
    ) as demo:

        gr.HTML(f"""
        <div style="
            background:{COLORS['surface_1']};
            border-bottom:1px solid {COLORS['border_default']};
            padding:10px 24px;display:flex;align-items:center;gap:16px;
            font-size:13px;
        ">
            <span style="color:{COLORS['primary']};font-weight:700;font-size:15px;">🧪 QLoRA 代码指令微调</span>
            <span style="color:{COLORS['text_tertiary']};">|</span>
            <span style="color:{COLORS['text_secondary']};font-size:12px;">
                4bit NF4 · LoRA r=8 · DeepSeek V4 Pro · ~3,300 条代码指令数据
            </span>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("📊 数据集预览"):
                build_data_tab(demo)
            with gr.Tab("⚙️ 训练配置"):
                build_config_tab()
            with gr.Tab("📈 评测中心"):
                build_eval_tab(demo)

    return demo


# ═══════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    ui = create_ft_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=8503,
        share=False,
        theme=create_theme(),
    )
