from fastapi import APIRouter
from app.api.v1.routers import users, auth

router = APIRouter()


router.include_router(users.router, prefix="users", tags=["User"])
router.include_router(auth.router, prefix="auth", tags=["Auth"])
