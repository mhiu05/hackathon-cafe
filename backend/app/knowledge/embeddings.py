"""Voyage AI embeddings over plain HTTPS (no SDK dependency).

Contract:
- documents are embedded with input_type="document", queries with input_type="query";
- vectors are returned as float32 and L2-normalised, shape (n, dimension);
- any transport/HTTP failure raises EmbeddingError (callers fall back to keyword search).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
import numpy as np

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


class EmbeddingError(RuntimeError):
    """Raised when Voyage cannot return embeddings (timeout, auth, quota, malformed response)."""


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


@dataclass
class VoyageEmbedder:
    api_key: str
    model: str = "voyage-4-lite"
    dimension: int = 512
    timeout_s: float = 8.0
    batch_size: int = 64
    max_retries: int = 1
    total_tokens: int = field(default=0, init=False)

    def _payload(self, texts: list[str], input_type: str) -> dict:
        return {"input": texts, "model": self.model, "input_type": input_type, "output_dimension": self.dimension}

    def _parse(self, body: dict, expected: int) -> np.ndarray:
        try:
            data = sorted(body["data"], key=lambda d: d["index"])
            vectors = np.asarray([d["embedding"] for d in data], dtype=np.float32)
            self.total_tokens += int(body.get("usage", {}).get("total_tokens", 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError(f"Malformed Voyage response: {exc}") from exc
        if vectors.shape != (expected, self.dimension):
            raise EmbeddingError(f"Unexpected embedding shape {vectors.shape}, wanted ({expected}, {self.dimension})")
        return l2_normalize(vectors)

    def _post(self, texts: list[str], input_type: str) -> np.ndarray:
        if not self.api_key:
            raise EmbeddingError("VOYAGE_API_KEY is not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.post(VOYAGE_URL, headers=headers, json=self._payload(texts, input_type), timeout=self.timeout_s)
                if resp.status_code == 200:
                    return self._parse(resp.json(), len(texts))
                last_error = EmbeddingError(f"Voyage HTTP {resp.status_code}: {resp.text[:200]}")
                if resp.status_code not in (429, 500, 502, 503, 504):
                    break
            except httpx.HTTPError as exc:
                last_error = EmbeddingError(f"Voyage transport error: {type(exc).__name__}")
            if attempt < self.max_retries:
                time.sleep(1.5 * (attempt + 1))
        raise last_error or EmbeddingError("Voyage request failed")

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        parts = [self._post(texts[i : i + self.batch_size], "document") for i in range(0, len(texts), self.batch_size)]
        return np.vstack(parts)

    def embed_query(self, text: str) -> np.ndarray:
        return self._post([text], "query")[0]

    async def aembed_query(self, text: str) -> np.ndarray:
        """Async single-query embedding for request handlers/agent tools (no retry: fail fast)."""
        if not self.api_key:
            raise EmbeddingError("VOYAGE_API_KEY is not set")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    VOYAGE_URL, headers={"Authorization": f"Bearer {self.api_key}"}, json=self._payload([text], "query")
                )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Voyage transport error: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise EmbeddingError(f"Voyage HTTP {resp.status_code}: {resp.text[:200]}")
        return self._parse(resp.json(), 1)[0]


def vector_to_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype="<f4").tobytes()


def blob_to_vector(blob: bytes, dimension: int) -> np.ndarray:
    vec = np.frombuffer(blob, dtype="<f4")
    if vec.shape[0] != dimension:
        raise ValueError(f"Vector blob has {vec.shape[0]} dims, expected {dimension}")
    return vec
