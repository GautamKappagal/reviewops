"""Runtime settings, read from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_version: str
    prompt_version: str
    llm_backend: str      # "fake" (deterministic, default) or "ollama"
    ollama_url: str
    ollama_model: str
    max_history: int


def get_settings() -> Settings:
    return Settings(
        app_version=os.getenv("APP_VERSION", "0.1.0-dev"),
        prompt_version=os.getenv("PROMPT_VERSION", "v1"),
        llm_backend=os.getenv("LLM_BACKEND", "fake").lower(),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
        max_history=int(os.getenv("MAX_HISTORY", "50")),
    )
