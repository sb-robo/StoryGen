from fastapi import APIRouter

from app.api.v1.routers import auth, brds, features, operations, stories, sub_features, users

router = APIRouter()


router.include_router(users.router, prefix="/users", tags=["User"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(brds.router, prefix="/brds", tags=["BRD"])
router.include_router(features.router, prefix="/features", tags=["Features"])
router.include_router(sub_features.router, prefix="/sub-features", tags=["Sub-features"])
router.include_router(stories.router, prefix="/stories", tags=["Stories"])
router.include_router(operations.router, prefix="/operations", tags=["Operations"])
