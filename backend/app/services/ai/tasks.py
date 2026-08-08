import logging
import time

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.services.ai.feature_service import FeatureService
from app.services.ai.story_points_service import StoryPointsService
from app.services.ai.story_service import StoryService
from app.services.ai.sub_feature_service import SubFeatureService
from app.services.ai.test_case_service import TestCaseService

logger = logging.getLogger(__name__)


async def _run_ai_task(operation_id: str, *, complete_fn_name: str, service_factory) -> None:
    from app.db.models.async_operation import OperationStatus

    started = time.perf_counter()
    async with async_session_local() as session:
        op_repo = OperationRepository(session)
        try:
            operation = await op_repo.get_by_id(operation_id)
            if not operation:
                logger.error("Operation not found: %s", operation_id)
                return
            if operation.status == OperationStatus.CANCELLED.value:
                logger.info("Skipping cancelled operation: %s", operation_id)
                return

            logger.info(
                "Background AI task starting: %s operation_id=%s resource_type=%s "
                "resource_id=%s",
                complete_fn_name,
                operation_id,
                operation.resource_type,
                operation.resource_id,
            )

            await op_repo.mark_running(operation)
            await session.commit()

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                logger.info("Operation cancelled before work started: %s", operation_id)
                return

            service = service_factory(session)
            complete_fn = getattr(service, complete_fn_name)
            result = await complete_fn(operation_id)

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                logger.info("Operation cancelled during work: %s", operation_id)
                return

            if result is None:
                await op_repo.mark_failed(
                    operation, f"Resource not found for {complete_fn_name}"
                )
                logger.warning(
                    "Background AI task failed (resource missing): %s operation_id=%s",
                    complete_fn_name,
                    operation_id,
                )
            else:
                await op_repo.mark_succeeded(operation)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "Background AI task succeeded: %s operation_id=%s elapsed_ms=%s",
                    complete_fn_name,
                    operation_id,
                    elapsed_ms,
                )

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
                if operation and operation.status != OperationStatus.CANCELLED.value:
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
