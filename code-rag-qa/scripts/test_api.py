"""
步骤 1 验证脚本 — 测试 DeepSeek API 三种能力
运行: python scripts/test_api.py
"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.generation.llm import llm_client


def test_code_generation():
    """测试 1: 代码生成"""
    print("=" * 60)
    print("测试 1/3: 代码生成")
    print("=" * 60)
    result = llm_client.generate_code("用 Python 实现一个带 LRU 缓存装饰器的函数")
    print(result)
    print()


def test_code_explanation():
    """测试 2: 代码解释"""
    print("=" * 60)
    print("测试 2/3: 代码解释")
    print("=" * 60)
    code = """
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""
    result = llm_client.explain_code(code)
    print(result)
    print()


def test_code_debugging():
    """测试 3: 代码排错"""
    print("=" * 60)
    print("测试 3/3: 代码排错")
    print("=" * 60)
    error = """
Traceback (most recent call last):
  File "main.py", line 5, in <module>
    result = add(5, "10")
TypeError: unsupported operand type(s) for +: 'int' and 'str'
"""
    result = llm_client.debug_code(error)
    print(result)
    print()


if __name__ == "__main__":
    print("\n*** DeepSeek API 能力测试 ***\n")
    try:
        test_code_generation()
        test_code_explanation()
        test_code_debugging()
        print("[OK] 全部测试通过! DeepSeek API 接入正常。")
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        print("请检查 .env 中的 DEEPSEEK_API_KEY 是否正确配置")
