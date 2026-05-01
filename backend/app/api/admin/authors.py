from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import author as author_crud
from app.schemas.author import AuthorCreate, AuthorRead

router = APIRouter(prefix="/admin/authors", tags=["admin-authors"])


@router.post("", response_model=AuthorRead)
async def create_author(
    data: AuthorCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await author_crud.create_author(db, data)
