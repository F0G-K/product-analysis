"""OpenAI 兼容模型适配器。"""

import json
from typing import Any

import httpx
from asa_core.application.ports.model_port import ModelPort, ModelRequest, ModelResult
from asa_core.domain.agents.exceptions import ModelCallFailed, ModelOutputInvalid
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AgentModelOutput(BaseModel):
    """所有角色共享的最小结构化输出。"""

    model_config = ConfigDict(extra="allow")

    summary: str = Field(min_length=1, max_length=4000)
    role: str | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)


class OpenAICompatibleModelAdapter(ModelPort):
    """通过 OpenAI 兼容 Chat Completions 协议调用模型。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("模型 API 地址必须是 HTTP(S) URL")
        if not api_key or not model_name:
            raise ValueError("模型 API Key 和模型名称不能为空")
        if timeout_seconds <= 0 or max_output_tokens <= 0:
            raise ValueError("模型超时和输出 token 上限必须大于 0")
        self._model_name = model_name
        self._max_output_tokens = max_output_tokens
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def complete(self, request: ModelRequest) -> ModelResult:
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": request.user_prompt,
                            "context": request.context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in request.tools
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "asa_agent_output",
                    "strict": True,
                    "schema": request.output_schema,
                },
            },
            "max_completion_tokens": self._max_output_tokens,
        }
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw_output = json.loads(content) if isinstance(content, str) else content
            output = AgentModelOutput.model_validate(raw_output)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ModelCallFailed("模型服务暂时不可用", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code == 429 or exc.response.status_code >= 500
            raise ModelCallFailed("模型服务返回错误", retryable=retryable) from exc
        except httpx.HTTPError as exc:
            raise ModelCallFailed("模型服务调用失败", retryable=False) from exc
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise ModelOutputInvalid() from exc

        usage = body.get("usage") or {}
        return ModelResult(
            content=output.model_dump(mode="json"),
            summary=output.summary,
            prompt_tokens=max(0, int(usage.get("prompt_tokens", 0))),
            completion_tokens=max(0, int(usage.get("completion_tokens", 0))),
        )

    def estimate_tokens(self, text: str) -> int:
        # 不依赖供应商 tokenizer，使用保守估算供上下文裁剪。
        return max(1, (len(text) + 2) // 3)

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/models")
            return response.is_success
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
