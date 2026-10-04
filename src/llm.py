"""OpenAI client that meters every call (tokens, USD, seconds) for the Flat RAG vs GraphRAG benchmark."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, fields

OPENAI_CHAT_MODEL = "gpt-4o-mini"
# USD per 1M tokens (input, output). Check https://openai.com/api/pricing before reporting real numbers.
PRICES_PER_M = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}

@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    seconds: float = 0.0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(*(getattr(self, f.name) + getattr(other, f.name) for f in fields(self)))

    def __sub__(self, other: "Usage") -> "Usage":
        return Usage(*(getattr(self, f.name) - getattr(other, f.name) for f in fields(self)))

def price(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    per_in, per_out = PRICES_PER_M.get(model, (0.0, 0.0))
    return (input_tokens * per_in + output_tokens * per_out) / 1_000_000

class MeteredOpenAI:
    """`chat` and `embed` are drop-in `llm_fn` / `embedding_fn`; `usage` accumulates across calls."""

    def __init__(self, chat_model: str | None = None, embedding_model: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.chat_model = chat_model or os.getenv("OPENAI_CHAT_MODEL", OPENAI_CHAT_MODEL)
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self._backend_name = self.embedding_model
        self.usage = Usage()

    def chat(self, prompt: str, json_mode: bool = False) -> str:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
        )
        tokens_in, tokens_out = response.usage.prompt_tokens, response.usage.completion_tokens
        self.usage += Usage(1, tokens_in, tokens_out, price(self.chat_model, tokens_in, tokens_out), time.perf_counter() - start)
        return response.choices[0].message.content or ""

    def embed(self, text: str) -> list[float]:
        start = time.perf_counter()
        response = self.client.embeddings.create(model=self.embedding_model, input=text)
        tokens = response.usage.prompt_tokens
        self.usage += Usage(1, tokens, 0, price(self.embedding_model, tokens), time.perf_counter() - start)
        return [float(value) for value in response.data[0].embedding]

    __call__ = embed
