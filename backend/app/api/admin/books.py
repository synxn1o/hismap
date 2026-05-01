from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_session
from app.crud import book as book_crud
from app.schemas.book import BookCreate, BookRead

router = APIRouter(prefix="/admin/books", tags=["admin-books"])


@router.post("", response_model=BookRead)
async def create_book(
    data: BookCreate,
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(get_current_admin),
):
    return await book_crud.create_book(db, data)
