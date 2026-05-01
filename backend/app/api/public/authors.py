from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.crud import author as author_crud
from app.schemas.author import AuthorDetail, AuthorRead

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=list[AuthorRead])
async def list_authors(
    dynasty: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    return await author_crud.get_authors(db, dynasty=dynasty)


@router.get("/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: int, db: AsyncSession = Depends(get_session)):
    author = await author_crud.get_author(db, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author
