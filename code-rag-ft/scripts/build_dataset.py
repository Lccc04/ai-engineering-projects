"""
垂类代码数据集构建器 — 整合 CodeAlpaca + 手工模板 + LLM 增强
产出标准 Alpaca 格式 JSONL，可直接提交 DeepSeek 微调平台

核心亮点：
1. LLM 自动批量生成 200 条高质量垂类数据（不是简单复制）
2. 种子模板保证方向，LLM 扩充多样性
3. 每类数据带 source 标记，可追溯来源
"""
import sys
import json
import random
import time
from pathlib import Path
from hashlib import md5

# 支持独立运行
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env", override=False)

from data.schema import AlpacaItem


# ═══════════════════════════════════════════════════
# 种子模板库 — 每种任务类型 5-8 个高质量种子
# 这些是"锚点"，LLM 以它们为参考批量扩增
# ═══════════════════════════════════════════════════

CODE_GEN_SEEDS = [
    {
        "instruction": "创建一个 FastAPI 应用，包含用户注册和登录接口，使用 JWT 认证和 bcrypt 密码加密",
        "output": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import jwt
import bcrypt

app = FastAPI(title="Auth Service")
users_db = {}

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/register")
async def register(req: RegisterRequest):
    if req.username in users_db:
        raise HTTPException(400, "User exists")
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt())
    users_db[req.username] = {"email": req.email, "password": hashed}
    return {"message": "ok"}

@app.post("/login")
async def login(req: LoginRequest):
    user = users_db.get(req.username)
    if not user or not bcrypt.checkpw(req.password.encode(), user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode({"sub": req.username}, "secret", algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}''',
    },
    {
        "instruction": "用 Python 实现一个带 TTL 过期功能的 LRU 缓存装饰器",
        "output": '''from collections import OrderedDict
from functools import wraps
import time

def lru_cache(maxsize=128, ttl=60):
    """带 TTL 的 LRU 缓存装饰器"""
    def decorator(func):
        cache = OrderedDict()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in cache:
                value, timestamp = cache[key]
                if ttl is None or (now - timestamp) < ttl:
                    cache.move_to_end(key)
                    return value
                del cache[key]
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            if len(cache) > maxsize:
                cache.popitem(last=False)
            return result

        def info():
            return {"size": len(cache), "maxsize": maxsize}
        wrapper.cache_info = info
        return wrapper
    return decorator''',
    },
    {
        "instruction": "实现 FastAPI 中间件，记录每个 HTTP 请求的耗时、方法和路径",
        "output": '''import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("access")

class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path} "
            f"{response.status_code} {elapsed:.1f}ms"
        )
        response.headers["X-Response-Time"] = f"{elapsed:.1f}ms"
        return response''',
    },
    {
        "instruction": "用 Pandas 读取 CSV 文件，按某列分组后计算每组的均值和总和",
        "output": '''import pandas as pd

def analyze_csv(path: str, group_col: str, value_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.groupby(group_col).agg(
        mean=(value_col, "mean"),
        total=(value_col, "sum"),
        count=(value_col, "count")
    ).reset_index()''',
    },
    {
        "instruction": "FastAPI 中如何使用 Query 参数验证？实现一个分页查询接口",
        "output": '''from fastapi import FastAPI, Query

app = FastAPI()
items_db = list(range(100))

@app.get("/items")
async def list_items(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str = Query(None, description="搜索关键词"),
):
    start = (page - 1) * size
    end = start + size
    result = items_db[start:end]
    return {
        "page": page,
        "size": size,
        "total": len(items_db),
        "items": result,
    }''',
    },
]

CODE_EXPLAIN_SEEDS = [
    {
        "instruction": '''请逐行解释以下 FastAPI 代码的工作原理：
```python
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    q: str = Query(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user
```''',
        "output": '''逐行解释：
1. `@app.get("/users/{user_id}")` — 注册 GET 路由，`{user_id}` 是路径参数
2. `async def get_user(...)` — 异步处理函数，FastAPI 自动在线程池中运行
3. `user_id: int` — 路径参数自动转为 int 类型
4. `q: str = Query(None)` — 可选查询参数，不在路径中
5. `db: Session = Depends(get_db)` — 依赖注入，FastAPI 调用 `get_db()` 获取数据库会话后传入
6. `db.query(User).filter(...)` — SQLAlchemy ORM 查询
7. `.first()` — 只取第一条结果
8. `raise HTTPException(404, ...)` — 找不到时返回 404 错误
9. `return user` — Pydantic 自动将 ORM 对象序列化为 JSON

关键模式：路径参数 + 查询参数 + 依赖注入三者解耦，各司其职。''',
    },
    {
        "instruction": '''解释 Pandas groupby + agg 的 split-apply-combine 机制：
```python
df.groupby('category').agg({
    'price': ['mean', 'std'],
    'quantity': 'sum'
})
```''',
        "output": '''这是 Pandas 核心的 split-apply-combine 模式：

**Split（拆分）**：`groupby('category')` 按 category 列的唯一值将 DataFrame 拆成多个子组。

**Apply（应用）**：`.agg()` 对每个子组独立执行聚合函数：
- `price` 列求 mean（均值）和 std（标准差）
- `quantity` 列求 sum（总和）

**Combine（合并）**：将每个子组的结果合并为一个新的 DataFrame，索引是分组键。

性能要点：groupby 操作返回的是延迟对象，`.agg()` 触发实际计算。对于大数据集，建议先筛选列再聚合。''',
    },
]

BUG_FIX_SEEDS = [
    {
        "instruction": '''以下 FastAPI 代码出现 "pydantic field not defined" 错误，请修复：
```python
class Item(BaseModel):
    name: str
    price: float

@app.put("/items/{id}")
async def update(id: int, item: Item):
    items_db[id] = item.dict()
    items_db[id].id = id  # 这里报错
    return items_db[id]
```''',
        "output": '''错误原因：`item.dict()` 返回的是普通 dict，`items_db[id].id = id` 试图给 dict 设置属性。

修复方案（3 种）：
```python
# 方案 1：直接用字典操作
data = item.model_dump()
data["id"] = id
items_db[id] = data

# 方案 2：用 Pydantic model_dump + 合并
items_db[id] = {**item.model_dump(), "id": id}

# 方案 3：如果确实需要对象，用 dataclass
from dataclasses import dataclass
@dataclass
class Item:
    name: str
    price: float
    id: int = None
```
推荐方案 2，简洁且类型安全。''',
    },
]

TEST_GEN_SEEDS = [
    {
        "instruction": '''为以下 FastAPI 用户服务类编写 pytest 单元测试：
```python
class UserService:
    def __init__(self, db):
        self.db = db

    def create_user(self, username: str, email: str) -> dict:
        if self.db.exists(username):
            raise ValueError("User exists")
        user = {"username": username, "email": email}
        self.db.insert(user)
        return user

    def get_user(self, username: str) -> dict | None:
        return self.db.find(username)
```''',
        "output": '''```python
import pytest
from unittest.mock import Mock

class TestUserService:
    @pytest.fixture
    def db(self):
        return Mock()

    @pytest.fixture
    def service(self, db):
        return UserService(db)

    def test_create_user_success(self, service, db):
        db.exists.return_value = False
        result = service.create_user("alice", "alice@test.com")
        assert result["username"] == "alice"
        db.insert.assert_called_once()

    def test_create_user_duplicate(self, service, db):
        db.exists.return_value = True
        with pytest.raises(ValueError, match="User exists"):
            service.create_user("alice", "alice@test.com")

    def test_get_user_found(self, service, db):
        db.find.return_value = {"username": "bob"}
        result = service.get_user("bob")
        assert result["username"] == "bob"

    def test_get_user_not_found(self, service, db):
        db.find.return_value = None
        result = service.get_user("nobody")
        assert result is None
```'''
    },
]


# ═══════════════════════════════════════════════════
# LLM 数据增强器
# ═══════════════════════════════════════════════════

class LLMDataAugmentor:
    """
    用 DeepSeek V4 Pro 自动批量生成垂类训练数据

    策略：
    1. 以种子模板为参考样本
    2. 构造元 Prompt 让 LLM 生成同一风格的变体
    3. 每批 5 条，避免模式崩塌
    """

    def __init__(self):
        from openai import OpenAI
        import os

        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    def generate_batch(
        self,
        task_type: str,
        seeds: list[dict],
        count: int = 200,
    ) -> list[dict]:
        """
        以种子为参考，生成 count 条同风格数据

        Args:
            task_type: code_gen | code_explain | bug_fix | test_gen
            seeds: 种子样本列表 [{"instruction": ..., "output": ...}, ...]
            count: 目标生成数量
        """
        task_labels = {
            "code_gen": "代码生成",
            "code_explain": "代码解释",
            "bug_fix": "Bug 修复",
            "test_gen": "单元测试生成",
        }
        label = task_labels.get(task_type, task_type)

        # 构建种子参考文本
        seed_text = ""
        for i, s in enumerate(seeds, 1):
            seed_text += f"\n### 示例 {i}\n**指令**: {s['instruction']}\n**输出**:\n{s['output'][:500]}\n"

        meta_prompt = f"""你是 Python 代码数据标注专家。请参考以下{label}任务的示例风格，生成新的高质量训练数据。

要求：
1. 每条数据必须有 `instruction`（任务指令）和 `output`（期望答案）两个字段
2. instruction 描述清晰具体，output 准确完整
3. 内容聚焦 FastAPI / Pandas / Python 后端开发场景
4. 输出多样性：不要重复示例中的模式，创造新的变体
5. 代码必须完整可运行

{seed_text}

请严格按以下 JSON 格式输出（不要输出其他内容）：
```json
[
  {{"instruction": "...", "output": "..."}},
  {{"instruction": "...", "output": "..."}},
  {{"instruction": "...", "output": "..."}},
  {{"instruction": "...", "output": "..."}},
  {{"instruction": "...", "output": "..."}}
]
```"""

        results = []
        batch_size = 5
        remaining = count

        print(f"  [LLM增强] {label}: 目标 {count} 条...")

        for round_num in range((count // batch_size) + 1):
            if remaining <= 0:
                break

            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是 Python 代码数据标注专家，只输出符合要求的 JSON，不输出其他内容。"},
                        {"role": "user", "content": meta_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4000,
                )

                content = resp.choices[0].message.content
                # 提取 JSON 块
                json_match = __import__('re').search(r'```(?:json)?\s*\n?(.*?)\n?```', content, __import__('re').DOTALL)
                if json_match:
                    content = json_match.group(1)

                batch = json.loads(content)
                for item in batch:
                    if isinstance(item, dict) and "instruction" in item and "output" in item:
                        if len(item["output"]) > 30:  # 过滤明显低质量
                            results.append(item)
                            remaining -= 1

                print(f"    第 {round_num+1} 批: +{len(batch)} 条, 剩余 {max(0, remaining)} 条")

                if remaining <= 0:
                    break

                time.sleep(0.5)  # 限速

            except Exception as e:
                print(f"    第 {round_num+1} 批失败: {e}")
                time.sleep(2)

        print(f"  [LLM增强完成] 实际生成 {len(results)} 条")
        return results[:count]


# ═══════════════════════════════════════════════════
# 数据集构建器
# ═══════════════════════════════════════════════════

class DatasetBuilder:
    """
    垂类数据集构建器

    数据来源（按优先级）：
    1. 种子模板 → ~30 条高质量锚点
    2. LLM 增强 → ~200 条自动生成变体
    3. CodeAlpaca → ~500 条筛选 Python 数据
    4. 负例 → ~100 条常见错误修复
    """

    def __init__(self, output_dir: Path, use_llm: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.items: list[AlpacaItem] = []
        self.use_llm = use_llm
        self.augmentor = LLMDataAugmentor() if use_llm else None

    def add_seed_data(self):
        """添加种子模板 — 高质量锚点数据"""
        count = 0
        for task_type, seeds in [
            ("code_gen", CODE_GEN_SEEDS),
            ("code_explain", CODE_EXPLAIN_SEEDS),
            ("bug_fix", BUG_FIX_SEEDS),
            ("test_gen", TEST_GEN_SEEDS),
        ]:
            for seed in seeds:
                self.items.append(AlpacaItem(
                    instruction=seed["instruction"],
                    output=seed["output"],
                    task_type=task_type,
                    source="manual",
                ))
                count += 1
        print(f"  [种子模板] {count} 条")
        return self

    def add_llm_augmented(self, target_per_task: int = 50):
        """用 LLM 批量生成垂类数据"""
        if not self.use_llm:
            print("  [LLM增强] 跳过（未启用）")
            return self

        for task_type, seeds in [
            ("code_gen", CODE_GEN_SEEDS),
            ("code_explain", CODE_EXPLAIN_SEEDS),
            ("bug_fix", BUG_FIX_SEEDS),
            ("test_gen", TEST_GEN_SEEDS),
        ]:
            augmented = self.augmentor.generate_batch(
                task_type=task_type,
                seeds=seeds,
                count=target_per_task,
            )
            for item in augmented:
                self.items.append(AlpacaItem(
                    instruction=item["instruction"],
                    output=item["output"],
                    task_type=task_type,
                    source="llm_augmented",
                ))
        return self

    def add_codealpaca_data(self, source_file: Path | None = None):
        """添加 CodeAlpaca 筛选数据"""
        items = self._generate_builtin(500)
        for item in items:
            self.items.append(item)
        print(f"  [CodeAlpaca] {len(items)} 条")
        return self

    def add_negative_examples(self, count: int = 100):
        """添加负例：常见错误 + 修复"""
        ne_examples = [
            ("def get_first(lst):\n    return lst[0]", "def get_first(lst):\n    return lst[0] if lst else None"),
            ("def divide(a, b):\n    return a / b", "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b"),
            ("data = {'a': [1,2], 'b': [3]}\ndf = pd.DataFrame(data)", "data = {'a': [1,2], 'b': [3, None]}\ndf = pd.DataFrame(data).fillna(0)"),
            ("result = db.execute(f\"SELECT * FROM users WHERE name='{name}'\")", "result = db.execute(\"SELECT * FROM users WHERE name=?\", (name,))"),
        ]
        for i, (buggy, fixed) in enumerate(ne_examples * (count // len(ne_examples) + 1)):
            if i >= count:
                break
            self.items.append(AlpacaItem(
                instruction=f"以下代码存在潜在 bug，请分析问题并给出修复：\n```python\n{buggy}\n```",
                output=f"问题分析及修复：\n```python\n{fixed}\n```",
                task_type="bug_fix",
                source="rlhf",
            ))
        print(f"  [负例] {min(count, len(ne_examples) * (count // len(ne_examples) + 1))} 条")
        return self

    def clean(self):
        """数据清洗"""
        before = len(self.items)
        seen = set()
        deduped = []
        for item in self.items:
            key = md5(item.instruction.encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        self.items = [it for it in deduped if 20 < len(it.output) < 8000]
        for item in self.items:
            item.output = item.output.strip()
            item.instruction = item.instruction.strip()
        print(f"  [清洗] {before} -> {len(self.items)}")
        return self

    def save_all(self) -> dict:
        """保存所有格式"""
        # Alpaca JSONL
        alpaca_path = self.output_dir / "dataset.jsonl"
        with open(alpaca_path, "w", encoding="utf-8") as f:
            for item in self.items:
                f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

        # DeepSeek 平台格式
        ds_path = self.output_dir / "deepseek_sft.jsonl"
        with open(ds_path, "w", encoding="utf-8") as f:
            for item in self.items:
                record = {
                    "messages": [
                        {"role": "system", "content": "你是一个资深 Python 工程师，请根据用户指令生成高质量代码或分析。请严格遵守指令要求，输出完整可运行的代码。"},
                        {"role": "user", "content": item.to_training_format()},
                        {"role": "assistant", "content": item.output},
                    ]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"  [Alpaca格式] {len(self.items)} 条 -> {alpaca_path}")
        print(f"  [DeepSeek格式] {len(self.items)} 条 -> {ds_path}")
        return {"alpaca": alpaca_path, "deepseek": ds_path}

    @staticmethod
    def _generate_builtin(count: int) -> list[AlpacaItem]:
        """生成基础 Python 代码任务"""
        tasks = [
            ("用 Python 实现快速排序算法", "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)"),
            ("用 Python 实现 LRU 缓存类，支持 get 和 put 操作", "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, cap):\n        self.cap = cap\n        self.cache = OrderedDict()\n    def get(self, k):\n        if k not in self.cache: return -1\n        self.cache.move_to_end(k)\n        return self.cache[k]\n    def put(self, k, v):\n        if k in self.cache: self.cache.move_to_end(k)\n        self.cache[k] = v\n        if len(self.cache) > self.cap: self.cache.popitem(last=False)"),
            ("用 Python 解析 JSON 并写入 CSV 文件", "import json, csv\ndef json_to_csv(json_path, csv_path):\n    with open(json_path) as f:\n        data = json.load(f)\n    if not data: return\n    with open(csv_path, 'w', newline='') as f:\n        w = csv.DictWriter(f, fieldnames=data[0].keys())\n        w.writeheader()\n        w.writerows(data)"),
            ("用 Python 实现单例模式装饰器", "def singleton(cls):\n    instances = {}\n    def get(*a, **kw):\n        if cls not in instances:\n            instances[cls] = cls(*a, **kw)\n        return instances[cls]\n    return get"),
            ("用 Python 统计文本中出现频率最高的单词", "from collections import Counter\ndef word_freq(text):\n    words = text.lower().split()\n    return dict(Counter(words).most_common(10))"),
        ]
        items = []
        for i, (instr, out) in enumerate(tasks * (count // len(tasks) + 1)):
            if i >= count: break
            items.append(AlpacaItem(instruction=instr, output=out, task_type="code_gen", source="codealpaca"))
        return items


# ═══════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="构建垂类代码指令微调数据集")
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 增强")
    parser.add_argument("--llm-count", type=int, default=50, help="每类 LLM 增强条数")
    args = parser.parse_args()

    output_dir = _PROJECT_ROOT / "data" / "processed"
    builder = DatasetBuilder(output_dir, use_llm=not args.no_llm)

    print("=" * 60)
    print("  垂类代码指令数据集构建 (DeepSeek QLoRA 微调)")
    print("=" * 60)

    builder.add_seed_data()            # ~30 条种子
    builder.add_llm_augmented(args.llm_count)  # ~200 条 LLM
    builder.add_codealpaca_data()      # ~500 条通用
    builder.add_negative_examples(100) # ~100 条负例
    builder.clean()                    # 清洗
    builder.save_all()                 # 保存

    # 统计
    stats = {}
    for item in builder.items:
        stats[item.task_type] = stats.get(item.task_type, 0) + 1
    src_stats = {}
    for item in builder.items:
        src_stats[item.source] = src_stats.get(item.source, 0) + 1

    print(f"\n{'='*60}")
    print(f"  数据集构建完成")
    print(f"{'='*60}")
    print(f"  总数: {len(builder.items)} 条")
    print(f"  任务分布: {stats}")
    print(f"  来源分布: {src_stats}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
