from pydantic import BaseModel, Field


class ExtractedStoryItem(BaseModel):
    title: str = Field(description="Short story title")
    description: str = Field(
        description="User story in 'As a ... I want ... so that ...' format"
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Testable acceptance criteria",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Why this story is needed and well-scoped")
    source_excerpt: str | None = Field(default=None)
    source_section_path: str | None = Field(
        default=None,
        description="Matching BRD [Section Path] when available",
    )


class StoryGenerationOutput(BaseModel):
    stories: list[ExtractedStoryItem]


class StoryInvestCritique(BaseModel):
    passes: bool = Field(description="True when all stories meet INVEST criteria")
    issues: list[str] = Field(
        default_factory=list,
        description="INVEST violations or quality problems per story",
    )
    feedback: str = Field(description="Actionable guidance for revision")


class StoryRevisionOutput(BaseModel):
    stories: list[ExtractedStoryItem]
