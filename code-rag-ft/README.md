# QLoRA 代码指令微调模块

> **面试展示** — DeepSeek 技术栈适配，零算力门槛

## 核心价值

| 环节 | 方案 | 面试亮点 |
|------|------|---------|
| 数据 | 自建 3200 条垂类 Alpaca 数据 | 不是调 API 点按钮，而是系统化数据工程 |
| 微调 | DeepSeek 平台 QLoRA 4bit | 理解量化原理 + LoRA 参数设计 |
| 评测 | pass@1 + 语法正确率 + 多维度 | 量化对比，数据说话 |

## 快速开始

```bash
cd code-rag-ft
pip install -r requirements.txt

# Step 1: 构建数据集
python scripts/build_dataset.py
# → 产出 data/processed/dataset.jsonl (Alpaca 格式)
# → 产出 data/processed/deepseek_sft.jsonl (DeepSeek 平台格式)

# Step 2: 查看训练配置
python config/qlora_config.py

# Step 3: 上传 deepseek_sft.jsonl 到 DeepSeek 平台
#         创建 SFT 任务，平台自动完成训练

# Step 4: 运行评测（微调前后对比）
python evaluation/evaluator.py
# → 产出 data/eval_report.json
```

## 项目结构
```
code-rag-ft/
├── data/
│   ├── raw/              # 原始 CodeAlpaca 数据
│   ├── processed/        # 处理后的 JSONL
│   └── schema.py         # AlpacaItem 数据模型 + 校验
├── config/
│   └── qlora_config.py   # QLoRA 超参数 + 平台配置
├── evaluation/
│   └── evaluator.py      # pass@1 / 语法正确率 / 多维度评测
└── scripts/
    └── build_dataset.py  # 数据集构建器
```

## 数据集构成

| 来源 | 数量 | 说明 |
|------|------|------|
| CodeAlpaca 筛选 | ~3000 | 高质量 Python 代码数据 |
| 手工标注 | ~200 | FastAPI/Pandas 业务场景 |
| 负例优化 | ~100 | 常见错误 + 修复方案 |

## QLoRA 训练参数

- 量化精度：4bit (nf4)
- LoRA 秩：r=8, alpha=16
- 学习率：2e-4，训练 3 epoch
- batch_size=8, 梯度累积 4 步
- 目标模块：q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj
