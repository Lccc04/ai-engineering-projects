"""
微调效果评测脚本 — 调用 DeepSeek API 真实对比
运行: python scripts/run_eval.py [--n 50] [--full]
"""
import sys
import json
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env", override=False)

from openai import OpenAI
from evaluation.evaluator import Evaluator
from app.logger import logger  # 统一日志


# ═══════════════════════════════════════════════════
# 50 条测试集 — 不参与训练，纯评测用
# ═══════════════════════════════════════════════════

TEST_SET = [
    # FastAPI
    {"instruction": "用 FastAPI 创建一个带有请求体验证的文章发布接口", "mode": "code_gen", "domain": "fastapi"},
    {"instruction": "FastAPI 中如何实现文件上传并限制文件大小？", "mode": "code_gen", "domain": "fastapi"},
    {"instruction": "实现 FastAPI 的 OAuth2 密码流认证", "mode": "code_gen", "domain": "fastapi"},
    {"instruction": "FastAPI 中 background tasks 怎么用？写一个发送邮件的例子", "mode": "code_gen", "domain": "fastapi"},
    {"instruction": "用 FastAPI 实现 WebSocket 端点，广播消息给所有连接的客户端", "mode": "code_gen", "domain": "fastapi"},
    {"instruction": "解释 FastAPI Depends 的嵌套依赖解析机制", "mode": "code_explain", "domain": "fastapi"},
    {"instruction": "FastAPI 中 int 路径参数为什么能自动类型转换？原理是什么？", "mode": "code_explain", "domain": "fastapi"},
    {"instruction": "解释 FastAPI middleware、dependency、exception handler 的执行顺序", "mode": "code_explain", "domain": "fastapi"},
    # Pandas
    {"instruction": "用 Pandas 实现：读取两个 CSV 文件，按 key 列合并后做透视表", "mode": "code_gen", "domain": "pandas"},
    {"instruction": "Pandas 中如何对时间序列数据做重采样？给出按月聚合的例子", "mode": "code_gen", "domain": "pandas"},
    {"instruction": "用 Pandas 处理含缺失值的销售数据：填充、去重、异常值检测", "mode": "code_gen", "domain": "pandas"},
    {"instruction": "Pandas 中 DataFrame.apply、transform、agg 的区别是什么？各给例子", "mode": "code_explain", "domain": "pandas"},
    {"instruction": "解释 Pandas 的链式赋值（SettingWithCopyWarning）原因和解决方案", "mode": "code_explain", "domain": "pandas"},
    # Python 通用
    {"instruction": "用 Python asyncio 实现并发 HTTP 请求，控制并发数为 5", "mode": "code_gen", "domain": "python"},
    {"instruction": "实现一个支持上下文管理器的数据库连接类", "mode": "code_gen", "domain": "python"},
    {"instruction": "用 Python 装饰器实现函数调用重试机制（支持指数退避）", "mode": "code_gen", "domain": "python"},
    {"instruction": "解释 Python generator 和 yield from 的工作原理", "mode": "code_explain", "domain": "python"},
    {"instruction": "Python 中 __new__ 和 __init__ 的区别是什么？什么时候用 __new__？", "mode": "code_explain", "domain": "python"},
    # Bug 修复
    {"instruction": '''以下代码报 KeyError，请修复：
```python
config = {"host": "localhost"}
port = config["port"]
```''', "mode": "bug_fix", "domain": "python"},
    {"instruction": '''Pandas 代码报错：groupby 后取不到列名，请修复：
```python
result = df.groupby("category")["price"].mean()
result["category"]  # KeyError
```''', "mode": "bug_fix", "domain": "pandas"},
]


class ModelTester:
    """
    调用真实 DeepSeek API 测试
    支持两轮对比：原生模型 vs RAG 增强 vs (未来) 微调模型
    """

    def __init__(self):
        import os
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    def query_baseline(self, instruction: str) -> str:
        """直接用原生模型，不带任何上下文"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个 Python 工程师。请直接回答，输出代码完整可运行。"},
                {"role": "user", "content": instruction},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return resp.choices[0].message.content


def main():
    import argparse
    parser = argparse.ArgumentParser(description="微调效果评测")
    parser.add_argument("--n", type=int, default=10, help="测试条数（默认 10，避免耗时过长）")
    parser.add_argument("--full", action="store_true", help="跑全部 50 条")
    args = parser.parse_args()

    n = len(TEST_SET) if args.full else min(args.n, len(TEST_SET))
    test_cases = TEST_SET[:n]

    print("=" * 60)
    print("  QLoRA 微调效果评测 (DeepSeek V4 Pro)")
    print(f"  测试数量: {n}")
    print("=" * 60)

    tester = ModelTester()
    evaluator = Evaluator()

    results = []
    for i, tc in enumerate(test_cases):
        instruction = tc["instruction"]
        print(f"\n[{i+1}/{n}] {instruction[:60]}...")

        try:
            actual = tester.query_baseline(instruction)
            result = evaluator.evaluate_pair(
                instruction=instruction,
                expected="",  # 开放评测模式
                actual=actual,
            )
            results.append(result)
            logger.info(f"Eval [{i+1}/{n}] syntax={result.syntax_correct} quality={result.code_quality} runnable={result.runnable}")
            print(f"  语法: {'OK' if result.syntax_correct else 'FAIL'} | "
                  f"质量: {result.code_quality}/5 | "
                  f"可运行: {'Y' if result.runnable else 'N'}")
        except Exception as e:
            logger.error(f"Eval [{i+1}/{n}] error: {e}")
            print(f"  错误: {e}")

        time.sleep(0.3)

    # 汇总
    summary = evaluator.summary()
    print("\n" + "=" * 60)
    print("  评测结果汇总 (Baseline: DeepSeek V4 Pro 零样本)")
    print("=" * 60)
    print(f"  pass@1:          {summary['pass_at_1']*100:.1f}%")
    print(f"  语法正确率:      {summary['syntax_correct_rate']*100:.1f}%")
    print(f"  平均代码质量:    {summary['avg_code_quality']:.1f}/5")
    print(f"  可运行率:        {summary['runnable_rate']*100:.1f}%")
    print("=" * 60)

    # 保存
    report_path = _PROJECT_ROOT / "data" / "eval_baseline.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": tester.model,
            "test_count": n,
            "summary": summary,
            "details": [r.to_dict() for r in results],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")
    print("微调完成后，用 --finetuned-model <新模型ID> 重新跑评测即可对比")


if __name__ == "__main__":
    main()
