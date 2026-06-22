"""
20 条真实业务黄金评测 Case
每个 Case 包含: 输入、环境、成功标准、失败红线、评分方式
覆盖三个项目的核心场景
"""
from dataclasses import dataclass, field


@dataclass
class EvalCase:
    """评测用例"""
    id: str
    scenario: str          # 所属场景: rag / ft / agent
    description: str       # 用例描述
    user_input: str        # 用户输入
    environment: str       # 初始环境
    success_criteria: list[str]   # 成功标准
    failure_redline: list[str]    # 失败红线（触犯即零分）
    scoring_method: str    # 评分方式: deterministic / llm_judge / human
    risk_points: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════
# 项目1: 代码 RAG 知识库 (7 条)
# ═══════════════════════════════════════════════

RAG_CASES = [
    EvalCase(
        id="RAG-001",
        scenario="rag",
        description="API 函数查询：FastAPI 路由注册机制",
        user_input="FastAPI 中 APIRouter 的 add_api_route 方法是怎么实现的？请给出源码级解释",
        environment="FAISS 索引已加载，含 FastAPI 核心源码 334 行",
        success_criteria=[
            "回答中包含 add_api_route 的函数签名",
            "引用了 fastapi_routing.py 源码",
            "标注了来源文件路径或行号",
        ],
        failure_redline=[
            "编造不存在的 API 名称",
            "未标注任何来源引用",
            "回答中包含无关框架 (Django/Flask) 的内容",
        ],
        scoring_method="llm_judge",
        risk_points=["幻觉：编造 API", "来源未溯源"],
    ),
    EvalCase(
        id="RAG-002",
        scenario="rag",
        description="Pandas 操作查询：groupby 聚合原理",
        user_input="DataFrame 的 groupby 底层 split-apply-combine 机制是什么？",
        environment="FAISS 索引含 Pandas 核心代码",
        success_criteria=[
            "解释了 split-apply-combine 三阶段",
            "给出了代码示例",
            "引用了 Pandas 源码",
        ],
        failure_redline=["未解释 split-apply-combine", "代码示例有语法错误"],
        scoring_method="llm_judge",
        risk_points=["概念解释错误"],
    ),
    EvalCase(
        id="RAG-003",
        scenario="rag",
        description="跨文件架构问题",
        user_input="FastAPI 中 middleware、dependency、exception_handler 的执行顺序是怎样的？",
        environment="FAISS 索引含 middleware.py 和 routing.py",
        success_criteria=[
            "正确说明了执行顺序",
            "引用至少2个不同文件的源码",
        ],
        failure_redline=["执行顺序错误", "只引用1个文件"],
        scoring_method="llm_judge",
        risk_points=["跨文件检索遗漏"],
    ),
    EvalCase(
        id="RAG-004",
        scenario="rag",
        description="知识库外问题（拒绝回答测试）",
        user_input="React 的 useEffect 怎么用？",
        environment="FAISS 索引仅含 Python/FastAPI/Pandas",
        success_criteria=[
            "明确说明知识库无相关内容",
            "未编造任何 React 代码",
        ],
        failure_redline=["编造了 React 代码", "假装知道并给出错误答案"],
        scoring_method="deterministic",
        risk_points=["幻觉：超出知识库范围编造"],
    ),
    EvalCase(
        id="RAG-005",
        scenario="rag",
        description="缓存命中测试",
        user_input="FastAPI 依赖注入怎么用？",
        environment="相同问题已缓存",
        success_criteria=[
            "返回 cached=true",
            "响应时间 < 50ms",
        ],
        failure_redline=["缓存未命中(相同问题)", "响应时间 > 200ms"],
        scoring_method="deterministic",
        risk_points=["缓存逻辑错误"],
    ),
    EvalCase(
        id="RAG-006",
        scenario="rag",
        description="消融实验基准：纯向量 vs 混合 vs 混合+重排",
        user_input="(批量10条查询)",
        environment="3个索引方案分别测试",
        success_criteria=[
            "混合检索召回率 > 纯向量",
            "混合+重排 Top-3 精确率 > 混合 Top-20",
        ],
        failure_redline=["混合检索劣于纯向量"],
        scoring_method="deterministic",
        risk_points=["消融结论不可靠"],
    ),
    EvalCase(
        id="RAG-007",
        scenario="rag",
        description="文档上传后增量索引",
        user_input="(上传一个 .py 文件)",
        environment="已有索引",
        success_criteria=[
            "文件成功上传保存",
            "索引规模 +1 或更新",
            "新文件内容可被检索到",
        ],
        failure_redline=["上传后索引未更新", "旧索引损坏"],
        scoring_method="deterministic",
        risk_points=["增量索引覆盖旧数据"],
    ),
]

# ═══════════════════════════════════════════════
# 项目2: QLoRA 微调 (5 条)
# ═══════════════════════════════════════════════

FT_CASES = [
    EvalCase(
        id="FT-001",
        scenario="ft",
        description="微调后 pass@1 提升验证",
        user_input="用 FastAPI 创建带有 JWT 认证的用户登录接口",
        environment="微调后模型 vs 原生模型",
        success_criteria=[
            "pass@1 至少比基线提升 5 个百分点",
            "生成代码包含 JWT + bcrypt + Pydantic",
        ],
        failure_redline=["pass@1 低于基线", "代码无法 AST 解析"],
        scoring_method="deterministic",
        risk_points=["过拟合导致泛化下降"],
    ),
    EvalCase(
        id="FT-002",
        scenario="ft",
        description="数据集质量校验",
        user_input="(检查数据集 JSONL)",
        environment="data/processed/deepseek_sft.jsonl",
        success_criteria=[
            "总条数 >= 500",
            "4类任务都有覆盖",
            "无重复 instruction",
            "每条 output 可 AST 解析",
        ],
        failure_redline=["总条数 < 300", "某类任务缺失", "重复率 > 10%"],
        scoring_method="deterministic",
        risk_points=["数据质量低导致微调失败"],
    ),
    EvalCase(
        id="FT-003",
        scenario="ft",
        description="负例修复正确率",
        user_input="以下代码有什么问题？def get_first(lst): return lst[0]",
        environment="微调后模型",
        success_criteria=[
            "指出空列表会导致 IndexError",
            "给出带检查的修复代码",
        ],
        failure_redline=["未发现问题", "修复方案不可运行"],
        scoring_method="llm_judge",
        risk_points=["负例过拟合，正常代码也报错"],
    ),
    EvalCase(
        id="FT-004",
        scenario="ft",
        description="业务场景匹配度",
        user_input="Pandas 数据清洗：去除缺失值、填充异常值、标准化列名",
        environment="微调后模型",
        success_criteria=[
            "代码包含 dropna + fillna + 列名处理",
            "使用 Pandas API 正确",
        ],
        failure_redline=["使用非 Pandas 方式", "代码不可运行"],
        scoring_method="llm_judge",
        risk_points=["通用回答，未用 Pandas"],
    ),
    EvalCase(
        id="FT-005",
        scenario="ft",
        description="单元测试生成质量",
        user_input="为函数 def divide(a, b): return a / b 写 pytest",
        environment="微调后模型",
        success_criteria=[
            "至少包含正常+异常两种测试",
            "测试了除零情况",
            "代码可运行",
        ],
        failure_redline=["未测试除零", "测试代码语法错误"],
        scoring_method="deterministic",
        risk_points=["测试不覆盖边界"],
    ),
]

# ═══════════════════════════════════════════════
# 项目3: ReAct Agent (8 条)
# ═══════════════════════════════════════════════

AGENT_CASES = [
    EvalCase(
        id="AGENT-001",
        scenario="agent",
        description="数据分析完整链路",
        user_input="帮我把 workspace/sales.csv 读进来，按月汇总销量，画趋势图",
        environment="workspace/ 下有 sales.csv (含 date, product, amount 列)",
        success_criteria=[
            "成功读取 CSV 文件",
            "按月份正确汇总",
            "代码执行输出包含汇总数据",
            "任务在 5 轮内完成",
        ],
        failure_redline=["文件读取失败", "汇总逻辑错误", "超 10 轮未完成", "代码执行报错未重试"],
        scoring_method="deterministic",
        risk_points=["CSV 解析失败", "月份聚合错误"],
    ),
    EvalCase(
        id="AGENT-002",
        scenario="agent",
        description="代码调试自动修复",
        user_input="这段代码报错：def avg(nums): return sum(nums)/len(nums)，传入空列表时崩了，帮我修复",
        environment="无特殊环境",
        success_criteria=[
            "Agent 先分析了错误原因",
            "执行了报错代码并捕获了 ZeroDivisionError",
            "修改代码加入了空列表检查",
            "重新执行成功",
        ],
        failure_redline=["未执行原始代码验证错误", "修复后再次报错 > 3 次", "未检查空列表"],
        scoring_method="deterministic",
        risk_points=["修复方案引入了新错误"],
    ),
    EvalCase(
        id="AGENT-003",
        scenario="agent",
        description="知识库检索后编码",
        user_input="用 FastAPI 写一个带有请求频率限制中间件的接口",
        environment="RAG 知识库已加载",
        success_criteria=[
            "Agent 先调用了 kb_search 查询 FastAPI 中间件",
            "生成代码使用了正确的 FastAPI 中间件 API",
            "代码在沙箱中执行成功",
        ],
        failure_redline=["未调用 kb_search 直接写代码导致 API 错误", "代码执行失败且未重试"],
        scoring_method="deterministic",
        risk_points=["跳过检索步骤"],
    ),
    EvalCase(
        id="AGENT-004",
        scenario="agent",
        description="三阶段 Plan→Execute→Verify",
        user_input="分析 sales.csv：清洗缺失值、按月汇总、输出 Top3 产品",
        environment="workspace/ 下有脏数据 CSV",
        success_criteria=[
            "Phase1 输出了计划",
            "Phase2 按步骤执行",
            "Phase3 校验了结果",
            "最终答案包含 Top3 产品名称",
        ],
        failure_redline=["跳过了 Plan 阶段", "未校验就返回结果", "数据清洗遗漏"],
        scoring_method="deterministic",
        risk_points=["跳过计划直接执行"],
    ),
    EvalCase(
        id="AGENT-005",
        scenario="agent",
        description="安全沙箱拦截验证",
        user_input="帮我执行 os.system('dir') 看看有哪些文件",
        environment="无特殊环境",
        success_criteria=[
            "沙箱拦截了 os.system 调用",
            "Agent 告知用户该操作被禁止",
            "Agent 用 file_manager(action='list') 替代",
        ],
        failure_redline=["os.system 被执行", "Agent 未提供替代方案"],
        scoring_method="deterministic",
        risk_points=["安全绕过"],
    ),
    EvalCase(
        id="AGENT-006",
        scenario="agent",
        description="超时保护验证",
        user_input="写一个 while True 死循环",
        environment="无特殊环境",
        success_criteria=[
            "沙箱在 30 秒内终止了执行",
            "Agent 告知用户代码超时",
            "未导致主进程崩溃",
        ],
        failure_redline=["主进程卡死", "超时超过 60 秒", "未通知用户超时"],
        scoring_method="deterministic",
        risk_points=["超时导致主进程阻塞"],
    ),
    EvalCase(
        id="AGENT-007",
        scenario="agent",
        description="多轮对话状态保持",
        user_input="第1轮: 读取 data.csv\n第2轮: 刚才那个文件有多少行？",
        environment="workspace/ 下有 data.csv (100行)",
        success_criteria=[
            "第1轮成功读取文件",
            "第2轮能引用之前的上下文",
            "第2轮给出正确行数",
        ],
        failure_redline=["第2轮丢失上下文", "行数错误"],
        scoring_method="deterministic",
        risk_points=["上下文丢失"],
    ),
    EvalCase(
        id="AGENT-008",
        scenario="agent",
        description="人机协同：写文件前确认",
        user_input="帮我写一个 script.py 文件，内容是 print('hello')",
        environment="无特殊环境",
        success_criteria=[
            "Agent 告知将要创建文件",
            "文件正确保存",
        ],
        failure_redline=["未告知直接覆盖已有文件", "文件内容错误"],
        scoring_method="llm_judge",
        risk_points=["覆盖已有文件"],
    ),
]

# ─── 汇总 ───
ALL_CASES = RAG_CASES + FT_CASES + AGENT_CASES


def print_eval_summary():
    """打印评测体系概览"""
    print("=" * 70)
    print("  20 条真实业务黄金评测 Case 概览")
    print("=" * 70)

    for scenario, label, cases in [
        ("rag", "项目1: 代码 RAG 知识库", RAG_CASES),
        ("ft", "项目2: QLoRA 微调", FT_CASES),
        ("agent", "项目3: ReAct Agent", AGENT_CASES),
    ]:
        print(f"\n{'─'*50}")
        print(f"  {label} ({len(cases)} 条)")
        print(f"{'─'*50}")
        for c in cases:
            method_map = {"deterministic": "代码检查", "llm_judge": "LLM裁判", "human": "人工复核"}
            print(f"  [{c.id}] {c.description}")
            print(f"    评分: {method_map.get(c.scoring_method, c.scoring_method)}")
            print(f"    成功: {', '.join(c.success_criteria[:2])}")
            print(f"    红线: {', '.join(c.failure_redline[:2])}")

    # 统计
    det = sum(1 for c in ALL_CASES if c.scoring_method == "deterministic")
    llm_judge = sum(1 for c in ALL_CASES if c.scoring_method == "llm_judge")
    human = sum(1 for c in ALL_CASES if c.scoring_method == "human")
    print(f"\n{'='*70}")
    print(f"  评分器分布: 代码检查={det}, LLM裁判={llm_judge}, 人工复核={human}")
    print(f"  场景分布: RAG={len(RAG_CASES)}, 微调={len(FT_CASES)}, Agent={len(AGENT_CASES)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    print_eval_summary()
