"""Reasoning-model abstraction. The rest of the system only sees `ReasoningModel.complete(...) -> str (JSON)`.

Providers: gemini | anthropic | openai (any OpenAI-compatible base URL) | scripted.
`scripted` is an OFFLINE TEST DOUBLE used for pipeline tests without API keys. It is not AI and is labelled as such
everywhere it surfaces.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from abc import ABC, abstractmethod

from backend.config import model_name, settings


class ModelError(RuntimeError):
    pass


class ReasoningModel(ABC):
    provider: str = ""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def _complete(self, system: str, user: str, image: bytes | None) -> str: ...

    async def complete(self, system: str, user: str, image: bytes | None = None) -> tuple[str, int]:
        """Returns (raw_text, latency_ms). One transport retry on transient failure."""
        last: Exception | None = None
        for attempt in range(2):
            start = time.perf_counter()
            try:
                text = await asyncio.wait_for(self._complete(system, user, image), timeout=settings.model_timeout_s)
                return text, int((time.perf_counter() - start) * 1000)
            except Exception as exc:  # retried once, then surfaced as ModelError
                last = exc
        raise ModelError(f"{self.provider} call failed: {type(last).__name__}: {last}")


class GeminiModel(ReasoningModel):
    provider = "gemini"

    def __init__(self, model: str):
        super().__init__(model)
        from google import genai
        self._client = genai.Client()

    async def _complete(self, system: str, user: str, image: bytes | None) -> str:
        from google.genai import types
        parts: list = []
        if image:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/jpeg"))
        parts.append(user)
        resp = await self._client.aio.models.generate_content(
            model=self.model, contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=settings.temperature,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=0) if "flash" in self.model else None,
            ),
        )
        return resp.text or ""


class AnthropicModel(ReasoningModel):
    provider = "anthropic"

    def __init__(self, model: str):
        super().__init__(model)
        import anthropic
        self._client = anthropic.AsyncAnthropic(max_retries=0)

    async def _complete(self, system: str, user: str, image: bytes | None) -> str:
        content: list[dict] = []
        if image:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(image).decode()}})
        content.append({"type": "text", "text": user})
        kwargs: dict = {}
        if not self.model.startswith("claude-haiku"):
            kwargs["output_config"] = {"effort": "low"}  # per-step latency matters more than depth here
        resp = await self._client.messages.create(
            model=self.model, max_tokens=4000, system=system,
            messages=[{"role": "user", "content": content}], **kwargs,
        )
        if resp.stop_reason == "refusal":
            raise ModelError("model refused")
        return "".join(b.text for b in resp.content if b.type == "text")


class OpenAIModel(ReasoningModel):
    provider = "openai"

    def __init__(self, model: str):
        super().__init__(model)
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(base_url=settings.openai_base_url, max_retries=0)

    async def _complete(self, system: str, user: str, image: bytes | None) -> str:
        content: list[dict] = [{"type": "text", "text": user}]
        if image:
            b64 = base64.standard_b64encode(image).decode()
            content.insert(0, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        resp = await self._client.chat.completions.create(
            model=self.model, temperature=settings.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
        )
        return resp.choices[0].message.content or ""


class OllamaModel(ReasoningModel):
    """Local models via Ollama's native API: JSON-schema constrained decoding + thinking disabled for latency."""
    provider = "ollama"

    def __init__(self, model: str):
        super().__init__(model)
        import httpx
        from backend.schemas import ModelDecision
        self._client = httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=settings.model_timeout_s)
        self._schema = ModelDecision.model_json_schema()

    async def _complete(self, system: str, user: str, image: bytes | None) -> str:
        msg: dict = {"role": "user", "content": user}
        if image:
            msg["images"] = [base64.standard_b64encode(image).decode()]
        # Only the agent's decision call is schema-constrained; free-form probes (health) use plain JSON mode.
        fmt = self._schema if "OBSERVATION_ID:" in user else "json"
        r = await self._client.post("/api/chat", json={
            "model": self.model, "stream": False, "think": False, "format": fmt, "keep_alive": "30m",
            "messages": [{"role": "system", "content": system}, msg],
            "options": {"temperature": settings.temperature, "num_ctx": settings.ollama_num_ctx},
        })
        r.raise_for_status()
        return r.json()["message"]["content"]


def build_model() -> ReasoningModel:
    name = model_name()
    if settings.provider == "ollama":
        return OllamaModel(name)
    if settings.provider == "gemini":
        return GeminiModel(name)
    if settings.provider == "anthropic":
        return AnthropicModel(name)
    if settings.provider == "openai":
        return OpenAIModel(name)
    from backend.agent.scripted import ScriptedModel
    return ScriptedModel(name)


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def extract_json(text: str) -> dict:
    """Parse model text into a dict, tolerating code fences / surrounding prose."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if not m:
            raise
        return json.loads(m.group(0))
