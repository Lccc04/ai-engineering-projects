"""
Prompt 模板库 — 3 套模板 + 双模式问答路由
"""
from enum import Enum


class QueryMode(str, Enum):
    """问答模式"""
    CODE_GEN = "code_gen"        # 代码生成
    CODE_EXPLAIN = "code_explain"  # 代码解释
    CODE_DEBUG = "code_debug"     # 代码排错


# ─── System Prompt 核心约束 ───

SYSTEM_CONSTRAINTS = """
【核心规则 — 必须严格遵守】
1. 你只能根据下方「参考资料」中的内容回答问题。
2. 如果参考资料中没有相关信息，你必须明确回答："根据现有资料无法解答此问题"。
3. 禁止编造任何未在参考资料中出现过的 API、函数、类名或配置参数。
4. 对于代码类问题，必须输出可直接运行的完整代码，并附带逐行逻辑解释。
5. 答案末尾必须标注引用来源，格式：[来源: 文件名 | 模块.函数名 | L行号范围]
6. 如果参考资料不足以完整回答，先给出已有的部分，再说明哪些信息缺失。
"""

# ─── 代码生成模板 ───

CODE_GEN_TEMPLATE = """
{system_constraints}

## 参考资料
{context}

## 用户需求
{query}

请生成满足需求的可运行 Python 代码，并对关键逻辑做逐行解释。
输出格式：
1. **思路分析**：简述实现思路
2. **完整代码**：```python ... ```
3. **逐行解释**：对关键行标注解释
4. **来源引用**：[来源: 文件名 | 函数名 | L行号]
"""

# ─── 代码解释模板 ───

CODE_EXPLAIN_TEMPLATE = """
{system_constraints}

## 参考资料
{context}

## 待解释的代码
{query}

请逐行解释这段代码的逻辑、关键函数的作用、以及涉及的框架/库概念。
输出格式：
1. **整体概述**：这段代码的功能
2. **逐行分析**：
   - L{行号}: `代码片段` — 解释
3. **关键概念**：涉及的框架/库知识点
4. **来源引用**：[来源: 文件名 | 函数名 | L行号]
"""

# ─── 代码排错模板 ───

CODE_DEBUG_TEMPLATE = """
{system_constraints}

## 参考资料
{context}

## 错误信息
{query}

请分析错误原因并给出修复方案。
输出格式：
1. **错误根因**：定位到具体代码行和原因
2. **修复方案**：给出修改后的正确代码
3. **预防建议**：如何避免类似错误
4. **来源引用**：[来源: 文件名 | 函数名 | L行号]
"""


# ─── 模板工厂 ───

def build_prompt(
    query: str,
    context: str,
    mode: QueryMode = QueryMode.CODE_GEN,
) -> str:
    """
    根据模式构建完整 Prompt

    Args:
        query: 用户查询
        context: 检索到的上下文
        mode: 问答模式

    Returns:
        完整的 Prompt 字符串
    """
    base = SYSTEM_CONSTRAINTS.strip()

    if mode == QueryMode.CODE_GEN:
        return CODE_GEN_TEMPLATE.format(
            system_constraints=base,
            context=context if context else "（无参考资料，请告知用户）",
            query=query,
        )
    elif mode == QueryMode.CODE_EXPLAIN:
        return CODE_EXPLAIN_TEMPLATE.format(
            system_constraints=base,
            context=context if context else "（无参考资料，请告知用户）",
            query=query,
        )
    elif mode == QueryMode.CODE_DEBUG:
        return CODE_DEBUG_TEMPLATE.format(
            system_constraints=base,
            context=context if context else "（无参考资料，请告知用户）",
            query=query,
        )
    else:
        raise ValueError(f"未知的问答模式: {mode}")


def build_messages(query: str, context: str, mode: QueryMode) -> list[dict]:
    """
    构建标准的 messages 列表（用于 OpenAI 兼容 API）

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    system_prompt = f"""{SYSTEM_CONSTRAINTS.strip()}

## 问答模式
当前模式: {mode.value}

## 回答要求
- 严格遵守核心规则
- 代码必须完整可运行
- 必须标注来源引用
"""

    user_prompt = f"""## 参考资料
{context if context else "（无参考资料，请严格按照规则回答：根据现有资料无法解答此问题）"}

## 用户问题
{query}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def route_query(query: str, keyword_match_count: int) -> QueryMode:
    """
    问题路由 — 简单/复杂双模式

    Args:
        query: 用户查询
        keyword_match_count: BM25 关键词命中数

    Returns:
        推荐的 QueryMode
    """
    # 关键词特征识别
    gen_keywords = ["写", "生成", "实现", "编写", "创建", "开发", "写一个", "generate", "create", "implement"]
    debug_keywords = ["报错", "错误", "异常", "bug", "修复", "fix", "debug", "error", "traceback", "不工作"]
    explain_keywords = ["解释", "说明", "是什么", "做什么", "功能", "作用", "explain", "how does", "what is"]

    query_lower = query.lower()

    if any(kw in query_lower for kw in debug_keywords):
        return QueryMode.CODE_DEBUG
    elif any(kw in query_lower for kw in gen_keywords):
        return QueryMode.CODE_GEN
    elif any(kw in query_lower for kw in explain_keywords):
        return QueryMode.CODE_EXPLAIN
    else:
        # 默认：关键词命中少 → 可能是复杂的架构问题 → 代码解释模式（给更多上下文）
        return QueryMode.CODE_EXPLAIN if keyword_match_count < 3 else QueryMode.CODE_GEN
