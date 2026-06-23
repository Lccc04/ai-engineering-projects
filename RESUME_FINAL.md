# 刘琛琛 — AI 应用开发工程师（1页简历）

> 邮箱: qq1299610790@163.com · 手机: 13283982127 · 籍贯: 河南省三门峡
> 2026届 · 吉林工商学院 · 数据科学与大数据技术 · 专业排名前10%
> 投递方向: AI 应用开发 / 后端开发（AI方向） · 地点不限 · 随时到岗

---

## 个人技能

| 方向 | 描述 |
|------|------|
| **AI 框架** | LangChain4j/LangGraph 企业级开发, Prompt Engineering 全栈, PGvector 向量库 |
| **RAG 全链路** | 文档 ETL → 语法感知分块 → 向量+关键词混合检索 → Cross-BERT 重排 → 幻觉检测 |
| **Agent 开发** | ReAct Agent · Plan→Execute→Verify · Function Calling · MCP Server/Skills 开发 |
| **微调** | QLoRA 4bit NF4 双重量化 · LoRA r=8 α=16 · 数据集构建与评测 |
| **后端工程** | FastAPI · Python asyncio · SQLite(WAL) · 令牌桶限流 · TTL 缓存 · Docker |
| **AI 编程** | Cursor/Claude Code/Vibe Coding · Spec-Driven Development · Harness Engineering |
| **安全** | Human-in-the-loop 风险分级 · 子进程沙箱隔离 · Prompt 注入防护 · 路径穿越防护 |
| **评测** | 消融实验 · P50/P95/P99 压测 · Recall@K/MRR · pass@1 · BLEU/ROUGE |

---

## 项目经验

### 代码 RAG 知识库问答系统
技术栈: Python · LangChain · FAISS · BM25 · Cross-BERT · FastAPI · Docker

- **Prompt 工程**：为代码场景设计3套专用 System Prompt 模板（代码生成/解释/排错），6条幻觉约束规则（仅基于上下文/不知道就说不知道/禁止编造API），temperature=0.1 低温控制；关键词路由自动识别20+意图关键词；三层幻觉抑制方案（Prompt约束+上下文压缩+实体反向匹配），幻觉率下降65%
- 独立设计 6 层 RAG 管线：**语法感知分块**(AST边界切分, chunk=600/overlap=80) → FAISS IndexFlatIP 向量检索 + **BM25**(jieba代码感知分词) → Min-Max 归一化融合(0.6:0.4) → **Cross-BERT 精排**(Top-20→Top-3) → 句子级上下文压缩(Token-35%) → **三层幻觉抑制**(Prompt约束+压缩+实体反向匹配)
- 消融实验量化：**Top-3 召回率 纯向量0.67→混合0.79→混合+重排0.88**；语法感知分块+19%；幻觉率-65%
- 工程化：FastAPI API(**令牌桶10QPS**+**TTL缓存<5ms**+Swagger中文文档) + loguru全链路 + 15并发100%成功率 + Docker Compose

### 服装图文 RAG 智能问答系统 (实习) 2024.02-2024.05
河南牛人设计网络科技有限公司

- 基于 RAG 搭建服装图文知识问答系统：多模态接入(商品图/属性/面料/穿搭规则) → 维度化分块(按品类/面料/场景,句段完整度98%) → CLIP图文联合向量化 → 混合检索 → LLM生成，单条生成<2.5s
- 修复 LangChain 相似度分布失衡(L2距离 vs 内积混用)，新增品类粗筛前置过滤 + MMR多样性检索 + 五维细粒度重排，**Top-3命中率 52%→84%，Top-1属性匹配 48%→79%**
- 3层幻觉抑制(属性校验+面料比对+回检索验证)，**幻觉率 32%→4.5%**；LCEL+实体识别实现多轮指代消解，消解准确率92%+；全链路量化评估(Recall@K/MRR+BLEU/ROUGE)，问答准确率+28pp

### QLoRA 代码指令微调
技术栈: Python · DeepSeek V4 Pro · QLoRA 4bit · Pydantic · YAML

- 自制 ~3,300条代码指令数据集：CodeAlpaca-20k筛选3k + 手工标注200条FastAPI/Pandas + 100条负例(错误+修复) + **元Prompt驱动LLM自动增强200条**(种子模板→批量扩增, 5条/批防崩塌, JSON格式强制输出)，覆盖4类任务
- 数据质量Pipeline: **Pydantic格式校验→AST语法检查→MD5去重→长度过滤**，标注来源，输出Alpaca JSONL+DeepSeek SFT格式
- **QLoRA 4bit NF4双重量化** + LoRA r=8 α=16(7个全投影层) + lr=2e-4 cosine + 3epoch batch=8，训练参数仅0.1%，**pass@1 43%→61%**
- 20条黄金Case评测体系(含成功标准/失败红线) + 三级评分器(确定性检查/LLM裁判/人工复核) + 自动化回归(--n)

### ReAct 智能研发 Agent
技术栈: Python · DeepSeek Function Calling · SQLite · multiprocessing沙箱

- **Prompt 链编排**：设计三阶段 Prompt 链驱动 Agent 任务编排——SYSTEM_PROMPT 定义行为边界和工具规则，PLAN_PROMPT 强制输出结构化子步骤，VERIFY_PROMPT 驱动自检并标记 [PASS]/[RETRY]；temperature=0.2 保证执行稳定性
- **Plan→Execute→Verify 三阶段 ReAct**：Plan拆解子步骤(t=0.1)→Execute Function Calling逐步调用→Verify反向校验(最多3次回溯)，单任务平均2.7轮调试
- 三工具: python_runner(**multiprocessing.spawn子进程隔离,30s超时,10类危险模块黑名单**) + kb_search(对接RAG索引) + file_manager(路径穿越防护)
- **SQLite 4表持久化**(WAL+外键+4索引): sessions/messages/agent_traces/tool_call_logs，支持断点续接+全链路审计
- 安全: Human-in-the-loop **四级风险分级**(LOW→CRITICAL) + exec/eval禁止 + 工具调用自动落库(参数/结果/耗时/成败)

---

## 教育背景

**吉林工商学院** · 数据科学与大数据技术 · 本科 · 2022.09 ~ 2026.06
主修: 高等数学 · Python · 数据结构与算法 · 机器学习 · 深度学习 · Linux

---

## 自我评价

全链路 AI 工程能力：独立交付 3 个 AI 项目(70+文件/7300行)，覆盖 RAG→微调→Agent。量化驱动：每个关键优化有消融实验支撑。工程化思维：分层架构+持久化+限流缓存+日志+容器化。熟悉 Vibe Coding/Claude Code/SDD 等 AI 原生开发模式，能利用 MCP/Agent Skills 高效交付。
