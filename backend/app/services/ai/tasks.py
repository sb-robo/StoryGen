import logging

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.services.ai.feature_service import FeatureService
from app.services.ai.story_points_service import StoryPointsService
from app.services.ai.story_service import StoryService
from app.services.ai.sub_feature_service import SubFeatureService
from app.services.ai.test_case_service import TestCaseService

logger = logging.getLogger(__name__)


async def _run_ai_task(operation_id: str, *, complete_fn_name: str, service_factory) -> None:
    async with async_session_local() as session:
        op_repo = OperationRepository(session)
        try:
            operation = await op_repo.get_by_id(operation_id)
            if not operation:
                logger.error("Operation not found: %s", operation_id)
                return

            await op_repo.mark_running(operation)
            await session.commit()

            service = service_factory(session)
            complete_fn = getattr(service, complete_fn_name)
            result = await complete_fn(operation_id)
            if result is None:
                await op_repo.mark_failed(
                    operation, f"Resource not found for {complete_fn_name}"
                )
            else:
                await op_repo.mark_succeeded(operation)

            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception(
                "Background AI task failed (%s) for operation_id=%s",
                complete_fn_name,
                operation_id,
            )
            try:
                operation = await op_repo.get_by_id(operation_id)
                if operation:
                    await op_repo.mark_failed(operation, str(exc))
                    await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "Failed to mark operation as failed: %s", operation_id
                )


async def run_feature_extraction_task(operation_id: str) -> None:
    await _run_ai_task(
        operation_id,
        complete_fn_name="complete_extraction",
        service_factory=FeatureService,
    )


async def run_sub_feature_generation_task(operation_id: str) -> None:
    await _run_ai_task(
        operation_id,
        complete_fn_name="complete_generation",
        service_factory=SubFeatureService,
    )


async def run_story_generation_task(operation_id: str) -> None:
    await _run_ai_task(
        operation_id,
        complete_fn_name="complete_generation",
        service_factory=StoryService,
    )


async def run_story_point_estimation_task(operation_id: str) -> None:
    await _run_ai_task(
        operation_id,
        complete_fn_name="complete_estimation",
        service_factory=StoryPointsService,
    )


async def run_test_case_generation_task(operation_id: str) -> None:
    await _run_ai_task(
        operation_id,
        complete_fn_name="complete_generation",
        service_factory=TestCaseService,
    )
