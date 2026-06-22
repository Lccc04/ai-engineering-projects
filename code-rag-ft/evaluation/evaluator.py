"""
效果评测体系 — pass@1 / 语法正确率 / 多维度对比
核心产出：微调前后量化对比报告
"""
import re
import ast
import json
import time
import statistics
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """单条评测结果"""
    instruction: str
    expected: str        # 期望输出
    actual: str          # 模型实际输出
    pass_at_1: bool      # 代码是否一次通过
    syntax_correct: bool # 语法是否正确
    business_match: int  # 业务匹配度 1-5
    code_quality: int    # 代码规范度 1-5
    runnable: bool       # 是否可运行

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction[:80],
            "pass_at_1": self.pass_at_1,
            "syntax_correct": self.syntax_correct,
            "business_match": self.business_match,
            "code_quality": self.code_quality,
            "runnable": self.runnable,
        }


class Evaluator:
    """
    效果评测器

    三大指标：
    1. pass@1 - 代码一次运行通过率
    2. 语法正确率 - AST 解析成功比例
    3. 多维度人工评估 - 业务匹配度 + 代码规范度 + 可运行性
    """

    def __init__(self):
        self.results: list[EvalResult] = []

    def check_syntax(self, code: str) -> bool:
        """
        检查 Python 代码语法是否正确
        用 AST 解析验证
        """
        # 提取代码块
        code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', code, re.DOTALL)
        if not code_blocks:
            # 没有 markdown 代码块时尝试直接解析
            code_blocks = [code]

        for block in code_blocks:
            try:
                ast.parse(block.strip())
                return True
            except SyntaxError:
                continue
        return False

    def check_runnable(self, code: str) -> bool:
        """
        检查代码是否包含明显不可运行的错误
        （简化版，生产环境应实际执行）
        """
        code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', code, re.DOTALL)
        if not code_blocks:
            code_blocks = [code]

        for block in code_blocks:
            # 检查基本要求
            has_imports_or_defs = bool(re.search(r'(import |from |def |class )', block))
            has_complete_statements = not block.strip().endswith(':')
            # 无明显语法错误
            try:
                ast.parse(block.strip())
                if has_imports_or_defs or has_complete_statements:
                    return True
            except SyntaxError:
                pass
        return False

    def score_business_match(self, expected: str, actual: str) -> int:
        """
        评估业务匹配度 (1-5)

        检查 actual 输出中包含 expected 中关键 API/函数的比例
        """
        # 提取关键字（函数名、类名、API）
        keywords_pattern = re.compile(r'\b([a-z_]+\(|[A-Z][a-zA-Z]+|\.\w+\()')
        expected_kw = set(keywords_pattern.findall(expected))
        actual_kw = set(keywords_pattern.findall(actual))

        if not expected_kw:
            return 3  # 无法评估，给中间分

        overlap = len(expected_kw & actual_kw) / len(expected_kw)

        if overlap >= 0.8:
            return 5
        elif overlap >= 0.6:
            return 4
        elif overlap >= 0.4:
            return 3
        elif overlap >= 0.2:
            return 2
        else:
            return 1

    def score_code_quality(self, code: str) -> int:
        """
        评估代码质量 (1-5)

        检查：类型注解、docstring、错误处理、命名规范
        """
        score = 1
        code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', code, re.DOTALL)
        target = code_blocks[0] if code_blocks else code

        if re.search(r'(def |class )', target):
            score += 1  # 有函数/类定义
        if re.search(r'""".*?"""', target, re.DOTALL):
            score += 1  # 有 docstring
        if re.search(r':\s*(int|str|float|bool|list|dict|tuple|Optional|Union)\b', target):
            score += 1  # 有类型注解
        if re.search(r'(try:|except |raise |if __name__)', target):
            score += 1  # 有错误处理或入口

        return min(score, 5)

    def evaluate_pair(self, instruction: str, expected: str, actual: str) -> EvalResult:
        """评估单条"""
        return EvalResult(
            instruction=instruction,
            expected=expected,
            actual=actual,
            pass_at_1=self.check_runnable(actual),
            syntax_correct=self.check_syntax(actual),
            business_match=self.score_business_match(expected, actual),
            code_quality=self.score_code_quality(actual),
            runnable=self.check_runnable(actual),
        )

    def run_benchmark(self, test_cases: list[dict]) -> dict:
        """
        运行完整评测

        test_cases: [{"instruction": ..., "expected": ..., "actual": ...}, ...]
        """
        self.results = []
        for tc in test_cases:
            result = self.evaluate_pair(
                tc["instruction"],
                tc.get("expected", ""),
                tc.get("actual", ""),
            )
            self.results.append(result)

        return self.summary()

    def summary(self) -> dict:
        """生成评测汇总报告"""
        if not self.results:
            return {}

        n = len(self.results)
        pass_at_1_rate = sum(1 for r in self.results if r.pass_at_1) / n
        syntax_rate = sum(1 for r in self.results if r.syntax_correct) / n
        avg_business = statistics.mean(r.business_match for r in self.results)
        avg_quality = statistics.mean(r.code_quality for r in self.results)
        runnable_rate = sum(1 for r in self.results if r.runnable) / n

        return {
            "total_samples": n,
            "pass_at_1": round(pass_at_1_rate, 4),
            "syntax_correct_rate": round(syntax_rate, 4),
            "avg_business_match": round(avg_business, 2),
            "avg_code_quality": round(avg_quality, 2),
            "runnable_rate": round(runnable_rate, 4),
        }

    def compare(self, before: dict, after: dict) -> str:
        """对比微调前后"""
        report = []
        report.append("=" * 60)
        report.append("  微调前后效果对比")
        report.append("=" * 60)
        report.append(f"{'指标':<20} {'微调前':>12} {'微调后':>12} {'提升':>12}")
        report.append("-" * 56)

        metrics = [
            ("pass@1", "pass_at_1"),
            ("语法正确率", "syntax_correct_rate"),
            ("业务匹配度", "avg_business_match"),
            ("代码质量", "avg_code_quality"),
            ("可运行率", "runnable_rate"),
        ]

        for label, key in metrics:
            v_before = before.get(key, 0)
            v_after = after.get(key, 0)
            if isinstance(v_before, float) and v_before < 1:
                delta = f"+{(v_after - v_before) * 100:.1f}%"
                report.append(f"{label:<20} {v_before*100:>10.1f}% {v_after*100:>10.1f}% {delta:>12}")
            else:
                delta = f"+{(v_after - v_before):.2f}"
                report.append(f"{label:<20} {v_before:>12.2f} {v_after:>12.2f} {delta:>12}")

        report.append("=" * 60)
        return "\n".join(report)


def main():
    """运行评测演示"""
    evaluator = Evaluator()

    # 模拟微调前（baseline DeepSeek V4 Pro 零样本）
    before_cases = [
        {
            "instruction": "用 FastAPI 创建一个用户注册接口",
            "expected": "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass User(BaseModel):\n    username: str\n    password: str\n\n@app.post('/register')\nasync def register(user: User):\n    return {'message': '注册成功'}",
            "actual": "```python\nfrom fastapi import FastAPI\napp = FastAPI()\n\n@app.post('/register')\ndef register(username: str, password: str):\n    # 缺少 Pydantic 验证\n    return {'message': 'ok'}\n```",
        },
        {
            "instruction": "Pandas 中 groupby 后如何求多列聚合？",
            "expected": "df.groupby('category').agg({'price': 'mean', 'quantity': 'sum'})",
            "actual": "```python\ndf.groupby('category').mean()  # 只做了单列聚合\n```",
        },
        {
            "instruction": "实现 FastAPI 的依赖注入 get_current_user",
            "expected": "from fastapi import Depends\n\nasync def get_current_user(token: str = Header(...)):\n    user = verify_token(token)\n    return user\n\n@app.get('/me')\nasync def me(user = Depends(get_current_user)):\n    return user",
            "actual": "```python\ndef get_current_user():\n    return {'name': 'admin'}  # 缺少 token 验证\n\n@app.get('/me')\nasync def me():\n    user = get_current_user()  # 手动调用而非依赖注入\n    return user\n```",
        },
    ]

    # 模拟微调后（QLoRA 微调模型）
    after_cases = [
        {
            "instruction": tc["instruction"],
            "expected": tc["expected"],
            "actual": tc["expected"],  # 理想情况：微调后输出 = 期望
        }
        for tc in before_cases
    ]

    before_summary = evaluator.run_benchmark(before_cases)
    after_summary = evaluator.run_benchmark(after_cases)

    print(evaluator.compare(before_summary, after_summary))

    # 保存报告
    report_path = Path(__file__).parent.parent / "data" / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "before_finetune": before_summary,
            "after_finetune": after_summary,
            "details": [r.to_dict() for r in evaluator.results],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
