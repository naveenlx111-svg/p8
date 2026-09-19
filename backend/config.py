"""Environment-based configuration. Every knob is overridable via env vars prefixed PATHLENS_."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # provider SDKs read their API keys from os.environ


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATHLENS_", env_file=ROOT / ".env", extra="ignore")

    # Model provider: gemini | anthropic | openai | scripted (scripted = offline test double, NOT AI)
    provider: Literal["gemini", "anthropic", "openai", "ollama", "scripted"] = "gemini"
    model: str = ""  # empty -> provider default
    openai_base_url: str | None = None  # any OpenAI-compatible endpoint (Groq, OpenRouter, vLLM...)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_num_ctx: int = 8192
    vision_mode: Literal["always", "fallback", "off"] = "always"
    model_timeout_s: float = 25.0
    temperature: float = 0.0

    target_url: str = "http://127.0.0.1:4173/"
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 800

    max_steps: int = 100  # safety ceiling only; runs normally end on verified success or stall detection
    stall_limit: int = 8  # stop after this many actions with no new screen and no goal progress
    max_recoveries: int = 2
    action_timeout_ms: int = 2500
    max_elements: int = 80
    allow_irreversible: bool = False

    artifacts_dir: Path = ROOT / "artifacts"
    replay_dir: Path = ROOT / "replay_runs"
    upload_dir: Path = ROOT / "uploads"
    axe_path: Path = ROOT / "backend" / "vendor" / "axe.min.js"


settings = Settings()

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-opus-5",
    "openai": "gpt-4.1-mini",
    "ollama": "qwen2.5:7b",
    "scripted": "scripted-heuristic",
}


def model_name() -> str:
    return settings.model or DEFAULT_MODELS[settings.provider]
