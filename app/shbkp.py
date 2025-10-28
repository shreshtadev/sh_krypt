from datetime import datetime, timedelta, timezone
from typing import Annotated

from boto3 import client
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose.jwt import decode, encode

# You would typically get these from a .env file
# (e.g., using python-dotenv library)
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import ALGORITHM, PRIVATE_KEY_FILE_PATH, PUBLIC_KEY_FILE_PATH
from app.models import AdminClient, Company, get_db
from app.schemas import AdminClientResponse, CompanyOut

pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/admin/auth/token')


def hash_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_secret(secret: str, hashed_secret: str) -> bool:
    return pwd_context.verify(secret, hashed_secret)


def get_company_by_api_key(
    company_api_key: Annotated[str | None, Header(alias='X-Company-Api-Key')],
    db: Session = Depends(get_db),
):
    if not company_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Company API key header is required',
        )
    company = (
        db.query(Company).filter(Company.company_api_key == company_api_key).first()
    )

    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Company not found'
        )

    yield company


def get_s3_client(company: CompanyOut = Depends(get_company_by_api_key)):
    aws_access_key = company.aws_access_key
    aws_secret_key = company.aws_secret_key
    aws_bucket_region = company.aws_bucket_region
    s3_client = client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_bucket_region,
    )
    yield s3_client


def create_client(
    client_id: str, client_secret: str, db: Session
) -> AdminClientResponse | None:
    client: AdminClient = (
        db.query(AdminClient).filter(AdminClient.client_id == client_id).first()
    )
    if client:
        return None
    hashed = hash_secret(client_secret)
    new_client = AdminClient(client_id=client_id, hashed_secret=hashed)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return AdminClientResponse(client_id=str(new_client.client_id))


def authenticate_client(
    client_id: str, client_secret: str, db: Session
) -> AdminClientResponse | None:
    client = db.query(AdminClient).filter(AdminClient.client_id == client_id).first()
    if not client or not verify_secret(client_secret, str(client.hashed_secret)):
        return None
    return AdminClientResponse(client_id=str(client.client_id))


def read_key(file_path: str):
    READ_KEY = ''
    with open(file_path, 'rb') as f:
        READ_KEY = f.read()
    return READ_KEY


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({'exp': expire})
    return encode(to_encode, read_key(PRIVATE_KEY_FILE_PATH), algorithm=ALGORITHM)


def get_current_client(db: Session, token: str = Depends(oauth2_scheme)):
    try:
        payload = decode(token, read_key(PUBLIC_KEY_FILE_PATH), algorithms=[ALGORITHM])
        # Extract claims
        exp = payload.get('exp')
        role = payload.get('role')
        client_id = payload.get('sub')

        # Check expiration
        if exp is None and datetime.fromtimestamp(
            float(str(exp)), tz=timezone.utc
        ) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired'
            )

        # Check role
        if role != 'client':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail='Invalid role'
            )

        # Check client existence in DB
        client = (
            db.query(AdminClient).filter(AdminClient.client_id == client_id).first()
        )
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Unknown client'
            )

        return client_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token'
        )
