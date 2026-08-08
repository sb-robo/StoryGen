from __future__ import annotations

from app.ai.feature_extraction.context import FeatureExtractionContext
from app.ai.feature_extraction.context_builder import FeatureExtractionContextBuilder
from app.ai.feature_extraction.feature_merger import FeatureMerger
from app.ai.nodes import feature_extraction as feature_nodes
from app.ai.openai_client import OpenAIClient
from app.ai.rag.chunk_retrieval import (
    FEATURE_RETRIEVAL_QUERY,
    build_retrieval_query,
    retrieve_similar_chunks,
)
from app.ai.states.feature_state import FeatureExtractionOutput
from app.core.config import settings
from app.db.models.brd_chunk import BrdChunk
from app.repositories.brd_chunk_repository import BrdChunkRepository
from app.services.brd.storage_service import BrdStorageService


class FeatureExtractor:
    """
    Orchestrates feature extraction using indexed BRD chunks when available.

    Small/medium BRDs: single pass with chunk-formatted content.
    Large BRDs with embeddings: vector top-k retrieval, then critique/revise.
    Large BRDs without embeddings: map-reduce per top-level section, then refine.
    """

    def __init__(
        self,
        client: OpenAIClient,
        chunk_repo: BrdChunkRepository,
        *,
        storage: BrdStorageService | None = None,
        context_builder: FeatureExtractionContextBuilder | None = None,
        merger: FeatureMerger | None = None,
    ):
        self.client = client
        self.chunk_repo = chunk_repo
        self.context_builder = context_builder or FeatureExtractionContextBuilder(
            chunk_repo, storage=storage
        )
        self.merger = merger or FeatureMerger()

    async def extract(
        self,
        *,
        brd,
        pipeline_context: str,
        operation_id: str | None,
        user_id: int,
    ) -> FeatureExtractionOutput:
        context = await self.context_builder.build(brd)
        chunks = await self.chunk_repo.list_for_brd(brd.id) if context.uses_chunks else []

        if self.context_builder.should_use_retrieval(context):
            retrieved_context = await self._try_retrieval_context(
                brd_id=brd.id,
                structural_context=context,
            )
            if retrieved_context is not None:
                return await self._run_single_pass(
                    brd_name=brd.name,
                    context=retrieved_context,
                    pipeline_context=pipeline_context,
                    operation_id=operation_id,
                    user_id=user_id,
                    brd_id=brd.id,
                )

        if self.context_builder.should_map_reduce(context, chunks):
            draft = await self._extract_map_reduce(
                brd_name=brd.name,
                context=context,
                chunks=chunks,
                pipeline_context=pipeline_context,
                operation_id=operation_id,
                user_id=user_id,
                brd_id=brd.id,
            )
            return await self._refine_draft(
                context=context,
                draft=draft,
                pipeline_context=pipeline_context,
                operation_id=operation_id,
                user_id=user_id,
                brd_id=brd.id,
            )

        return await self._run_single_pass(
            brd_name=brd.name,
            context=context,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd.id,
        )

    async def _try_retrieval_context(
        self,
        *,
        brd_id: int,
        structural_context: FeatureExtractionContext,
    ) -> FeatureExtractionContext | None:
        embedded = await self.chunk_repo.count_embedded_for_brd(brd_id)
        if embedded == 0:
            return None

        query = build_retrieval_query(
            FEATURE_RETRIEVAL_QUERY,
            "Key sections:",
            structural_context.section_hints,
        )
        retrieved = await retrieve_similar_chunks(
            self.client,
            self.chunk_repo,
            brd_id=brd_id,
            query_text=query,
            limit=settings.RAG_FEATURE_CHUNK_LIMIT,
        )
        if not retrieved:
            return None

        return self.context_builder.build_from_retrieved(
            retrieved,
            total_chunk_count=structural_context.chunk_count,
            section_hints=structural_context.section_hints,
        )

    async def _run_single_pass(
        self,
        *,
        brd_name: str,
        context: FeatureExtractionContext,
        pipeline_context: str,
        operation_id: str | None,
        user_id: int,
        brd_id: int,
    ) -> FeatureExtractionOutput:
        from app.ai.graphs.feature_extraction import run_feature_extraction_graph

        return await run_feature_extraction_graph(
            self.client,
            brd_name=brd_name,
            brd_content=context.brd_content,
            section_hints=context.section_hints,
            pipeline_context=pipeline_context,
            operation_id=operation_id,
            user_id=user_id,
            brd_id=brd_id,
        )

    async def _extract_map_reduce(
        self,
        *,
        brd_name: str,
        context: FeatureExtractionContext,
        chunks: list[BrdChunk],
        pipeline_context: str,
        operation_id: str | None,
        user_id: int,
        brd_id: int,
    ) -> FeatureExtractionOutput:
        section_outputs: list[FeatureExtractionOutput] = []
        for section, group_chunks in self.context_builder.group_chunks_by_section(chunks):
            section_content = self.context_builder.format_chunk_group(section, group_chunks)
            output = await feature_nodes.generate_features(
                self.client,
                brd_name=brd_name,
                brd_content=section_content,
                pipeline_context=pipeline_context,
                operation_id=operation_id,
                user_id=user_id,
                brd_id=brd_id,
                iteration=0,
            )
            section_outputs.append(output)
        return self.merger.merge(section_outputs)

    async def _refine_draft(
        self,
        *,
        context: FeatureExtractionContext,
        draft: FeatureExtractionOutput,
        pipeline_context: str,
        operation_id: str | None,
        user_id: int,
        brd_id: int,
    ) -> FeatureExtractionOutput:
        current = draft
        for iteration in range(1, settings.LLM_MAX_ITERATIONS + 1):
            critique_result = await feature_nodes.critique_completeness(
                self.client,
                section_hints=context.section_hints,
                draft=current,
                pipeline_context=pipeline_context,
                operation_id=operation_id,
                user_id=user_id,
                brd_id=brd_id,
                iteration=iteration,
            )
            if critique_result.passes:
                break
            revised = await feature_nodes.revise_features(
                self.client,
                brd_content=context.brd_content,
                draft=current,
                critique=critique_result,
                pipeline_context=pipeline_context,
                operation_id=operation_id,
                user_id=user_id,
                brd_id=brd_id,
                iteration=iteration,
            )
            current = FeatureExtractionOutput(features=revised.features)
        return current
