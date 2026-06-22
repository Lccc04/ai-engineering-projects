"""
QLoRA 微调配置 — DeepSeek 平台 + 本地 HuggingFace 两套参数
"""
from pydantic import BaseModel, Field


class QLoRAConfig(BaseModel):
    """QLoRA 微调超参数"""
    # 量化
    bits: int = Field(4, description="量化精度 (4bit)")
    double_quant: bool = Field(True, description="双重量化")
    quant_type: str = Field("nf4", description="NormalFloat4")

    # LoRA
    lora_r: int = Field(8, description="LoRA 秩")
    lora_alpha: int = Field(16, description="LoRA alpha")
    lora_dropout: float = Field(0.05, description="Dropout")
    target_modules: list[str] = Field(
        default=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        description="LoRA 目标模块"
    )

    # 训练
    learning_rate: float = Field(2e-4, description="学习率")
    num_epochs: int = Field(3, description="训练轮数")
    batch_size: int = Field(8, description="批次大小")
    gradient_accumulation_steps: int = Field(4, description="梯度累积步数")
    warmup_ratio: float = Field(0.03, description="预热比例")
    max_seq_length: int = Field(2048, description="最大序列长度")

    # 优化器
    optimizer: str = Field("paged_adamw_8bit", description="优化器")
    lr_scheduler: str = Field("cosine", description="学习率调度器")


# ─── DeepSeek 平台配置 ───

DEEPSEEK_PLATFORM_CONFIG = """
# DeepSeek 微调平台任务配置
# 在 platform.deepseek.com 创建 SFT 任务时使用以下参数

model: deepseek-coder-base  # 与 V4 Pro 同架构的基座
task_type: sft
finetuning_method: lora

# LoRA 参数
lora_rank: 8
lora_alpha: 16
lora_target: q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj

# 训练参数
learning_rate: 2e-4
epochs: 3
batch_size: 8
gradient_accumulation: 4
max_length: 2048
warmup_ratio: 0.03

# 量化
quantization: 4bit
quant_type: nf4
double_quant: true

# 数据集
train_file: data/processed/deepseek_sft.jsonl
eval_split: 0.1

# 输出
output_dir: ft-output
"""


def print_config():
    """打印完整训练配置（面试用）"""
    cfg = QLoRAConfig()
    print("=" * 60)
    print("  QLoRA 微调超参数配置")
    print("=" * 60)
    for k, v in cfg.model_dump().items():
        print(f"  {k}: {v}")
    print()
    print(DEEPSEEK_PLATFORM_CONFIG)


if __name__ == "__main__":
    print_config()
