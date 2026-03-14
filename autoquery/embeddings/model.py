"""Embedding model abstraction + Ollama BGE implementation."""

from __future__ import annotations

import math
import os
from abc import ABC, abstractmethod

import httpx


def _l2_normalize(vec: list[float]) -> list[float]:
    """L2-normalize a vector in-place."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


class EmbeddingModel(ABC):
    """Abstract embedding interface."""

    dimensions: int

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text, returning an L2-normalized vector."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. Default: sequential calls."""
        return [await self.embed(t) for t in texts]


class OllamaEmbeddingModel(EmbeddingModel):
    """BGE-large-en-v1.5 (1024-dim) via Ollama /api/embeddings."""

    def __init__(
        self,
        model_name: str | None = None,
        ollama_url: str | None = None,
        dimensions: int = 1024,
    ):
        self.model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", "bge-large-en-v1.5"
        )
        self.ollama_url = (ollama_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434"
        )).rstrip("/")
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """POST to Ollama /api/embeddings, validate dims, L2-normalize."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
            )
            resp.raise_for_status()
            vec = resp.json()["embedding"]

        if len(vec) != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, got {len(vec)}. "
                f"Model '{self.model_name}' may not match the DB schema."
            )
        return _l2_normalize(vec)
