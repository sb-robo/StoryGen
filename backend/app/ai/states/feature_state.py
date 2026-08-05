from pydantic import BaseModel, Field


class ExtractedFeatureItem(BaseModel):
    title: str = Field(description="Short feature name")
    description: str = Field(description="What the feature delivers for the user/business")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence 0-1")
    rationale: str = Field(description="Why this is a distinct feature based on the BRD")
    source_excerpt: str | None = Field(
        default=None, description="Relevant quote or section reference from the BRD"
    )
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="Questions when requirements are ambiguous",
    )


class FeatureExtractionOutput(BaseModel):
    features: list[ExtractedFeatureItem]


class FeatureCompletenessCritique(BaseModel):
    passes: bool = Field(description="True when coverage is sufficient")
    missing_sections: list[str] = Field(
        default_factory=list,
        description="BRD section headings or topics not yet reflected in features",
    )
    feedback: str = Field(description="Actionable guidance for the next revision")


class FeatureRevisionOutput(BaseModel):
    features: list[ExtractedFeatureItem]
