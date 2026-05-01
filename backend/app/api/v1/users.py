from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.core.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(db: AsyncSession = Depends(get_db)):
    return JSONResponse(content={"message": "User registered successfully"})
