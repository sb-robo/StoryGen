from pydantic import BaseModel, Field


class ExtractedSubFeatureItem(BaseModel):
    title: str = Field(description="Short sub-feature name")
    description: str = Field(description="Scoped capability within the parent feature")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Why this sub-feature is distinct")
    source_excerpt: str | None = Field(default=None)


class SubFeatureGenerationOutput(BaseModel):
    sub_features: list[ExtractedSubFeatureItem]
