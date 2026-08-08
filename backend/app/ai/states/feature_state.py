from pydantic import BaseModel, Field


class ExtractedFeatureItem(BaseModel):
    title: str = Field(
        description="Short noun-phrase capability name (e.g. Merchant Onboarding), not a user story"
    )
    description: str = Field(
        description=(
            "2–4 sentences: who benefits, what outcome the capability delivers, "
            "and key BRD constraints / boundaries vs sibling features"
        )
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence 0-1")
    rationale: str = Field(
        description="Why this is a distinct deliverable capability grounded in the BRD"
    )
    source_excerpt: str | None = Field(
        default=None,
        description="Short quote or section reference from the BRD",
    )
    source_section_path: str | None = Field(
        default=None,
        description=(
            "Best-matching BRD section path from [Section Path] headers when present "
            "(exact path string for traceability)"
        ),
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="1–3 questions when requirements are ambiguous (omit when clear)",
    )


class FeatureExtractionOutput(BaseModel):
    features: list[ExtractedFeatureItem]


class FeatureCompletenessCritique(BaseModel):
    passes: bool = Field(
        description="True when coverage is sufficient and structure is clean enough"
    )
    missing_sections: list[str] = Field(
        default_factory=list,
        description="BRD section headings or topics not yet reflected in features",
    )
    feedback: str = Field(
        description="Actionable guidance: missing topics, overlaps, or granularity issues"
    )


class FeatureRevisionOutput(BaseModel):
    features: list[ExtractedFeatureItem]


class RefinedFeatureOutput(BaseModel):
    """Single feature revised from clarifying answers."""

    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    source_excerpt: str | None = None
    source_section_path: str | None = None
    clarifying_questions: list[str] = Field(default_factory=list)
