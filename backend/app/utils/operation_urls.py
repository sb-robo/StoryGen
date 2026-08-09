from app.db.models.async_operation import OperationType

# Maps operation_type → API router prefix for status/result polling.
# Each resource's own router owns the trigger, status/result tracking, and
# CRUD for instances of itself (e.g. sub-feature generation is triggered
# from and tracked on /sub-features, not /features).
OPERATION_ROUTE_PREFIX: dict[str, str] = {
    OperationType.BRD_UPLOAD.value: "brds",
    OperationType.BRD_REPARSE.value: "brds",
    OperationType.FEATURE_EXTRACTION.value: "features",
    OperationType.SUB_FEATURE_GENERATION.value: "sub-features",
    OperationType.STORY_GENERATION.value: "stories",
    OperationType.STORY_POINT_ESTIMATION.value: "stories",
    OperationType.TEST_CASE_GENERATION.value: "test-cases",
}

BRD_OPERATION_TYPES = {
    OperationType.BRD_UPLOAD.value,
    OperationType.BRD_REPARSE.value,
}
FEATURE_OPERATION_TYPES = {OperationType.FEATURE_EXTRACTION.value}
SUB_FEATURE_OPERATION_TYPES = {OperationType.SUB_FEATURE_GENERATION.value}
STORY_OPERATION_TYPES = {
    OperationType.STORY_GENERATION.value,
    OperationType.STORY_POINT_ESTIMATION.value,
}
TEST_CASE_OPERATION_TYPES = {OperationType.TEST_CASE_GENERATION.value}


def operation_status_url(operation_id: str, operation_type: str) -> str:
    prefix = OPERATION_ROUTE_PREFIX[operation_type]
    return f"/api/v1/{prefix}/status/{operation_id}"


def operation_result_url(operation_id: str, operation_type: str) -> str:
    prefix = OPERATION_ROUTE_PREFIX[operation_type]
    return f"/api/v1/{prefix}/result/{operation_id}"
