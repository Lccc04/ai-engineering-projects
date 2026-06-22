"""
Alpaca 格式数据模型 + 校验规则
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class AlpacaItem(BaseModel):
    """
    Alpaca 格式单条数据

    instruction: 任务指令（必填）
    input: 具体输入（可为空）
    output: 期望输出（必填）
    task_type: 任务分类（代码生成/解释/修复/测试）
    source: 数据来源（codealpaca / manual / rlhf）
    """
    instruction: str = Field(..., min_length=5, max_length=5000)
    input: str = Field(default="", max_length=10000)
    output: str = Field(..., min_length=5, max_length=10000)
    task_type: str = Field(default="code_gen")
    source: str = Field(default="manual")

    @field_validator("instruction")
    @classmethod
    def check_instruction(cls, v: str) -> str:
        """确保 instruction 以明确的任务描述开头"""
        bad_prefixes = ("当然", "好的", "让我", "首先")
        for p in bad_prefixes:
            if v.startswith(p):
                raise ValueError(f"instruction 不应以 '{p}' 开头，需要是明确的任务指令")
        return v.strip()

    @field_validator("task_type")
    @classmethod
    def check_task_type(cls, v: str) -> str:
        allowed = {"code_gen", "code_explain", "bug_fix", "test_gen"}
        if v not in allowed:
            raise ValueError(f"task_type 必须为 {allowed} 之一")
        return v

    @field_validator("source")
    @classmethod
    def check_source(cls, v: str) -> str:
        allowed = {"codealpaca", "manual", "rlhf"}
        if v not in allowed:
            raise ValueError(f"source 必须为 {allowed} 之一")
        return v

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
            "task_type": self.task_type,
            "source": self.source,
        }

    def to_training_format(self) -> str:
        """
        转换为 DeepSeek 平台微调格式
        """
        if self.input:
            user_content = f"{self.instruction}\n\n输入:\n{self.input}"
        else:
            user_content = self.instruction

        return user_content

    def to_huggingface_format(self) -> dict:
        """
        转换为 HuggingFace 标准训练格式
        """
        return {
            "messages": [
                {"role": "system", "content": "你是一个资深 Python 工程师。"},
                {"role": "user", "content": self.to_training_format()},
                {"role": "assistant", "content": self.output},
            ]
        }
