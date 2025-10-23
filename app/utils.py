import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from fastapi import (
    BackgroundTasks,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import ALGORITHM, SECRET_KEY
from app.models import Company

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/auth/api/token")
pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')


def read_key_file(filepath: str) -> str | None:
    try:
        file_content = Path(filepath).read_text(encoding='utf-8')
        return file_content
    except FileNotFoundError:
        logging.error(f"File '{filepath}' was not found.")
    except Exception as e:
        logging.error(f'An error occurred: {e}')


async def get_token_from_all_sources(
    request: Request,
    authorization: str,
):
    token = None

    # 1. Try to get it from the header (the standard way)
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]

    # 2. If not found, try from the cookie
    if not token:
        token = request.cookies.get('access_token')

    # 3. If still not found, try from a URL query parameter
    if not token:
        token = request.query_params.get('access_token')
    if not token:
        token = request.session.get('access_token')

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated. No valid token found.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return token


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    if SECRET_KEY is None or SECRET_KEY == '':
        raise JWTError('NO SECRET KEY FOUND')
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_token(token: str):
    username = ''
    expires_at = 0
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = str(payload.get('sub'))
        expires_at: int = int(str(payload.get('exp')))
        curr_time = round(datetime.now().timestamp())
        is_valid = username is not None and (curr_time < expires_at)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='UnAuthorized'
        )
    return (is_valid, username, expires_at)


def get_bucket_size(s3_client, bucket_name):
    """
    Calculates the total size of all objects in an S3 bucket.
    """
    total_size = 0
    try:
        # Use a paginator to handle large numbers of objects
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)

        # Iterate through all pages of objects
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    total_size += obj['Size']

        # Convert bytes to megabytes for a more readable result
        total_size_mb = total_size / (1024 * 1024)
        return total_size_mb

    except Exception as e:
        print(f'An error occurred: {e}')
        return None


def get_api_key_file(
    company_api_key: str, base_url: str, background_tasks: BackgroundTasks
):
    """
    Dynamically creates and serves an apikey.lic file for download.
    """
    # 1. Define the content for the apikey.lic file
    file_content = f"""API_KEY={company_api_key}
API_BASE_URL={base_url}
"""

    # 2. Use a temporary file to hold the content
    with tempfile.NamedTemporaryFile(
        mode='w+', delete=False, suffix='.lic'
    ) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    # 3. Schedule file removal after response is sent
    background_tasks.add_task(os.remove, temp_file_path)

    # 4. Use FileResponse to send the file to the user
    return FileResponse(
        path=temp_file_path, media_type='text/plain', filename='apikey.lic'
    )


def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against a stored hash."""
    return pwd_context.verify(password, hashed_password)


def get_time_of_day():
    current_time = datetime.now()
    hour = current_time.hour

    if 5 <= hour < 12:
        return 'Morning'
    elif hour == 12:
        return 'Noon'
    elif 12 < hour < 18:
        return 'Afternoon'
    elif 18 <= hour < 22:
        return 'Evening'
    else:
        return 'Night'


def get_s3_client(company: Company):
    aws_access_key, aws_secret_key, aws_bucket_region = company
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_bucket_region,
    )
    return s3_client
