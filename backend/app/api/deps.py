from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def require_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if not settings.admin_api_token:
        raise HTTPException(status_code=500, detail="ADMIN_API_TOKEN is not configured")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")
    if credentials.credentials != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials
