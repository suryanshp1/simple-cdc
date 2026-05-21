"""
SimpleCDC — API authentication dependency.

Token-based auth via the ``X-API-Token`` header.
"""

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_token(x_api_token: str | None = Header(default=None)) -> bool:
    """
    FastAPI dependency that validates the ``X-API-Token`` header.

    Raises:
        HTTPException 401 if the token is missing or does not match.

    Returns:
        ``True`` on successful verification.
    """
    if x_api_token is None or x_api_token != settings.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )
    return True
