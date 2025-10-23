import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.auth_bearer import JWTBearer
from app.auth.auth_handler import decode_jwt, sign_jwt
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import User
from app.schemas import (
    CurrentUser,
    ErrorResponse,
    LoginResponse,
    UserCreate,
    UserResponse,
)
from app.shbkp import get_db
from app.utils import (
    hash_password,
    verify_password,
)

router = APIRouter(prefix='/admin/auth', tags=['auth'])


@router.post('/api/token')
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # Retrieve user from the database by username
    user = (
        db.query(User)
        .filter(and_(User.email == form_data.username, User.is_active))
        .first()
    )

    if not user or not verify_password(form_data.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = sign_jwt(str(user.username))
    # Update last_login_at
    setattr(user, 'last_login_at', datetime.now())
    db.commit()
    login_response = ErrorResponse(
        username=str(user.email), details='UnAuthorized', status=401
    )
    if access_token:
        login_response = LoginResponse(
            access_token=access_token,
            token_type='bearer',
            expires_at=int(access_token_expires.total_seconds()),
        )
    return login_response


@router.post(
    '/api/register',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_admin(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user.
    Hashes the password using argon2 before storing it in the database.
    """
    try:
        # Hash the password
        hashed_password = hash_password(user.password)

        # Create a new user instance
        new_user = User(
            id=uuid.uuid4(),
            username=user.username,
            email=user.email,
            password_hash=hashed_password,
            is_active=False,  # Example: set to active on registration
        )

        # Add to the session and commit
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Username or email already registered.',
        )


@router.get('/api/users/me')
async def get_current_user(
    request: Request, token: str = Depends(JWTBearer()), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = decode_jwt(token)
        if not payload:
            return ErrorResponse(username='', status=401, details='Invalid Token')
        username: str = str(payload.get('user_id'))
        expires_at: int = int(str(payload.get('expires')))
        curr_time = round(datetime.now().timestamp())
        if username is None or (curr_time > expires_at):
            return ErrorResponse(username='', status=500, details='JWT Error')
        user = (
            db.query(User)
            .filter(
                and_(
                    User.username == username,
                    User.is_active,
                )
            )
            .first()
        )
        if user is None:
            raise credentials_exception
        current_user = CurrentUser(
            username=str(user.username),
            email=str(user.email),
            is_active=bool(user.is_active),
        )
        return current_user
    except JWTError:
        return ErrorResponse(username='', status=500, details='JWT Error')
    except Exception:
        return ErrorResponse(username='', status=500, details='Internal Server Error')
