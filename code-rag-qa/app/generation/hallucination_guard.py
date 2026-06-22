"""
幻觉校验 — 生成答案后反向检索验证
提取答案中的关键实体，匹配回原始上下文，评估 Faithfulness
"""
import re


class HallucinationGuard:
    """
    幻觉检测器

    三层防护:
    Layer 1 (Prompt): 系统约束「不知道就说不知道」
    Layer 2 (Compress): 上下文压缩去噪
    Layer 3 (Post-check): 生成后验证 ← 本模块

    校验逻辑:
    1. 从答案中提取关键实体（函数名、类名、API 名称、文件名）
    2. 在原始上下文中匹配这些实体的出现情况
    3. 计算匹配率 = 找到的实体数 / 总实体数
    4. 低于阈值 → 标记为可能幻觉
    """

    # 提取代码实体的正则
    # Python 标识符模式
    PY_IDENTIFIER = re.compile(r'\b([A-Z][a-zA-Z0-9_]*|[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)\b')

    # Markdown 代码块中的内容
    CODE_BLOCK = re.compile(r'```[\s\S]*?```')

    # 排除的常见词（非实体）
    STOP_WORDS = {
        "python", "def", "class", "import", "from", "return", "self", "cls",
        "the", "this", "that", "with", "for", "and", "not", "can", "you",
        "代码", "解释", "实现", "使用", "一个", "可以", "会", "需要", "没有",
        "根据", "现有", "资料", "无法", "解答", "print", "true", "false",
        "if", "else", "elif", "try", "except", "finally", "raise", "None",
        "str", "int", "list", "dict", "set", "tuple", "bool", "float",
    }

    def __init__(self, threshold: float = 0.6):
        """
        Args:
            threshold: 实体匹配率阈值，低于此值标记为可能幻觉
        """
        self.threshold = threshold

    def check(self, answer: str, contexts: list[str]) -> dict:
        """
        校验答案是否存在幻觉

        Args:
            answer: LLM 生成的答案
            contexts: 原始上下文 chunk 文本列表

        Returns:
            {
                "hallucination_risk": bool,    # 是否存在幻觉风险
                "match_rate": float,           # 实体匹配率
                "found_entities": list[str],   # 在上下文中找到的实体
                "missing_entities": list[str], # 未在上下文中找到的实体
                "verdict": str,                # 判断结论
            }
        """
        # Step 1: 提取答案中的实体
        answer_entities = self._extract_entities(answer)

        if not answer_entities:
            return {
                "hallucination_risk": False,
                "match_rate": 1.0,
                "found_entities": [],
                "missing_entities": [],
                "verdict": "答案中无可验证的代码实体",
            }

        # Step 2: 合并上下文
        full_context = " ".join(contexts).lower()

        # Step 3: 逐一匹配
        found = []
        missing = []
        for entity in answer_entities:
            if entity.lower() in full_context:
                found.append(entity)
            else:
                missing.append(entity)

        # Step 4: 计算匹配率
        match_rate = len(found) / len(answer_entities) if answer_entities else 1.0

        # Step 5: 判断
        if match_rate >= self.threshold:
            verdict = "✅ 答案关键实体与上下文匹配良好，幻觉风险低"
            risk = False
        elif match_rate >= 0.4:
            verdict = f"⚠️ 中等幻觉风险：{len(missing)}/{len(answer_entities)} 个实体未在上下文中找到"
            risk = True
        else:
            verdict = f"🚨 高幻觉风险：仅 {len(found)}/{len(answer_entities)} 个实体可溯源，建议忽略此答案"
            risk = True

        return {
            "hallucination_risk": risk,
            "match_rate": match_rate,
            "found_entities": found,
            "missing_entities": missing,
            "verdict": verdict,
        }

    def _extract_entities(self, text: str) -> list[str]:
        """从答案文本中提取代码实体"""
        # 移除代码块（避免把示例代码中的实体也算进去）
        clean_text = self.CODE_BLOCK.sub("", text)

        # 提取 Python 标识符
        matches = self.PY_IDENTIFIER.findall(clean_text)

        # 去重 + 过滤停用词
        seen = set()
        entities = []
        for m in matches:
            m_lower = m.lower()
            if m_lower not in self.STOP_WORDS and m_lower not in seen:
                seen.add(m_lower)
                entities.append(m)

        return entities
