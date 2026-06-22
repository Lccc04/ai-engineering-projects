"""
SQLite 持久化模块 — 保存会话、对话历史、工具调用日志
支持会话断点续接、多轮连续对话
"""
import sqlite3
import json
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field


DB_PATH = Path(__file__).parent.parent.parent / "data" / "agent.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接（自动建表）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_name TEXT DEFAULT 'default',
        created_at REAL,
        updated_at REAL,
        status TEXT DEFAULT 'active',  -- active / completed / failed
        metadata TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        role TEXT NOT NULL,            -- system / user / assistant / tool
        content TEXT,
        tool_calls TEXT,               -- JSON array
        tool_name TEXT,
        tool_result TEXT,
        created_at REAL,
        iteration INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS agent_traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(id),
        phase TEXT,                    -- plan / execute / verify
        content TEXT,
        tool_name TEXT,
        tool_args TEXT,
        tool_result TEXT,
        elapsed_ms REAL,
        success INTEGER,
        created_at REAL
    );

    CREATE TABLE IF NOT EXISTS tool_call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        arguments TEXT,
        result TEXT,
        success INTEGER,
        elapsed_ms REAL,
        error_type TEXT,
        retry_count INTEGER DEFAULT 0,
        created_at REAL
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);
    CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_traces_session ON agent_traces(session_id);
    CREATE INDEX IF NOT EXISTS idx_tool_logs_session ON tool_call_logs(session_id);
    """)


# ─── 操作接口 ───

class SessionStore:
    """会话持久化"""

    def __init__(self):
        self.db = get_db()

    def create(self, user_name: str = "default") -> str:
        sid = str(uuid.uuid4())[:12]
        now = time.time()
        self.db.execute(
            "INSERT INTO sessions (id, user_name, created_at, updated_at) VALUES (?,?,?,?)",
            (sid, user_name, now, now),
        )
        self.db.commit()
        return sid

    def update_status(self, sid: str, status: str):
        self.db.execute(
            "UPDATE sessions SET status=?, updated_at=? WHERE id=?",
            (status, time.time(), sid),
        )
        self.db.commit()

    def list_recent(self, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_message(self, sid: str, role: str, content: str = "",
                    tool_calls: list = None, tool_name: str = "",
                    tool_result: str = "", iteration: int = 0):
        self.db.execute(
            """INSERT INTO messages (session_id, role, content, tool_calls,
               tool_name, tool_result, created_at, iteration)
               VALUES (?,?,?,?,?,?,?,?)""",
            (sid, role, content,
             json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
             tool_name, tool_result, time.time(), iteration),
        )
        self.db.execute(
            "UPDATE sessions SET updated_at=? WHERE id=?",
            (time.time(), sid),
        )
        self.db.commit()

    def get_messages(self, sid: str, limit: int = 100) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
            (sid, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_trace(self, sid: str, phase: str, content: str = "",
                  tool_name: str = "", tool_args: str = "",
                  tool_result: str = "", elapsed_ms: float = 0,
                  success: bool = True):
        self.db.execute(
            """INSERT INTO agent_traces (session_id, phase, content, tool_name,
               tool_args, tool_result, elapsed_ms, success, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sid, phase, content[:2000], tool_name, tool_args,
             tool_result[:2000], elapsed_ms, int(success), time.time()),
        )
        self.db.commit()

    def get_traces(self, sid: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM agent_traces WHERE session_id=? ORDER BY id ASC",
            (sid,),
        ).fetchall()
        return [dict(r) for r in rows]

    def log_tool_call(self, sid: str, tool_name: str, arguments: str,
                      result: str, success: bool, elapsed_ms: float,
                      error_type: str = "", retry_count: int = 0):
        self.db.execute(
            """INSERT INTO tool_call_logs (session_id, tool_name, arguments,
               result, success, elapsed_ms, error_type, retry_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sid, tool_name, arguments[:1000], result[:2000],
             int(success), elapsed_ms, error_type, retry_count, time.time()),
        )
        self.db.commit()

    def get_tool_stats(self, sid: str = None) -> dict:
        """工具调用统计"""
        if sid:
            rows = self.db.execute(
                "SELECT tool_name, COUNT(*) as cnt, "
                "SUM(success) as ok, AVG(elapsed_ms) as avg_ms "
                "FROM tool_call_logs WHERE session_id=? "
                "GROUP BY tool_name", (sid,)
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT tool_name, COUNT(*) as cnt, "
                "SUM(success) as ok, AVG(elapsed_ms) as avg_ms "
                "FROM tool_call_logs GROUP BY tool_name"
            ).fetchall()
        return {
            r["tool_name"]: {
                "total": r["cnt"], "success": r["ok"],
                "fail": r["cnt"] - r["ok"],
                "avg_ms": round(r["avg_ms"] or 0, 1),
            }
            for r in rows
        }


# 全局单例
db_store = SessionStore()
