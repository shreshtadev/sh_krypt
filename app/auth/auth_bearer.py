from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.auth_handler import decode_jwt


class JWTBearer(HTTPBearer):
    """Handles token extraction and validation for protected routes."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> str:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(
            request
        )
        if credentials:
            if not credentials.scheme == 'Bearer':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid authentication scheme.',
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid token or expired token.',
                )
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Invalid authorization code.',
            )

    def verify_jwt(self, jwtoken: str) -> bool:
        """Verifies the JWT token."""
        is_valid = decode_jwt(jwtoken)
        return is_valid is not None
