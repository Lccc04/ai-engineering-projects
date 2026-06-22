"""
训练配置导出 — YAML 格式供 DeepSeek 平台直接导入
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml

from config.qlora_config import QLoRAConfig


def export_yaml(output_path: Path):
    """导出 DeepSeek 平台可用的训练配置 YAML"""
    cfg = QLoRAConfig()

    config = {
        "model": {
            "base": "deepseek-coder-base",  # 与 V4 Pro 同架构
            "revision": "main",
        },
        "finetuning": {
            "method": "lora",
            "type": "qlora",
        },
        "quantization": {
            "bits": cfg.bits,
            "double_quant": cfg.double_quant,
            "quant_type": cfg.quant_type,
        },
        "lora": {
            "r": cfg.lora_r,
            "alpha": cfg.lora_alpha,
            "dropout": cfg.lora_dropout,
            "target_modules": cfg.target_modules,
        },
        "training": {
            "learning_rate": cfg.learning_rate,
            "num_epochs": cfg.num_epochs,
            "batch_size": cfg.batch_size,
            "gradient_accumulation_steps": cfg.gradient_accumulation_steps,
            "warmup_ratio": cfg.warmup_ratio,
            "max_seq_length": cfg.max_seq_length,
            "optimizer": cfg.optimizer,
            "lr_scheduler": cfg.lr_scheduler,
        },
        "dataset": {
            "train_file": "data/processed/deepseek_sft.jsonl",
            "eval_split": 0.1,
            "format": "chat_completion",
            "system_prompt": "你是一个资深 Python 工程师，请根据用户指令生成高质量代码或分析。请严格遵守指令要求，输出完整可运行的代码。",
        },
        "output": {
            "dir": "ft-output",
            "save_strategy": "epoch",
            "save_total_limit": 3,
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"训练配置已导出: {output_path}")


if __name__ == "__main__":
    output = Path(__file__).parent.parent / "config" / "train_config.yaml"
    export_yaml(output)
