"""LLM client wrappers behind one tiny interface.

Isolating the network call here means:
  * the rest of the app depends on a stable interface (``complete``); and
  * unit tests can swap in a fake client with no network access; and
  * adding a new provider is just a new class + a line in the factory.

Security: API keys are held only inside these server-side client objects and
are never serialised back to the browser.
"""

from __future__ import annotations

from typing import Protocol

from . import config


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class GroqClient:
    """Client backed by Groq's OpenAI-compatible chat API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = config.DEFAULT_TEMPERATURE,
        max_tokens: int = config.DEFAULT_MAX_TOKENS,
    ) -> None:
        if not api_key:
            raise ValueError("A Groq API key is required.")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model or config.PROVIDERS["groq"]["default_model"]
        self._temperature = temperature
        self._max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


class GeminiClient:
    """Client backed by Google's Gemini (Generative AI) API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = config.DEFAULT_TEMPERATURE,
        max_tokens: int = config.DEFAULT_MAX_TOKENS,
    ) -> None:
        if not api_key:
            raise ValueError("A Gemini API key is required.")
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model or config.PROVIDERS["gemini"]["default_model"]
        self._temperature = temperature
        self._max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config={
                "temperature": self._temperature,
                "max_output_tokens": self._max_tokens,
            },
        )
        return getattr(response, "text", "") or ""


_CLIENTS = {
    "groq": GroqClient,
    "gemini": GeminiClient,
}


def create_client(provider: str, api_key: str, model: str | None = None) -> LLMClient:
    """Factory: return the right client for a provider name."""
    cls = _CLIENTS.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider}")
    return cls(api_key=api_key, model=model)
