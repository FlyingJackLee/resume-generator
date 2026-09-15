import json

import pytest

from resume_agent.config import Settings
from resume_agent.errors import ResumeAgentError
from resume_agent.models import HRReview
from resume_agent.providers.openai_compatible import (
    MAX_STRUCTURED_OUTPUT_ATTEMPTS,
    OpenAICompatibleProvider,
)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]
        self.usage = None


class _FakeCompletions:
    """Returns one canned content string per call, in order, and records the
    message history it was called with so tests can assert the repair turn
    was built correctly."""

    def __init__(self, contents):
        self._contents = list(contents)
        self.calls: list[list[dict]] = []

    def create(self, *, model, messages, response_format, temperature):
        self.calls.append(messages)
        content = self._contents.pop(0)
        return _FakeResponse(content)


def _make_provider(contents) -> tuple[OpenAICompatibleProvider, _FakeCompletions]:
    provider = OpenAICompatibleProvider(Settings(api_key="test-key"))
    fake_completions = _FakeCompletions(contents)
    provider.client.chat.completions = fake_completions
    return provider, fake_completions


VALID_HR_REVIEW = json.dumps(
    {
        "strengths": ["5 年 Python 经验"],
        "weaknesses": ["缺少 Kubernetes/Istio 经验"],
        "missing_keywords": ["Kubernetes"],
        "rewrite_priorities": ["突出云原生经验"],
    },
    ensure_ascii=False,
)

# Reproduces a real DeepSeek response: array fields wrapped as
# {"title": ..., "items": [...]} instead of a bare array.
MALFORMED_HR_REVIEW = json.dumps(
    {
        "strengths": {"title": "Strengths", "items": ["5 年 Python 经验"]},
        "weaknesses": {"title": "Weaknesses", "items": ["缺少 Kubernetes/Istio 经验"]},
        "missing_keywords": {"title": "Missing Keywords", "items": ["Kubernetes"]},
        "rewrite_priorities": {"title": "Rewrite Priorities", "items": ["突出云原生经验"]},
    },
    ensure_ascii=False,
)


def test_succeeds_on_first_try_without_retrying():
    provider, fake = _make_provider([VALID_HR_REVIEW])

    review = provider.complete(system="s", user="u", output_type=HRReview, temperature=0.2)

    assert review.strengths == ["5 年 Python 经验"]
    assert len(fake.calls) == 1


def test_self_heals_after_a_malformed_response():
    provider, fake = _make_provider([MALFORMED_HR_REVIEW, VALID_HR_REVIEW])

    review = provider.complete(system="s", user="u", output_type=HRReview, temperature=0.2)

    assert review.missing_keywords == ["Kubernetes"]
    assert len(fake.calls) == 2

    # The retry must be a real multi-turn repair: the bad output plus a
    # follow-up user turn describing the validation error, appended to the
    # original system/user messages.
    second_call_messages = fake.calls[1]
    assert len(second_call_messages) == 4
    assert second_call_messages[2] == {"role": "assistant", "content": MALFORMED_HR_REVIEW}
    assert second_call_messages[3]["role"] == "user"
    assert "校验" in second_call_messages[3]["content"]


def test_gives_up_after_exhausting_all_attempts():
    provider, fake = _make_provider([MALFORMED_HR_REVIEW] * MAX_STRUCTURED_OUTPUT_ATTEMPTS)

    with pytest.raises(ResumeAgentError) as exc_info:
        provider.complete(system="s", user="u", output_type=HRReview, temperature=0.2)

    assert len(fake.calls) == MAX_STRUCTURED_OUTPUT_ATTEMPTS
    assert str(MAX_STRUCTURED_OUTPUT_ATTEMPTS) in str(exc_info.value)


def test_empty_response_is_treated_as_a_repairable_error():
    provider, fake = _make_provider(["", VALID_HR_REVIEW])

    review = provider.complete(system="s", user="u", output_type=HRReview, temperature=0.2)

    assert review.strengths == ["5 年 Python 经验"]
    assert len(fake.calls) == 2
