# 三个项目运行指南

> 环境：Windows 11 · Python 3.13 · DeepSeek V4 Pro API · 所有路径和配置已就绪

---

## 一、全局配置（三个项目共用）

### 1.1 API Key 配置

文件 `code-rag-qa/.env`、`code-rag-ft/.env`、`code-rag-agent/.env` 内容相同（也可以只保留一个 `.env` 用软链接）：

```ini
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
HF_ENDPOINT=https://hf-mirror.com
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
RERANKER_MODEL=BAAI/bge-reranker-base
API_PORT=8000
STREAMLIT_PORT=8501
CACHE_TTL=3600
```

### 1.2 安装依赖

```bash
# 项目1 依赖（RAG 全链路最重）
cd f:/github-Data_Analysis-main/code-rag-qa
pip install openai sentence-transformers faiss-cpu rank-bm25 jieba \
    langchain langchain-text-splitters fastapi uvicorn streamlit \
    pydantic pydantic-settings python-dotenv httpx numpy -q

# 项目2 依赖（微调模块，较轻）
cd f:/github-Data_Analysis-main/code-rag-ft
pip install openai pydantic python-dotenv pyyaml loguru -q

# 项目3 依赖（Agent 模块）
cd f:/github-Data_Analysis-main/code-rag-agent
pip install openai pydantic python-dotenv loguru streamlit -q
```

---

## 二、项目1：代码 RAG 知识库问答系统

### 2.1 启动步骤

```bash
cd f:/github-Data_Analysis-main/code-rag-qa

# 第1步：构建语料索引（首次运行，约3-5分钟，需要下载模型）
python scripts/build_corpus.py --force

# 第2步：启动 API 服务
python main.py
# → FastAPI 运行在 http://localhost:8000
# → Swagger 文档 http://localhost:8000/docs

# 第3步（可选）：启动可视化前端
streamlit run frontend/streamlit_app.py --server.port=8501
# → 界面 http://localhost:8501
```

### 2.2 测试验证

```bash
# 命令行测试问答
curl -X POST http://localhost:8000/api/v1/code_qa \
  -H "Content-Type: application/json" \
  -d '{"query":"APIRouter 的 add_api_route 方法是怎么实现的？"}'

# 预期返回：包含 answer + sources + hallucination_check 的 JSON

# 健康检查
curl http://localhost:8000/health
# → {"status":"ok","model":"deepseek-v4-pro","index_size":25}

# 系统统计（缓存命中率/平均延迟/索引规模）
curl http://localhost:8000/api/v1/stats
```

### 2.3 消融实验 & 性能压测

```bash
# 消融实验（三种检索方案对比：纯向量 vs 混合 vs 混合+重排）
python scripts/ablation_study.py
# → 输出 data/ablation_report.json

# 性能压测（P50/P95/P99 延迟）
python scripts/benchmark.py --concurrent 3 --rounds 15
# → 输出 data/benchmark_report.json
```

### 2.4 上传文档增量索引

```bash
# 通过 API 上传
curl -X POST http://localhost:8000/api/v1/upload_doc \
  -F "file=@your_code.py"

# 或直接复制到 data/raw/ 后重建
cp your_code.py data/raw/
python scripts/build_corpus.py --force
```

### 2.5 Docker 部署

```bash
cd f:/github-Data_Analysis-main/code-rag-qa
docker compose -f docker/docker-compose.yml up -d
# → API 在 8000，Streamlit 在 8501
```

---

## 三、项目2：QLoRA 代码指令微调

### 3.1 启动步骤

```bash
cd f:/github-Data_Analysis-main/code-rag-ft

# 第1步：构建数据集（--no-llm 跳过 LLM 增强，纯本地构建，约10秒）
python scripts/build_dataset.py --no-llm
# → 产出 data/processed/dataset.jsonl (Alpaca 格式)
# → 产出 data/processed/deepseek_sft.jsonl (DeepSeek 平台格式)

# 第2步：查看训练配置
python config/qlora_config.py
# → 打印 QLoRA 所有超参数 + DeepSeek 平台配置

# 第3步：导出 YAML 配置
python scripts/export_config.py
# → 产出 config/train_config.yaml
```

### 3.2 测试验证

```bash
# 评测框架（模拟微调前后对比）
python evaluation/evaluator.py
# → 输出 微调前后效果对比表
# → 产出 data/eval_report.json

# 真实 API 评测（调用 DeepSeek V4 Pro 跑 10 条测试）
python scripts/run_eval.py --n 10
# → 产出 data/eval_baseline.json
```

### 3.3 提交 DeepSeek 平台微调

```bash
# 1. 将 data/processed/deepseek_sft.jsonl 上传到 platform.deepseek.com
# 2. 参照 config/train_config.yaml 创建 SFT 任务
# 3. 平台自动训练，产出自定义模型 API
# 4. 微调完成后，在 run_eval.py 中切换模型 ID，重新跑评测对比
```

---

## 四、项目3：ReAct 智能研发 Agent

### 4.1 启动步骤

```bash
cd f:/github-Data_Analysis-main/code-rag-agent

# 第1步：运行核心测试（验证沙箱/工具/Agent 全链路）
python scripts/test_agent.py
# → 4 项测试全部通过

# 第2步（可选）：启动可视化前端
streamlit run frontend/streamlit_app.py --server.port=8502
# → 界面 http://localhost:8502
```

### 4.2 测试验证

```bash
# 测试安全沙箱（正常代码 + 错误代码 + 危险代码拦截）
python -c "
from app.sandbox.executor import SandboxExecutor
s = SandboxExecutor(timeout=10)
print(s.execute('print(sum(range(100)))'))
print(s.execute('1/0'))
"

# 测试 Agent 完整流程（需要 API）
python -c "
from app.agent.orchestrator import ReActAgent
import os
if os.getenv('DEEPSEEK_API_KEY'):
    a = ReActAgent(verbose=True)
    r = a.run('用 Python 计算 1 到 100 的和')
    print(f'答案: {r[\"answer\"][:200]}')
    print(f'耗时: {r[\"total_ms\"]:.0f}ms')
    print(f'工具调用: {r[\"stats\"][\"total_tool_calls\"]}次')
"
```

### 4.3 查看 SQLite 数据

```bash
# 查看会话历史
python -c "
from app.core.database import db_store
sessions = db_store.list_recent()
for s in sessions:
    print(f'会话 {s[\"id\"][:8]}... | {s[\"status\"]} | {s[\"created_at\"]}')
stats = db_store.get_tool_stats()
print(f'工具统计: {stats}')
"
```

---

## 五、三个项目联动（可选）

项目3 Agent 的 `kb_search` 工具依赖项目1的 FAISS 索引：

```bash
# 确保项目1索引已构建
cd f:/github-Data_Analysis-main/code-rag-qa
python scripts/build_corpus.py --force

# 然后启动项目3 Agent
cd f:/github-Data_Analysis-main/code-rag-agent
python -c "
from app.tools.kb_search import KBSearchTool
t = KBSearchTool()
print(t.execute(query='FastAPI 路由注册'))
"
```

---

## 六、常见问题

### Q: `ModuleNotFoundError: No module named 'xxx'`

**A**: 确保在项目根目录运行（如 `cd code-rag-qa`），或安装对应依赖。

### Q: HuggingFace 模型下载失败

**A**: 检查 `.env` 中设置了 `HF_ENDPOINT=https://hf-mirror.com`（国内镜像）。

### Q: DeepSeek API 调用报错

**A**: 检查 `.env` 中 `DEEPSEEK_API_KEY` 正确。运行 `python scripts/test_api.py` 验证。

### Q: FAISS 索引不存在

**A**: 运行 `python scripts/build_corpus.py --force` 构建，确认 `data/indexes/faiss.index` 存在。

### Q: 端口被占用

**A**: 修改 `.env` 中 `API_PORT` / `STREAMLIT_PORT`。

### Q: GBK 终端乱码

**A**: 英文环境已修复。所有 print 已去掉 emoji，Python 3.13+ 可设置 `PYTHONIOENCODING=utf-8`。

---

## 七、项目启动速查卡

| 项目 | 启动命令 | 地址 |
|------|---------|------|
| RAG API | `cd code-rag-qa && python main.py` | http://localhost:8000 |
| RAG 前端 | `cd code-rag-qa && streamlit run frontend/streamlit_app.py` | http://localhost:8501 |
| RAG 消融 | `cd code-rag-qa && python scripts/ablation_study.py` | - |
| 微调数据 | `cd code-rag-ft && python scripts/build_dataset.py --no-llm` | - |
| 微调评测 | `cd code-rag-ft && python scripts/run_eval.py --n 10` | - |
| Agent 前端 | `cd code-rag-agent && streamlit run frontend/streamlit_app.py` | http://localhost:8502 |
| Agent 测试 | `cd code-rag-agent && python scripts/test_agent.py` | - |

---

## 八、面试演示流程（建议）

```bash
# 1. 启动 RAG API（展示 Swagger 文档）
cd f:/github-Data_Analysis-main/code-rag-qa && python main.py
# → 浏览器打开 http://localhost:8000/docs，展示 /code_qa 接口

# 2. 展示消融实验数据
python scripts/ablation_study.py
# → 讲纯向量 vs 混合 vs 混合+重排的召回率对比

# 3. 启动 Agent（展示 Plan→Execute→Verify + 思考过程）
cd f:/github-Data_Analysis-main/code-rag-agent
streamlit run frontend/streamlit_app.py --server.port=8502
# → 输入一个数据分析问题，展示三阶段执行过程

# 4. 展示微调数据
cd f:/github-Data_Analysis-main/code-rag-ft
python config/qlora_config.py
# → 讲数据集构成和 QLoRA 参数设计
```
