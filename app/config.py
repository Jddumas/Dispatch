"""Central configuration and helpers for the Dispatch AI backend."""

from __future__ import annotations

import logging
import os

LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1")
CLASSIFY_MODEL = os.getenv("CLASSIFY_MODEL", LLM_MODEL)
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", "data/checkpoints.sqlite")
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "2000"))


def setup_logging(level: int | str | None = None) -> None:
    """Configure the root logger for the project."""
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
