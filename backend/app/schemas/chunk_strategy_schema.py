from pydantic import BaseModel, Field

from app.schemas.pipeline_settings_schema import BrdChunkStrategy, CHUNK_STRATEGY_GUIDE


class ChunkStrategyGuideResponse(BaseModel):
    value: BrdChunkStrategy
    label: str
    summary: str
    when_to_use: str
    tradeoffs: str
    is_default: bool = False


class ChunkStrategyListResponse(BaseModel):
    default: BrdChunkStrategy = BrdChunkStrategy.SECTION
    items: list[ChunkStrategyGuideResponse] = Field(default_factory=list)


def build_chunk_strategy_list() -> ChunkStrategyListResponse:
    items = [
        ChunkStrategyGuideResponse(
            value=strategy,
            label=meta["label"],
            summary=meta["summary"],
            when_to_use=meta["when_to_use"],
            tradeoffs=meta["tradeoffs"],
            is_default=strategy == BrdChunkStrategy.SECTION,
        )
        for strategy, meta in CHUNK_STRATEGY_GUIDE.items()
    ]
    return ChunkStrategyListResponse(items=items)
