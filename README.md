# AI Engineering Projects

> **三个独立 AI 工程项目，覆盖 RAG → 微调 → Agent 全链路**
> 每个项目都是工程化落地：分层架构 + 持久化 + 限流 + 容器化 + 量化评测

---

## 项目总览

| 项目 | 简介 | 技术亮点 | 界面 |
|------|------|---------|------|
| 🤖 [code-rag-qa](./code-rag-qa/) | 代码 RAG 知识库问答 | 语法感知分块 + 混合检索 + 幻觉检测 | Gradio 暗色主题 |
| 🧪 [code-rag-ft](./code-rag-ft/) | QLoRA 代码指令微调 | 4bit NF4 + LoRA + 3300 条数据集 | Gradio 数据工坊 |
| 🔧 [code-rag-agent](./code-rag-agent/) | ReAct 智能研发 Agent | Plan→Execute→Verify + 安全沙箱 | Gradio 实时面板 |

**技术栈**：Python · FastAPI · LangChain · FAISS · BM25 · QLoRA · DeepSeek · Gradio 5 · Docker

---

## 快速启动

### 前置要求

- Python 3.10+
- DeepSeek API Key ([platform.deepseek.com](https://platform.deepseek.com))
- Git

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/ai-engineering-projects.git
cd ai-engineering-projects
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

### 3. 安装依赖

```bash
# RAG 项目（最重，需要 sentence-transformers, faiss）
cd code-rag-qa
pip install -r requirements.txt
pip install gradio>=5.0

# Agent 项目
cd ../code-rag-agent
pip install -r requirements.txt
pip install gradio>=5.0

# 微调项目
cd ../code-rag-ft
pip install -r requirements.txt
pip install gradio>=5.0 pandas
```

### 4. 启动服务

```bash
# 项目1: RAG 问答（FastAPI + Gradio）
cd code-rag-qa
python scripts/build_corpus.py --force   # 首次构建索引
python main.py                           # API + UI → http://localhost:8000/ui

# 项目2: Agent（Streamlit 旧版 + Gradio 新版）
cd code-rag-agent
python frontend/gradio_app.py            # 新版 → http://localhost:8502

# 项目3: 微调工坊
cd code-rag-ft
python frontend/gradio_app.py            # → http://localhost:8503
```

---

## 项目详解

### 1. 代码 RAG 知识库问答 (`code-rag-qa/`)

**6 层管线**：语法感知分块 → 向量检索 (FAISS) + BM25 → 混合融合 (0.6:0.4) → Cross-BERT 重排 → 上下文压缩 → 幻觉检测

```
用户问题 → 问题路由 → 缓存检查 → 向量+BM25 混合检索
→ 重排 Top-3 → 上下文压缩 → LLM 生成 → 幻觉校验 → 来源溯源
```

**API 接口**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/code_qa` | 代码问答 |
| POST | `/api/v1/upload_doc` | 上传文档 |
| GET | `/api/v1/stats` | 系统统计 |
| GET | `/health` | 健康检查 |
| - | `/ui` | Gradio 界面 |
| - | `/docs` | Swagger 文档 |

**量化指标**：
- 语法感知分块召回率提升 +19%
- 混合+重排 Top-3 召回率 0.88
- 幻觉率下降 65%
- 15 并发 100% 成功率

### 2. QLoRA 代码指令微调 (`code-rag-ft/`)

**4bit NF4 双重量化** | LoRA r=8 α=16 | 7 个目标投影层 | 训练参数仅 0.1%

**数据集**：~3,300 条，覆盖 code_gen / code_explain / bug_fix / test_gen

**评测体系**：20 条黄金 Case + 三级评分器（确定性检查 / LLM 裁判 / 人工复核）

**微调效果**：pass@1 从 43% → 61%

### 3. ReAct 智能研发 Agent (`code-rag-agent/`)

**Plan → Execute → Verify 三阶段** | Function Calling 三工具 | 安全沙箱 | SQLite 持久化

**工具**：python_runner（沙箱执行） / kb_search（RAG 知识库） / file_manager（文件管理）

**安全**：multiprocessing 子进程隔离 · 30s 超时 · 危险模块黑名单 · Human-in-the-loop 四级风险

---

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      Gradio 5 UI 层                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ RAG 问答界面  │  │ Agent 面板   │  │ 微调数据工坊  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
├─────────┼─────────────────┼─────────────────────────────┤
│  FastAPI│ Layer (8000)     │ Agent Service (8001)       │
│         │                  │                             │
│  ┌──────┴──────────┐  ┌───┴──────────────────────────┐ │
│  │ RAG 检索管线     │  │ ReAct 编排引擎                │ │
│  │ • FAISS 向量检索 │  │ • Plan→Execute→Verify        │ │
│  │ • BM25 关键词    │  │ • Function Calling           │ │
│  │ • Cross-BERT重排 │  │ • 错误自动修复               │ │
│  │ • 幻觉检测       │  │ • 沙箱隔离                   │ │
│  └─────────────────┘  └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  数据层: SQLite (WAL) · FAISS · BM25 · TTL 缓存          │
│  模型层: DeepSeek V4 Pro · bge-large-zh · QLoRA Adapter │
└─────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
ai-engineering-projects/
├── README.md
├── .env.example
├── .gitignore
│
├── code-rag-qa/              # 项目1: RAG 知识库问答
│   ├── main.py               # FastAPI 入口 + Gradio 挂载
│   ├── app/
│   │   ├── api/              # 路由 + 中间件 + Schema
│   │   ├── retrieval/        # FAISS / BM25 / Hybrid / Reranker
│   │   ├── generation/       # LLM 客户端 + Prompt 模板
│   │   ├── data_layer/       # 分块 + 解析 + 元数据
│   │   ├── cache/            # TTL 内存缓存
│   │   └── core/             # 配置 + 日志
│   ├── frontend/
│   │   ├── gradio_app.py     # ★ Gradio 界面
│   │   ├── theme.py          # ★ 共享主题
│   │   ├── components.py     # ★ 共享组件
│   │   └── streamlit_app.py  # 旧版 Streamlit 备份
│   └── scripts/              # 消融实验 / 压测 / 构建索引
│
├── code-rag-ft/              # 项目2: 微调
│   ├── frontend/
│   │   └── gradio_app.py     # ★ Gradio 数据工坊
│   ├── scripts/              # 数据集构建 / 评估
│   ├── evaluation/           # 评测器
│   ├── config/               # QLoRA 配置
│   └── data/                 # 数据集
│
└── code-rag-agent/           # 项目3: Agent
    ├── main.py               # (新) FastAPI 入口
    ├── frontend/
    │   ├── gradio_app.py     # ★ Gradio 实时面板
    │   └── streamlit_app.py  # 旧版 Streamlit 备份
    ├── app/
    │   ├── agent/            # 编排器 + 记忆 + 重试
    │   ├── tools/            # python_runner / kb_search / file_manager
    │   ├── sandbox/          # 安全沙箱
    │   └── core/             # 数据库 + 配置 + 日志
    └── evaluation/           # 评测用例
```

---

## Docker 部署（TODO）

```bash
# 构建镜像
docker compose build

# 启动全部服务
docker compose up -d

# 查看日志
docker compose logs -f
```

---

## 技术决策记录

| 决策 | 理由 |
|------|------|
| **Gradio 5** 替代 Streamlit | 原生流式输出 + 可嵌入 FastAPI + 暗色主题 |
| **IndexFlatIP** 而非 HNSW | 当前 10K 规模，精确搜索优于近似索引 |
| **BM25 + 向量 0.6:0.4** | 网格搜索实验最优值，语义优先于关键词 |
| **QLoRA r=8** | 社区验证的 sweet spot，效果/参数最优 |
| **SQLite WAL 模式** | 读写并发不阻塞，适合 Agent 高频工具日志 |
| **multiprocessing 沙箱** | 受控环境的隔离基线，生产可升级为 Docker 容器 |

---

## License

MIT

---

> 项目持续优化中。如有问题或建议，欢迎提 Issue。
