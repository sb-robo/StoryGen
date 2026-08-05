from pydantic import BaseModel, Field


class StoryPointsEstimate(BaseModel):
    story_points: int = Field(ge=1, le=21, description="Estimated story points")
    rationale: str = Field(description="Why this estimate fits the story scope")
    confidence: float = Field(ge=0.0, le=1.0)


class StoryPointsCritique(BaseModel):
    passes: bool
    feedback: str
    suggested_points: int | None = Field(
        default=None, description="Adjusted points if critique fails"
    )


class StoryPointsRevision(BaseModel):
    story_points: int = Field(ge=1, le=21)
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
