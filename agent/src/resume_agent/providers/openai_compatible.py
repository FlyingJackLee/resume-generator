from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from resume_agent.config import Settings
from resume_agent.errors import ResumeAgentError


OutputT = TypeVar("OutputT", bound=BaseModel)
logger = logging.getLogger(__name__)


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
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            max_retries=0,
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
        response = self.client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {
                    "role": "system",
                    "content": f"{system}\n\nReturn one JSON object matching this JSON Schema:\n{schema}",
                },
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise ResumeAgentError("模型返回空响应")
        logger.debug("LLM raw response output_type=%s:\n%s", output_type.__name__, content)
        usage = getattr(response, "usage", None)
        logger.info("LLM response output_type=%s usage=%s", output_type.__name__, usage)
        try:
            return output_type.model_validate_json(content)
        except Exception as exc:
            raise ResumeAgentError(f"模型结构化输出无效：{exc}") from exc
