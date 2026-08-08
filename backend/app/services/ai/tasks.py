import time

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.services.ai.feature_service import FeatureService
from app.services.ai.story_points_service import StoryPointsService
from app.services.ai.story_service import StoryService
from app.services.ai.sub_feature_service import SubFeatureService
from app.services.ai.test_case_service import TestCaseService
from app.utils.process_tracker import track, track_error


async def _run_ai_task(operation_id: str, *, complete_fn_name: str, service_factory) -> None:
    from app.db.models.async_operation import OperationStatus

    started = time.perf_counter()
    async with async_session_local() as session:
        op_repo = OperationRepository(session)
        try:
            operation = await op_repo.get_by_id(operation_id)
            if not operation:
                track_error("operation not found")
                return
            if operation.status == OperationStatus.CANCELLED.value:
                track("skipped (cancelled)")
                return

            track(
                f"start {operation.operation_type}",
                service=service_factory.__name__,
                handler=complete_fn_name,
                resource=f"{operation.resource_type}#{operation.resource_id}",
            )

            await op_repo.mark_running(operation)
            await session.commit()

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                track("cancelled before work started")
                return

            service = service_factory(session)
            complete_fn = getattr(service, complete_fn_name)
            result = await complete_fn(operation_id)

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                track("cancelled during work")
                return

            if result is None:
                await op_repo.mark_failed(
                    operation, f"Resource not found for {complete_fn_name}"
                )
                track_error(
                    f"failed {operation.operation_type}",
                    reason="resource not found",
                )
            else:
                await op_repo.mark_succeeded(operation)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                track(
                    f"done {operation.operation_type}",
                    status="succeeded",
                    ms=elapsed_ms,
                )

            await session.commit()
        except Exception as exc:
            await session.rollback()
            track_error(
                f"failed {complete_fn_name}",
                exc=exc,
            )
            try:
                operation = await op_repo.get_by_id(operation_id)
                if operation and operation.status != OperationStatus.CANCELLED.value:
                    await op_repo.mark_failed(operation, str(exc))
                    await session.commit()
            except Exception as mark_exc:
                await session.rollback()
                track_error(
                    "could not mark operation failed",
                    exc=mark_exc,
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
