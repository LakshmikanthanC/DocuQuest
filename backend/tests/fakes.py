"""Deterministic offline stand-ins for the heavyweight models."""

from __future__ import annotations

import hashlib
import math
import re

DIMENSION = 384
_TOKEN = re.compile(r"[a-z0-9]+")


class FakeEmbeddings:
    """Hashed bag-of-words embedding.

    Not semantically smart, but deterministic and cosine-meaningful enough for
    tests to assert that a question retrieves chunks about the same words.
    """

    def __init__(self, dimension: int = DIMENSION) -> None:
        self.dimension = dimension

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = _TOKEN.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse(self.answer)

    def stream(self, prompt: str):
        self.prompts.append(prompt)
        for word in self.answer.split(" "):
            yield FakeResponse(word + " ")
