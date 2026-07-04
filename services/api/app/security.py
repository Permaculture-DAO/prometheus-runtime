import secrets

from fastapi import Header, HTTPException, status
from .settings import Settings

def require_write_key(settings: Settings):
    async def dependency(x_api_key: str | None = Header(default=None)):
        if not settings.write_api_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="write operations disabled: WRITE_API_KEY not configured")
        if not x_api_key or not secrets.compare_digest(x_api_key, settings.write_api_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")
        return True
    return dependency
