from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_story_service
from app.db.models.user import User
from app.schemas.story_schema import (
    StoryResponse,
    StoryReviewResponse,
    StoryUpdateRequest,
)
from app.services.ai import StoryService

router = APIRouter()


@router.patch(
    "/{story_id}",
    response_model=StoryResponse,
    summary="Edit a user story",
)
async def update_story(
    story_id: int,
    payload: StoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryResponse:
    return await story_service.update_story(current_user.id, story_id, payload)


@router.post(
    "/{story_id}/approve",
    response_model=StoryReviewResponse,
    summary="Approve a user story after human review",
)
async def approve_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryReviewResponse:
    return await story_service.approve_story(current_user.id, story_id)


@router.post(
    "/{story_id}/reject",
    response_model=StoryReviewResponse,
    summary="Reject a user story after human review",
)
async def reject_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    story_service: StoryService = Depends(get_story_service),
) -> StoryReviewResponse:
    return await story_service.reject_story(current_user.id, story_id)
