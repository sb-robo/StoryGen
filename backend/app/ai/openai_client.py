"""OpenAI SDK wrapper with structured output and call logging."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.llm_call_log import LlmCallLog
from app.repositories.llm_call_log_repository import LlmCallLogRepository

logger = logging.getLogger(__name__)

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
    ) -> T:
        if self._client is None:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in backend/.env to run AI stages."
            )

        prompt_hash = hashlib.sha256(
            "|".join(f"{m['role']}:{m['content']}" for m in messages).encode()
        ).hexdigest()
        prompt_chars = sum(len(m["content"]) for m in messages)

        logger.info(
            "LLM call starting: node=%s iteration=%s model=%s operation_id=%s brd_id=%s "
            "prompt_chars=%s",
            node_name,
            iteration,
            self.model,
            operation_id,
            brd_id,
            prompt_chars,
        )

        started = time.perf_counter()
        try:
            response = await self._client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
            )
        except Exception:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "LLM call failed: node=%s iteration=%s model=%s operation_id=%s "
                "after %sms",
                node_name,
                iteration,
                self.model,
                operation_id,
                latency_ms,
            )
            raise
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        logger.info(
            "LLM call finished: node=%s iteration=%s latency_ms=%s tokens_in=%s "
            "tokens_out=%s operation_id=%s",
            node_name,
            iteration,
            latency_ms,
            tokens_in,
            tokens_out,
            operation_id,
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
            logger.error(
                "LLM call returned no parsed output: node=%s operation_id=%s "
                "finish_reason=%s refusal=%s",
                node_name,
                operation_id,
                response.choices[0].finish_reason if response.choices else None,
                getattr(response.choices[0].message, "refusal", None)
                if response.choices
                else None,
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

        response = await self._client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]
