import os

from fastapi import Header, HTTPException, status


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected_api_key = os.getenv("FINANCE_API_KEY", "dev-finance-api-key")

    if not x_api_key or x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
