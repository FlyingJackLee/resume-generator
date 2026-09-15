from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel
from langsmith.wrappers import wrap_openai

from resume_agent.config import Settings
from resume_agent.errors import ResumeAgentError


OutputT = TypeVar("OutputT", bound=BaseModel)
logger = logging.getLogger(__name__)

# First attempt plus up to two self-repair retries. Structured-output
# violations (malformed JSON, schema mismatches) are a normal, low-probability
# occurrence for any OpenAI-compatible model, not a bug to special-case per
# shape — feeding the exact validation error back to the model to fix is
# provider-agnostic and works regardless of which OpenAI-compatible endpoint
# RESUME_AGENT_BASE_URL points at.
MAX_STRUCTURED_OUTPUT_ATTEMPTS = 3


class StructuredProvider(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        output_type: type[OutputT],
        temperature: float,
    ) -> OutputT: ...


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise ResumeAgentError("未设置 RESUME_AGENT_API_KEY")
        self.settings = settings
        # LangGraph traces the workflow topology; wrapping the OpenAI-compatible
        # client adds the actual model request as a child span. The wrapper is a
        # no-op for remote logging unless LANGSMITH_TRACING is enabled.
        self.client = wrap_openai(
            OpenAI(
                api_key=settings.api_key,
                base_url=settings.base_url,
                timeout=settings.timeout_seconds,
                max_retries=0,
            ),
            completions_name="Resume LLM completion",
        )

    def complete(
        self,
        *,
        system: str,
        user: str,
        output_type: type[OutputT],
        temperature: float,
    ) -> OutputT:
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        logger.info(
            "LLM request model=%s output_type=%s temperature=%s",
            self.settings.model,
            output_type.__name__,
            temperature,
        )
        logger.debug("LLM system prompt:\n%s", system)
        logger.debug("LLM user payload:\n%s", user)
        messages = [
            {
                "role": "system",
                "content": f"{system}\n\nReturn one JSON object matching this JSON Schema:\n{schema}",
            },
            {"role": "user", "content": user},
        ]
        return self._complete_with_repair(messages, output_type, temperature)

    def complete_with_images(
        self, *, system: str, user: str, image_urls: list[str], output_type: type[OutputT], temperature: float
    ) -> OutputT:
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        content: list[dict[str, object]] = [{"type": "text", "text": user}]
        content.extend({"type": "image_url", "image_url": {"url": url, "detail": "high"}} for url in image_urls)
        messages = [
            {"role": "system", "content": f"{system}\n\nReturn one JSON object matching this JSON Schema:\n{schema}"},
            {"role": "user", "content": content},
        ]
        return self._complete_with_repair(messages, output_type, temperature)

    def _complete_with_repair(
        self, messages: list[dict[str, object]], output_type: type[OutputT], temperature: float
    ) -> OutputT:
        last_error: Exception | None = None
        for attempt in range(1, MAX_STRUCTURED_OUTPUT_ATTEMPTS + 1):
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            raw = response.choices[0].message.content or ""
            logger.debug(
                "LLM raw response output_type=%s attempt=%s:\n%s", output_type.__name__, attempt, raw
            )
            usage = getattr(response, "usage", None)
            logger.info(
                "LLM response output_type=%s attempt=%s usage=%s", output_type.__name__, attempt, usage
            )
            try:
                if not raw:
                    raise ValueError("模型返回空响应")
                return output_type.model_validate_json(raw)
            except Exception as exc:
                last_error = exc
                if attempt == MAX_STRUCTURED_OUTPUT_ATTEMPTS:
                    break
                logger.warning(
                    "structured output invalid, retrying attempt=%s/%s output_type=%s error=%s",
                    attempt,
                    MAX_STRUCTURED_OUTPUT_ATTEMPTS,
                    output_type.__name__,
                    exc,
                )
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次的输出没有通过校验，错误如下：\n"
                            f"{exc}\n\n"
                            "请只返回修正后的完整 JSON 对象，严格匹配前面给出的 JSON Schema，"
                            "不要包含任何解释、注释或 Markdown 代码块。"
                        ),
                    }
                )
        raise ResumeAgentError(
            f"模型结构化输出无效（已重试 {MAX_STRUCTURED_OUTPUT_ATTEMPTS - 1} 次，共 "
            f"{MAX_STRUCTURED_OUTPUT_ATTEMPTS} 次尝试）：{last_error}"
        ) from last_error
