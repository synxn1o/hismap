from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.security import ADMIN_PASSWORD_HASH, ADMIN_USERNAME, create_access_token, verify_password

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not ADMIN_PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Admin password not configured")
    if form_data.username != ADMIN_USERNAME or not verify_password(form_data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}
