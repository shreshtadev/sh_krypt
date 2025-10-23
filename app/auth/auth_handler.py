import time

from jose import JWTError, jwt

from app.config import JWT_ALGORITHM, PRIVATE_KEY, PUBLIC_KEY
from app.utils import read_key_file


def sign_jwt(user_id: str) -> str | None:
    """Signs a JWT token with the private key."""
    payload = {
        'user_id': user_id,
        'expires': round(time.time() + 600),  # Token expires in 10 minutes
    }
    read_private_key = read_key_file(PRIVATE_KEY)
    if not read_private_key:
        return None
    return jwt.encode(payload, read_private_key, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    """Decodes a JWT token with the public key."""
    read_public_key = read_key_file(PUBLIC_KEY)
    if not read_public_key:
        return None
    try:
        decoded_token = jwt.decode(token, read_public_key, algorithms=[JWT_ALGORITHM])
        expires = decoded_token.get('expires')
        # Explicitly check for None before comparison
        if expires is None:
            # Token does not have an expiration claim, reject it or handle as desired.
            return None

        # Now we know 'expires' is not None and can safely compare it.
        if expires >= time.time():
            return decoded_token

    except JWTError:
        # The token is invalid (e.g., malformed, wrong algorithm, invalid signature)
        return None

    # Return None for expired tokens
    return None
