"""Thin, provider-agnostic LLM clients (Anthropic + any OpenAI-compatible API)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Protocol

Message = Dict[str, str]

PROVIDER_PRESETS = {
    "anthropic": {"label": "Anthropic (Claude)", "base_url": None, "env_key": "ANTHROPIC_API_KEY",
                  "default_model": "claude-sonnet-5-5"},
    "openai": {"label": "OpenAI", "base_url": None, "env_key": "OPENAI_API_KEY", "default_model": "gpt-4o-mini"},
    "groq": {"label": "Groq (OpenAI-compatible)", "base_url": "https://api.groq.com/openai/v1",
             "env_key": "GROQ_API_KEY", "default_model": "llama-3.3-70b-versatile"},
    "gemini": {"label": "Google Gemini (OpenAI-compatible)",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "env_key": "GEMINI_API_KEY", "default_model": "gemini-2.0-flash"},
    "custom": {"label": "Custom OpenAI-compatible endpoint (e.g. Ollama, OpenRouter)", "base_url": None,
               "env_key": "LLM_API_KEY", "default_model": ""},
}


class LLMError(RuntimeError):
    """Raised when the model call fails for a non-recoverable reason."""


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, messages: List[Message]) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str, model: str, max_tokens: int = 800, temperature: float = 0.0) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError("The 'anthropic' package is not installed (pip install anthropic).") from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key, max_retries=3)
        self.model, self.max_tokens, self.temperature = model, max_tokens, temperature
        self.name = f"anthropic:{model}"

    def complete(self, system: str, messages: List[Message]) -> str:
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=system, messages=messages)
        try:
            try:
                resp = self._client.messages.create(temperature=self.temperature, **kwargs)
            except self._anthropic.BadRequestError as exc:
                if "temperature" not in str(exc).lower():
                    raise
                resp = self._client.messages.create(**kwargs)  # model does not accept a temperature
        except self._anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


class OpenAICompatClient:
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, temperature: float = 0.0,
                 label: str = "openai") -> None:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise LLMError("The 'openai' package is not installed (pip install openai).") from exc
        self._openai = openai
        self._client = openai.OpenAI(api_key=api_key or "not-needed", base_url=base_url, max_retries=3)
        self.model, self.temperature = model, temperature
        self.name = f"{label}:{model}"

    def complete(self, system: str, messages: List[Message]) -> str:
        payload = [{"role": "system", "content": system}] + list(messages)
        try:
            try:
                resp = self._client.chat.completions.create(model=self.model, messages=payload,
                                                            temperature=self.temperature)
            except self._openai.BadRequestError as exc:
                if "temperature" not in str(exc).lower():
                    raise
                resp = self._client.chat.completions.create(model=self.model, messages=payload)
        except self._openai.OpenAIError as exc:
            raise LLMError(f"LLM API error: {exc}") from exc
        return (resp.choices[0].message.content or "").strip()


class CachedLLM:
    """Disk cache so re-running an evaluation costs nothing and is reproducible."""

    def __init__(self, inner: LLMClient, cache_path: Path | str) -> None:
        self.inner = inner
        self.name = inner.name
        self.path = Path(cache_path)
        self._store: Dict[str, str] = {}
        if self.path.exists():
            try:
                self._store = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._store = {}

    def complete(self, system: str, messages: List[Message]) -> str:
        key = hashlib.sha256(json.dumps([self.inner.name, system, messages], sort_keys=True).encode()).hexdigest()
        if key not in self._store:
            self._store[key] = self.inner.complete(system, messages)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._store, indent=1), encoding="utf-8")
        return self._store[key]


def resolve_api_key(provider: str, explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
    return os.environ.get(preset["env_key"]) or os.environ.get("LLM_API_KEY")


def create_llm(provider: str, model: Optional[str] = None, api_key: Optional[str] = None,
               base_url: Optional[str] = None) -> LLMClient:
    """Factory used by the app and the command-line scripts."""
    if provider not in PROVIDER_PRESETS:
        raise LLMError(f"Unknown provider '{provider}'. Choose from {', '.join(PROVIDER_PRESETS)}.")
    preset = PROVIDER_PRESETS[provider]
    model = model or preset["default_model"]
    if not model:
        raise LLMError("Please provide a model name.")
    key = resolve_api_key(provider, api_key)
    if provider == "anthropic":
        if not key:
            raise LLMError("No Anthropic API key found. Set ANTHROPIC_API_KEY or enter it in the app.")
        return AnthropicClient(key, model)
    url = base_url or preset["base_url"] or os.environ.get("OPENAI_BASE_URL")
    if not key and provider != "custom":
        raise LLMError(f"No API key found for {preset['label']}. Set {preset['env_key']} or enter it in the app.")
    return OpenAICompatClient(key or "", model, base_url=url, label=provider)
