from pydantic import BaseModel, Field


class ExtractedSubFeatureItem(BaseModel):
    title: str = Field(description="Short sub-feature name")
    description: str = Field(description="Scoped capability within the parent feature")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Why this sub-feature is distinct")
    source_excerpt: str | None = Field(default=None)
    source_section_path: str | None = Field(
        default=None,
        description="Matching BRD [Section Path] when available",
    )


class SubFeatureGenerationOutput(BaseModel):
    sub_features: list[ExtractedSubFeatureItem]


class SubFeatureCritique(BaseModel):
    passes: bool = Field(
        description="True when sub-features are non-overlapping, complete, and well-scoped"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Overlap, gap, or scoping problems found",
    )
    feedback: str = Field(description="Actionable guidance for revision")


class SubFeatureRevisionOutput(BaseModel):
    sub_features: list[ExtractedSubFeatureItem]
