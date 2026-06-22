"""
错误重试机制 — 代码执行失败后自动修复
最多重试 3 次，每次重试前分析错误信息
"""
import re


class RetryHandler:
    """
    代码执行错误重试处理器

    策略：
    1. 解析错误信息（类型、行号、消息）
    2. 构造修复提示回传 LLM
    3. 最多重试 3 次
    """

    MAX_RETRIES = 3

    # 常见错误模式的快速修复提示
    ERROR_HINTS = {
        "NameError": "变量未定义，检查是否拼写错误或缺少 import",
        "TypeError": "类型不匹配，检查参数类型和操作符使用",
        "ValueError": "值错误，检查数据格式和转换逻辑",
        "KeyError": "键不存在，使用 .get() 或检查字典键名",
        "IndexError": "索引越界，检查列表长度和索引范围",
        "AttributeError": "属性不存在，检查对象类型和方法名",
        "ImportError": "模块导入失败，确认模块名正确或已安装",
        "ModuleNotFoundError": "模块未找到，确认安装或使用内置替代",
        "FileNotFoundError": "文件未找到，检查路径和文件名",
        "ZeroDivisionError": "除零错误，添加分母检查",
        "SyntaxError": "语法错误，检查括号匹配、缩进和冒号",
    }

    def __init__(self, max_retries: int = 3):
        self.max_retries = min(max_retries, self.MAX_RETRIES)
        self.retry_count = 0
        self.error_history: list[dict] = []

    def should_retry(self) -> bool:
        """是否应该重试"""
        return self.retry_count < self.max_retries

    def analyze_error(self, error_output: str) -> dict:
        """
        分析错误并生成修复建议

        Returns:
            {"error_type": str, "hint": str, "fix_suggestion": str}
        """
        self.retry_count += 1

        # 提取错误类型
        error_type = "Unknown"
        for known_type in self.ERROR_HINTS:
            if known_type in error_output:
                error_type = known_type
                break

        hint = self.ERROR_HINTS.get(error_type, "请检查代码逻辑")

        # 提取错误行号
        line_match = re.search(r'line (\d+)', error_output, re.IGNORECASE)
        line_info = f"第 {line_match.group(1)} 行" if line_match else "代码中"

        result = {
            "retry_count": self.retry_count,
            "error_type": error_type,
            "error_line": line_info,
            "hint": hint,
            "fix_suggestion": (
                f"第 {self.retry_count} 次重试。上次代码在{line_info}出现 {error_type}。"
                f"{hint}。请修改代码后重新执行。"
            ),
        }

        self.error_history.append(result)
        return result

    def reset(self):
        """重置重试计数"""
        self.retry_count = 0
        self.error_history = []

    def get_history(self) -> list[dict]:
        return self.error_history
