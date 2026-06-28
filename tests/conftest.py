"""Shared pytest fixtures and test doubles."""

from __future__ import annotations

import pytest


class FakeLLMClient:
    """Records the prompts it receives and returns canned responses."""

    def __init__(self, response: str = "```python\ndef test_ok():\n    assert True\n```") -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


class FailingLLMClient:
    """Always raises, to exercise error-handling paths."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("boom")


@pytest.fixture
def fake_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def failing_client() -> FailingLLMClient:
    return FailingLLMClient()
