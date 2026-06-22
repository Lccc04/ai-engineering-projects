"""
DeepSeek API 客户端 — OpenAI 兼容模式
支持代码生成、解释、排错三种场景
"""
from openai import OpenAI
from app.core.config import settings


class DeepSeekClient:
    """DeepSeek V4 Pro 客户端封装（OpenAI 兼容接口）"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
        self.model = settings.model

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        """
        通用对话接口

        Args:
            messages: [{"role": "system/user/assistant", "content": "..."}]
            temperature: 采样温度，默认用全局配置
            max_tokens: 最大输出 token
            stream: 是否流式输出

        Returns:
            模型回复文本
        """
        if temperature is None:
            temperature = settings.temperature

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        if stream:
            # 流式输出 — 返回生成器
            return self._stream_response(response)
        else:
            return response.choices[0].message.content

    def _stream_response(self, response):
        """流式输出生成器"""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def generate_code(self, prompt: str, context: str = "") -> str:
        """代码生成"""
        messages = [
            {"role": "system", "content": "你是一个资深 Python 工程师，擅长编写高质量、可运行的代码。"},
            {"role": "user", "content": f"上下文资料:\n{context}\n\n需求:\n{prompt}"},
        ]
        return self.chat(messages)

    def explain_code(self, code: str, context: str = "") -> str:
        """代码解释"""
        messages = [
            {"role": "system", "content": "你是一个代码分析专家，擅长逐行解释 Python 代码逻辑。"},
            {"role": "user", "content": f"参考资料:\n{context}\n\n请解释以下代码:\n{code}"},
        ]
        return self.chat(messages)

    def debug_code(self, error_info: str, context: str = "") -> str:
        """代码排错"""
        messages = [
            {"role": "system", "content": "你是一个 Python 调试专家，擅长快速定位并修复代码错误。"},
            {"role": "user", "content": f"参考资料:\n{context}\n\n错误信息:\n{error_info}"},
        ]
        return self.chat(messages)


# 全局客户端单例
llm_client = DeepSeekClient()
