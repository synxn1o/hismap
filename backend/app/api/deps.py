from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
