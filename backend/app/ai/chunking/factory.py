from __future__ import annotations

from app.ai.chunking.base import BrdChunkStrategyBase, ChunkContext
from app.ai.chunking.strategies.fixed_size_strategy import FixedSizeChunkStrategy
from app.ai.chunking.strategies.hybrid_strategy import HybridChunkStrategy
from app.ai.chunking.strategies.requirement_strategy import RequirementChunkStrategy
from app.ai.chunking.strategies.structure_strategy import StructureChunkStrategy
from app.ai.chunking.types import BrdChunkDraft
from app.schemas.pipeline_settings_schema import BrdChunkStrategy


class ChunkStrategyFactory:
    """
    Factory that selects a BRD chunking strategy by pipeline setting.

    Mirrors `ParserFactory` — new strategies register without changing orchestration.
    """

    def __init__(self, strategies: list[BrdChunkStrategyBase] | None = None):
        instances = strategies or [
            StructureChunkStrategy(BrdChunkStrategy.SECTION),
            StructureChunkStrategy(BrdChunkStrategy.SUBSECTION),
            RequirementChunkStrategy(),
            FixedSizeChunkStrategy(),
            HybridChunkStrategy(),
        ]
        self._by_strategy: dict[BrdChunkStrategy, BrdChunkStrategyBase] = {
            item.strategy: item for item in instances
        }

    def get(self, strategy: BrdChunkStrategy) -> BrdChunkStrategyBase:
        try:
            return self._by_strategy[strategy]
        except KeyError as exc:
            raise ValueError(f"Unsupported chunk strategy: {strategy!r}") from exc

    def register(self, strategy_impl: BrdChunkStrategyBase) -> None:
        self._by_strategy[strategy_impl.strategy] = strategy_impl

    async def chunk(
        self,
        text: str,
        *,
        strategy: BrdChunkStrategy,
        context: ChunkContext | None = None,
    ) -> list[BrdChunkDraft]:
        return await self.get(strategy).chunk(text, context=context)
