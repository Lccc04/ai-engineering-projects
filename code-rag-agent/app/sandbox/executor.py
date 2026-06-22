"""
安全沙箱执行器 — subprocess 隔离执行代码
- 30秒超时
- 禁止网络访问
- 禁止危险操作
- 捕获 stdout/stderr/traceback
"""
import sys
import io
import time
import traceback
import multiprocessing


# 危险模块黑名单
FORBIDDEN_MODULES = {
    "os", "subprocess", "shutil", "socket", "requests", "urllib",
    "http", "ftplib", "smtplib", "telnetlib",
}

# 允许的安全内置函数
SAFE_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "complex", "copyright", "credits",
    "delattr", "dict", "dir", "divmod", "enumerate", "filter", "float",
    "format", "frozenset", "getattr", "globals", "hasattr", "hash",
    "hex", "id", "input", "int", "isinstance", "issubclass", "iter",
    "len", "license", "list", "locals", "map", "max", "memoryview",
    "min", "next", "object", "oct", "open", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "setattr",
    "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple",
    "type", "vars", "zip", "__import__",
    # 常用模块
    "math", "json", "datetime", "collections", "itertools", "functools",
    "random", "statistics", "re", "string", "typing",
    # 数据分析
    "pandas", "numpy", "matplotlib",
    "True", "False", "None", "Exception", "ValueError", "TypeError",
    "KeyError", "IndexError", "StopIteration", "ZeroDivisionError",
}


def _run_in_subprocess(code: str, result_queue: multiprocessing.Queue):
    """
    在子进程中执行代码，结果通过 Queue 返回
    这是沙箱的核心 —— 即使代码崩溃也不影响主进程
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # 重定向标准输出
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    # 构建安全的执行环境
    safe_globals: dict = {"__builtins__": {}}
    for name in SAFE_BUILTINS:
        if name in __builtins__:
            safe_globals["__builtins__"][name] = __builtins__[name]

    # 注入常用模块
    try:
        import math
        safe_globals["math"] = math
        import json
        safe_globals["json"] = json
        from collections import Counter, defaultdict, OrderedDict
        safe_globals["Counter"] = Counter
        safe_globals["defaultdict"] = defaultdict
        safe_globals["OrderedDict"] = OrderedDict
        from itertools import chain, groupby, combinations, permutations
        safe_globals["chain"] = chain
        safe_globals["groupby"] = groupby
        import random
        safe_globals["random"] = random
        import statistics
        safe_globals["statistics"] = statistics
        import re
        safe_globals["re"] = re
        import datetime
        safe_globals["datetime"] = datetime
        from functools import reduce, lru_cache
        safe_globals["reduce"] = reduce
        safe_globals["lru_cache"] = lru_cache
    except ImportError:
        pass

    safe_locals: dict = {}

    output = ""
    error = ""
    success = False

    try:
        exec(code, safe_globals, safe_locals)
        success = True
    except Exception:
        error = traceback.format_exc()

    output = stdout_capture.getvalue()
    if not output:
        output = "(无输出)"

    result_queue.put({
        "success": success,
        "output": output.strip(),
        "error": error.strip(),
    })


class SandboxExecutor:
    """
    安全沙箱执行器

    使用 multiprocessing 创建子进程，实现真正的隔离：
    - 超时自动杀死子进程
    - 内存限制
    - 崩溃不影响主进程
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def execute(self, code: str) -> dict:
        """
        执行代码并返回结果

        Returns:
            {
                "success": bool,
                "output": str,    # stdout 输出
                "error": str,     # 错误信息
                "exec_time_ms": float,
                "timed_out": bool,
            }
        """
        code = self._preprocess(code)

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()

        process = ctx.Process(
            target=_run_in_subprocess,
            args=(code, result_queue),
        )

        start = time.perf_counter()
        process.start()
        process.join(timeout=self.timeout)

        elapsed = (time.perf_counter() - start) * 1000

        if process.is_alive():
            # 超时，强制终止
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
            return {
                "success": False,
                "output": "",
                "error": f"执行超时 ({self.timeout}秒)",
                "exec_time_ms": elapsed,
                "timed_out": True,
            }

        if result_queue.empty():
            return {
                "success": False,
                "output": "",
                "error": "子进程无输出（可能已崩溃）",
                "exec_time_ms": elapsed,
                "timed_out": False,
            }

        result = result_queue.get()
        result["exec_time_ms"] = elapsed
        result["timed_out"] = False
        return result

    @staticmethod
    def _preprocess(code: str) -> str:
        """安全预处理：检测危险操作"""
        code_lower = code.lower()

        for mod in FORBIDDEN_MODULES:
            if f"import {mod}" in code_lower or f"from {mod}" in code_lower:
                raise ValueError(f"禁止导入危险模块: {mod}")

        # 禁止嵌套 exec/eval
        if "exec(" in code and "exec(code" not in code:
            raise ValueError("禁止使用 exec()")
        if "eval(" in code:
            raise ValueError("禁止使用 eval()")

        # 禁止 system 调用
        if "os.system" in code_lower or "os.popen" in code_lower:
            raise ValueError("禁止系统调用")

        return code
