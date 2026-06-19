from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


import os
import dotenv


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Student TODO: load environment variables and return a LabConfig.

    Pseudocode:
    1. Resolve the repo root or default to the current file parent.
    2. Optionally load values from `.env`.
    3. Create `state/` if it does not exist.
    4. Return a populated LabConfig instance.
    """
    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    dotenv_path = root / ".env"
    if dotenv_path.exists():
        dotenv.load_dotenv(dotenv_path)
    else:
        dotenv.load_dotenv()

    # Paths
    data_dir = root / "data"
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "profiles").mkdir(parents=True, exist_ok=True)

    # Compact memory settings
    compact_threshold_tokens = int(os.environ.get("COMPACT_THRESHOLD_TOKENS", "300"))
    compact_keep_messages = int(os.environ.get("COMPACT_KEEP_MESSAGES", "4"))

    # Provider settings
    provider = os.environ.get("LLM_PROVIDER", "openai")
    model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.0"))

    api_key = None
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
    elif provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
    elif provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    elif provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
    elif provider == "custom":
        api_key = os.environ.get("CUSTOM_API_KEY")

    base_url = os.environ.get("CUSTOM_BASE_URL") or os.environ.get("OLLAMA_BASE_URL")

    model_config = ProviderConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )

    # Judge configuration
    judge_provider = os.environ.get("JUDGE_PROVIDER", provider)
    judge_model_name = os.environ.get("JUDGE_MODEL", model_name)

    judge_api_key = None
    if judge_provider == "openai":
        judge_api_key = os.environ.get("OPENAI_API_KEY")
    elif judge_provider == "gemini":
        judge_api_key = os.environ.get("GEMINI_API_KEY")
    elif judge_provider == "anthropic":
        judge_api_key = os.environ.get("ANTHROPIC_API_KEY")
    elif judge_provider == "openrouter":
        judge_api_key = os.environ.get("OPENROUTER_API_KEY")
    elif judge_provider == "custom":
        judge_api_key = os.environ.get("CUSTOM_API_KEY")

    judge_config = ProviderConfig(
        provider=judge_provider,
        model_name=judge_model_name,
        temperature=0.0,
        api_key=judge_api_key,
        base_url=base_url,
    )

    return LabConfig(
        base_dir=root,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=compact_threshold_tokens,
        compact_keep_messages=compact_keep_messages,
        model=model_config,
        judge_model=judge_config,
    )
