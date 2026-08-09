"""OpenAI SDK wrapper with structured output and call logging."""

from __future__ import annotations

import hashlib
import time
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.llm_call_log import LlmCallLog
from app.repositories.llm_call_log_repository import LlmCallLogRepository
from app.utils.process_tracker import node_label, track, track_error

T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    def __init__(
        self,
        db: AsyncSession | None = None,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.db = db
        self.model = (model or settings.openai_model).strip()
        self.embedding_model = settings.openai_embedding_model
        self.log_repo = LlmCallLogRepository(db) if db is not None else None
        key = (api_key or settings.openai_api_key).strip()
        self._client: AsyncOpenAI | None = (
            AsyncOpenAI(
                api_key=key,
                max_retries=settings.LLM_MAX_RETRIES,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            if key
            else None
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def parse_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[T],
        node_name: str,
        iteration: int = 0,
        operation_id: str | None = None,
        user_id: int | None = None,
        brd_id: int | None = None,
        temperature: float | None = None,
    ) -> T:
        if self._client is None:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in backend/.env to run AI stages."
            )

        prompt_hash = hashlib.sha256(
            "|".join(f"{m['role']}:{m['content']}" for m in messages).encode()
        ).hexdigest()
        prompt_chars = sum(len(m["content"]) for m in messages)
        label = node_label(node_name)
        round_suffix = f" round {iteration}" if iteration else ""

        track(
            f"LLM start: {label}{round_suffix}",
            model=self.model,
            chars=prompt_chars,
            brd_id=brd_id,
        )

        create_kwargs: dict = {}
        if settings.LLM_ENABLE_TEMPERATURE_CONTROL and temperature is not None:
            create_kwargs["temperature"] = temperature

        started = time.perf_counter()
        try:
            response = await self._client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                **create_kwargs,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            track_error(
                f"LLM failed: {label}{round_suffix}",
                exc=exc,
                model=self.model,
                ms=latency_ms,
            )
            raise
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        track(
            f"LLM done: {label}{round_suffix}",
            model=self.model,
            ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        if self.log_repo is not None and user_id is not None:
            await self.log_repo.create(
                LlmCallLog(
                    operation_id=operation_id,
                    user_id=user_id,
                    brd_id=brd_id,
                    node_name=node_name,
                    iteration=iteration,
                    model=self.model,
                    prompt_hash=prompt_hash,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                )
            )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            track_error(
                f"LLM returned no parsed output: {label}",
                finish_reason=response.choices[0].finish_reason if response.choices else None,
            )
            raise RuntimeError(f"OpenAI returned no parsed output for node {node_name}")
        return parsed

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if not texts:
            return []

        track(
            "embed texts for retrieval",
            model=self.embedding_model,
            count=len(texts),
        )
        response = await self._client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]
