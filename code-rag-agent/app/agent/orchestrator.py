"""
ReAct 编排引擎 v2 — Plan → Execute → Verify 三阶段循环

核心流程:
1. Plan:  LLM 拆解任务为有序子步骤
2. Execute: Function Calling 执行每个步骤
3. Verify: 校验执行结果，失败则重新 Plan → 最多3次
"""
import json
import time
from openai import OpenAI
from app.core.config import settings
from app.agent.memory import AgentMemory
from app.agent.retry import RetryHandler
from app.tools.python_runner import PythonRunnerTool
from app.tools.kb_search import KBSearchTool
from app.tools.file_manager import FileManagerTool
from app.core.database import db_store
from app.core.logger import log_tool_call, log_api_call, log_agent_phase, logger, agent_logger
from app.core.human_in_loop import HumanInTheLoop, RiskLevel


# ─── 三阶段 System Prompt ───

SYSTEM_PROMPT = """你是 ReAct 智能研发 Agent，基于 DeepSeek V4 Pro，采用 Plan→Execute→Verify 三阶段工作模式。

## 工作流程（严格遵守）
### Phase 1: Plan（规划）
- 分析用户需求，拆解为可执行的有序子步骤
- 每个子步骤明确：目标、所需工具、预期输出
- 规划完成后用中文告知用户计划

### Phase 2: Execute（执行）
- 按规划逐步执行，使用提供的工具完成每个子步骤
- 先检索知识库（kb_search）确认 API 用法，再编写代码（python_runner）
- 数据分析任务：读文件 → 清洗 → 计算 → 输出结论

### Phase 3: Verify（校验）
- 检查执行结果是否符合预期
- 代码是否运行成功、输出是否正确、是否遗漏步骤
- 不符合时回溯到 Plan 阶段重新规划（最多3次）

## 可用工具
- python_runner: 安全沙箱执行 Python 代码
- kb_search: 查询 FastAPI/Pandas 技术文档
- file_manager: 读写工作目录文件

## 约束
- 复杂任务必须先输出计划再执行
- 不确定的 API 用法必须先 kb_search
- 代码报错后分析原因→查知识库→修改→重新执行（最多3次）
- 高风险操作（覆盖文件、删除文件）前必须先说明理由
- 用中文回复用户
- 安全限制：沙箱禁止网络/系统调用，文件操作用限在工作目录，代码超时30秒
"""

PLAN_PROMPT = """## Phase 1: Plan（规划阶段）

请分析以下用户需求，拆解出有序的子步骤。每个步骤需标注：
- **目标**：这一步要完成什么
- **工具**：需要使用哪个工具
- **预期产出**：这一步完成后应该得到什么

用户需求：{query}

请用中文输出执行计划："""

VERIFY_PROMPT = """## Phase 3: Verify（校验阶段）

请检查以下执行结果是否符合预期：

**原始需求**：{query}

**执行计划**：
{plan}

**执行结果**：
{results}

请逐项检查：
1. 所有子步骤是否完成？
2. 代码是否执行成功？
3. 输出是否符合预期？
4. 是否需要重新执行？

如果一切正确，请回复 [PASS] 并给出最终答案。
如果有问题，请回复 [RETRY] 并说明需要修正的地方。"""


class ReActAgent:
    """ReAct Agent 编排器 v2 — Plan→Execute→Verify 三阶段"""

    def __init__(self, verbose: bool = True, sid: str = None):
        self.verbose = verbose
        self.client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        self.model = settings.model
        self.memory = AgentMemory()
        self.retry_handler = RetryHandler(max_retries=settings.max_retries)
        self.tools: dict = {}
        self._register_tools()
        self._trace: list[dict] = []  # 全链路执行轨迹
        self.sid = sid or db_store.create()  # 会话ID（持久化）
        agent_logger.info(f"Agent 初始化 sid={self.sid} model={self.model}")

    def _register_tools(self):
        _tools = [PythonRunnerTool(), KBSearchTool(), FileManagerTool()]
        self.tools = {t.name: t for t in _tools}

    def _build_tool_schemas(self) -> list[dict]:
        return [tool.to_openai_schema() for tool in self.tools.values()]

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            return f"[错误] 未知工具: {tool_name}"
        t0 = time.perf_counter()

        # 人机协同风险评估
        htl = HumanInTheLoop.assess(tool_name, arguments)

        if self.verbose:
            print(f"  [Tool] {tool_name}({json.dumps(arguments, ensure_ascii=False)[:200]})")

        success_flag = True
        try:
            result = tool.execute(**arguments)
        except Exception as e:
            result = f"[工具执行异常] {tool_name}: {e}"
            success_flag = False

        elapsed = (time.perf_counter() - t0) * 1000

        # 持久化工具调用日志
        db_store.log_tool_call(
            sid=self.sid, tool_name=tool_name,
            arguments=str(arguments)[:1000], result=result[:2000],
            success=success_flag and "[执行失败]" not in result,
            elapsed_ms=elapsed,
        )

        # 结构化日志
        log_tool_call(tool_name, str(arguments)[:100], result[:100], elapsed,
                      success_flag and "[执行失败]" not in result)

        self._trace.append({
            "phase": "execute",
            "tool": tool_name,
            "arguments": str(arguments)[:200],
            "result": result[:300],
            "elapsed_ms": elapsed,
            "success": "[执行失败]" not in result,
            "risk_level": htl.risk_level,
        })
        return result

    # ═══════════════════════════════════════════
    # Phase 1: Plan
    # ═══════════════════════════════════════════
    def _plan(self, query: str) -> str:
        """让 LLM 输出执行计划"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": PLAN_PROMPT.format(query=query)},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        plan = resp.choices[0].message.content or "直接执行用户需求"
        self._trace.append({"phase": "plan", "content": plan})
        if self.verbose:
            print(f"\n  [Plan] {plan[:300]}")
        return plan

    # ═══════════════════════════════════════════
    # Phase 2: Execute
    # ═══════════════════════════════════════════
    def _execute(self, query: str, plan: str) -> tuple[str, int]:
        """FC 循环执行工具调用"""
        self.memory = AgentMemory()
        self.memory.add_system(SYSTEM_PROMPT)
        self.memory.add_user(f"执行计划：\n{plan}\n\n用户需求：{query}\n\n请按计划逐步执行。")
        tool_schemas = self._build_tool_schemas()
        iterations = 0

        while iterations < settings.max_iterations:
            iterations += 1
            if self.verbose:
                print(f"\n  --- Execute 第 {iterations} 轮 ---")

            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.memory.messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    temperature=0.2,
                )
            except Exception as e:
                self.memory.add_assistant(content=f"LLM 调用失败: {e}")
                break

            msg = resp.choices[0].message

            if not msg.tool_calls:
                self.memory.add_assistant(content=msg.content or "完成")
                return msg.content or "完成", iterations

            self.memory.add_assistant(
                content=msg.content or "",
                tool_calls=[{
                    "id": tc.id,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                } for tc in msg.tool_calls],
            )

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = self._execute_tool(tc.function.name, args)
                self.memory.add_tool_result(tc.id, tc.function.name, result)

                if tc.function.name == "python_runner" and "[执行失败]" in result:
                    if self.retry_handler.should_retry():
                        analysis = self.retry_handler.analyze_error(result)
                        self.memory.add_retry(result, analysis["fix_suggestion"])
                        self.memory.messages.append({
                            "role": "user",
                            "content": f"代码执行失败: {analysis['fix_suggestion']}\n请先 kb_search 查找方案，修改后重新执行。",
                        })

            self.memory.trim()

        final = self.memory.messages[-1].get("content", "无回答") if self.memory.messages else "无回答"
        return final, iterations

    # ═══════════════════════════════════════════
    # Phase 3: Verify
    # ═══════════════════════════════════════════
    def _verify(self, query: str, plan: str, exec_result: str) -> tuple[bool, str]:
        """校验执行结果"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": VERIFY_PROMPT.format(
                    query=query, plan=plan, results=exec_result[:3000],
                )},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        verdict = resp.choices[0].message.content or "[PASS]"
        passed = "[PASS]" in verdict and "[RETRY]" not in verdict
        self._trace.append({"phase": "verify", "content": verdict, "passed": passed})
        if self.verbose:
            print(f"\n  [Verify] {'PASS' if passed else 'RETRY'}: {verdict[:200]}")
        return passed, verdict

    # ═══════════════════════════════════════════
    # 主循环: Plan → Execute → Verify
    # ═══════════════════════════════════════════
    def run(self, query: str) -> dict:
        self._trace = []
        self.retry_handler.reset()
        t_start = time.perf_counter()

        if self.verbose:
            print(f"\n{'='*50}\n  ReAct Agent v2 (Plan->Execute->Verify)\n  需求: {query[:100]}\n{'='*50}")

        # Phase 1: Plan
        plan = self._plan(query)

        # Phase 2+3: Execute → Verify 循环（最多3轮）
        final_answer = ""
        for attempt in range(1, settings.max_retries + 1):
            exec_result, iterations = self._execute(query, plan)
            passed, verdict = self._verify(query, plan, exec_result)

            if passed:
                final_answer = verdict.replace("[PASS]", "").strip()
                if not final_answer:
                    final_answer = exec_result
                break
            else:
                if self.verbose:
                    print(f"\n  [Loop] 第 {attempt} 轮验证未通过，重新执行...")
                plan = f"上一轮验证未通过：{verdict}\n\n修正计划并重新执行。原计划：{plan}"
        else:
            final_answer = exec_result if exec_result else "已达最大重试次数"

        total_ms = (time.perf_counter() - t_start) * 1000

        if self.verbose:
            print(f"\n  [Done] 耗时: {total_ms:.0f}ms, 追踪: {len(self._trace)} 条")

        return {
            "answer": final_answer,
            "plan": plan,
            "steps": self.memory.steps,
            "trace": self._trace,
            "stats": self.memory.get_stats(),
            "total_ms": total_ms,
        }

    def reset(self):
        self.memory = AgentMemory()
        self.retry_handler.reset()
        self._trace = []

    # ═══════════════════════════════════════════
    # 流式生成器模式 (for Gradio real-time UI)
    # ═══════════════════════════════════════════
    def run_stream(self, query: str):
        """
        流式执行 Agent — 每个事件 yield 给 Gradio UI

        Yield events:
            {"type": "phase", "phase": "plan"|"execute"|"verify"}
            {"type": "trace", "data": dict}
            {"type": "tool_start", "tool": str, "args": dict}
            {"type": "tool_result", "tool": str, "result": str, "success": bool, "elapsed_ms": float}
            {"type": "answer", "content": str}
            {"type": "stats", "iterations": int, "tool_calls": int, "retries": int, "elapsed_ms": float}
            {"type": "error", "message": str}
        """
        self._trace = []
        self.retry_handler.reset()
        t_start = time.perf_counter()

        # ── Phase 1: Plan ──
        yield {"type": "phase", "phase": "plan"}
        try:
            plan = self._plan(query)
            yield {"type": "trace", "data": {"phase": "plan", "content": plan[:300]}}
        except Exception as e:
            yield {"type": "error", "message": f"Plan 阶段失败: {e}"}
            return

        # ── Phase 2+3: Execute → Verify 循环 ──
        final_answer = ""
        for attempt in range(1, settings.max_retries + 1):
            yield {"type": "phase", "phase": "execute", "attempt": attempt}

            exec_result = ""
            iterations = 0
            self.memory = AgentMemory()
            self.memory.add_system(SYSTEM_PROMPT)
            self.memory.add_user(
                f"请按以下计划执行:\n{plan}\n\n用户需求:{query}"
            )
            tool_schemas = self._build_tool_schemas()
            tool_call_count = 0

            while iterations < settings.max_iterations:
                iterations += 1

                try:
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.memory.messages,
                        tools=tool_schemas,
                        tool_choice="auto",
                        temperature=0.2,
                    )
                except Exception as e:
                    yield {"type": "error", "message": f"LLM 调用失败: {e}"}
                    break

                msg = resp.choices[0].message

                if not msg.tool_calls:
                    self.memory.add_assistant(content=msg.content or "完成")
                    exec_result = msg.content or "完成"
                    break

                self.memory.add_assistant(
                    content=msg.content or "",
                    tool_calls=[{
                        "id": tc.id,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    } for tc in msg.tool_calls],
                )

                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    yield {
                        "type": "tool_start",
                        "tool": tc.function.name,
                        "args": args,
                    }

                    result = self._execute_tool(tc.function.name, args)
                    tool_call_count += 1
                    self.memory.add_tool_result(tc.id, tc.function.name, result)

                    yield {
                        "type": "tool_result",
                        "tool": tc.function.name,
                        "result": result,
                        "success": "[执行失败]" not in result,
                        "elapsed_ms": 0,  # filled by _execute_tool internals
                    }

                    if tc.function.name == "python_runner" and "[执行失败]" in result:
                        if self.retry_handler.should_retry():
                            analysis = self.retry_handler.analyze_error(result)
                            self.memory.add_retry(result, analysis["fix_suggestion"])
                            yield {
                                "type": "trace",
                                "data": {
                                    "phase": "retry",
                                    "error": analysis["error_type"],
                                    "suggestion": analysis["fix_suggestion"][:100],
                                },
                            }
                            self.memory.messages.append({
                                "role": "user",
                                "content": f"代码执行失败: {analysis['fix_suggestion']}\n请先 kb_search 查找方案，修改后重新执行。",
                            })

                self.memory.trim()

            # ── Phase 3: Verify ──
            yield {"type": "phase", "phase": "verify", "attempt": attempt}
            passed, verdict = self._verify(query, plan, exec_result)
            yield {"type": "trace", "data": {"phase": "verify", "content": verdict[:200], "passed": passed}}

            if passed:
                final_answer = verdict.replace("[PASS]", "").strip()
                if not final_answer:
                    final_answer = exec_result
                break
            else:
                plan = f"上一轮验证未通过:{verdict}\n\n修正计划并重新执行。原计划:{plan}"
        else:
            final_answer = exec_result if exec_result else "已达最大重试次数"

        total_ms = (time.perf_counter() - t_start) * 1000

        yield {
            "type": "answer",
            "content": final_answer,
        }
        yield {
            "type": "stats",
            "iterations": iterations,
            "tool_calls": tool_call_count,
            "retries": self.retry_handler.count,
            "elapsed_ms": total_ms,
        }


agent = ReActAgent()
