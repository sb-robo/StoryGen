from fastapi import APIRouter

from app.api.v1.routers import auth, brds, operations, users

router = APIRouter()


router.include_router(users.router, prefix="/users", tags=["User"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(brds.router, prefix="/brds", tags=["BRD"])
router.include_router(operations.router, prefix="/operations", tags=["Operations"])
