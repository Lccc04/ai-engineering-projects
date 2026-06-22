"""
ReAct Agent 测试脚本 — 测试工具调用和完整任务
运行: python scripts/test_agent.py
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def test_sandbox():
    """测试 1: 安全沙箱"""
    print("=" * 50)
    print("  测试 1: 安全沙箱执行")
    print("=" * 50)

    from app.sandbox.executor import SandboxExecutor

    sandbox = SandboxExecutor(timeout=10)

    # 正常代码
    result = sandbox.execute("print('hello world')\nprint(1+2+3)")
    assert result["success"], f"正常执行失败: {result}"
    assert "hello world" in result["output"]
    print(f"  [OK] 正常执行: {result['output'][:50]}")

    # 错误代码
    result = sandbox.execute("1/0")
    assert not result["success"]
    assert "ZeroDivisionError" in result["error"]
    print(f"  [OK] 错误捕获: {result['error'][:50]}")

    # 禁止 import os
    try:
        sandbox.execute("import os\nos.system('dir')")
        print("  [FAIL] 应拦截危险模块")
    except ValueError as e:
        print(f"  [OK] 危险模块拦截: {e}")

    print()


def test_python_runner_tool():
    """测试 2: python_runner 工具"""
    print("=" * 50)
    print("  测试 2: python_runner 工具")
    print("=" * 50)

    from app.tools.python_runner import PythonRunnerTool

    tool = PythonRunnerTool()

    result = tool.execute(code="print(sum(range(100)))")
    assert "4950" in result
    print(f"  [OK] 工具执行: {result}")


def test_file_manager_tool():
    """测试 3: file_manager 工具"""
    print("=" * 50)
    print("  测试 3: file_manager 工具")
    print("=" * 50)

    from app.tools.file_manager import FileManagerTool

    tool = FileManagerTool()

    # 保存
    result = tool.execute(action="save", path="test.txt", content="hello agent")
    assert "已保存" in result
    print(f"  [OK] {result}")

    # 读取
    result = tool.execute(action="read", path="test.txt")
    assert "hello agent" in result
    print(f"  [OK] 读取成功")

    # 列表
    result = tool.execute(action="list")
    print(f"  [OK] {result}")


def test_agent_workflow():
    """测试 4: Agent 完整流程（需要 API）"""
    print("=" * 50)
    print("  测试 4: Agent 完整流程")
    print("=" * 50)

    try:
        from app.agent.orchestrator import ReActAgent

        agent = ReActAgent(verbose=True)
        result = agent.run("用 Python 写一个函数计算 1 到 100 的和，打印结果")

        assert result["answer"], "Agent 未返回答案"
        print(f"\n  [OK] Agent 完成: {result['answer'][:200]}")
        print(f"  [OK] 迭代次数: {result['iterations']}")
        print(f"  [OK] 工具调用: {result['stats']['total_tool_calls']}")
    except Exception as e:
        print(f"  [FAIL] {e}")


if __name__ == "__main__":
    print("\n*** ReAct Agent 测试 ***\n")

    test_sandbox()
    test_python_runner_tool()
    test_file_manager_tool()

    print("\n[OK] 核心模块测试全部通过!\n")

    # 最后测 Agent（需要 API）
    import os
    if os.getenv("DEEPSEEK_API_KEY"):
        test_agent_workflow()
    else:
        print("跳过 Agent 测试：未配置 DEEPSEEK_API_KEY")
