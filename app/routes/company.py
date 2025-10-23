import secrets
import string
import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from boto3 import client
from botocore.exceptions import ClientError
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    status,
)
from itsdangerous.url_safe import URLSafeTimedSerializer
from slugify import slugify
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

# Import the SQLAlchemy models and Pydantic schemas
from app.config import SECRET_KEY
from app.models import Company, RegistrationToken, UploaderConfig
from app.schemas import (
    CompanyOut,
    CompanyQuotaUpdate,
    CompanyRegister,
    PresignedURLRequest,
)
from app.shbkp import get_db
from app.utils import (
    get_api_key_file,
    get_bucket_size,
)

router = APIRouter(prefix='/companies', tags=['company'])

# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------


# 1. API to find a company by its API key
@router.get('/api/by-api-key', response_model=CompanyOut)
async def find_company_by_api_key(
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    db: Session = Depends(get_db),
):
    """
    Find a company by its unique API key.
    """
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

    return company


@router.patch('/api/quota', response_model=CompanyOut)
async def update_company_quota(
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    quota_update: CompanyQuotaUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the total and/or used quota for a company.
    """
    # Optional: Check if the company_id, company_api_key exists
    if not company_api_key:
        raise HTTPException(
            status_code=400, detail='Company API key header is required'
        )
    company = (
        db.query(Company).filter(Company.company_api_key == company_api_key).first()
    )

    if not company:
        raise HTTPException(status_code=404, detail='Company not found')

    # Update the fields if they are provided in the request body

    if quota_update.used_quota is not None:
        if quota_update.file_txn_type == 1:
            setattr(company, 'used_quota', company.used_quota + quota_update.used_quota)
        else:
            setattr(company, 'used_quota', company.used_quota - quota_update.used_quota)

    db.commit()
    db.refresh(company)

    return company


@router.post('/api/generate-link')
async def generate_link(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Should be an authenticated request.',
            headers={'WWW-Authenticate': 'bearer'},
        )

    # Generate a new token
    new_token = URLSafeTimedSerializer(SECRET_KEY, str(uuid.uuid4())).dumps(
        str(uuid.uuid1()), salt=str(uuid.uuid1())
    )
    expires_at = datetime.now() + timedelta(minutes=15)
    # Create a new RegistrationToken entry in the database
    db_token = RegistrationToken(
        token=new_token,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    link = f'{request.base_url}companies/register?token={new_token}'
    return {'message': 'Link generated successfully!', 'link': link}


async def register_company(
    request: Request,
    company_data: CompanyRegister,
    token: str,
    db: Session,
):
    """
    Registers a new company.
    The company_api_key, start_date, and end_date are auto-generated.
    - **company_name**: Name of the company (must be unique).
    """
    # Check if token is still valid
    validated_token = (
        db.query(RegistrationToken)
        .filter(
            and_(
                RegistrationToken.token == token,
                RegistrationToken.expires_at > datetime.now(),
                RegistrationToken.company_id.is_(None),
            )
        )
        .first()
    )
    if not validated_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Not a valid registration link',
        )
    # 1. Check for existing company name
    company_name_slug = slugify(company_data.company_name)
    existing_company_name = (
        db.query(Company)
        .filter(
            or_(
                Company.company_name == company_data.company_name,
                Company.company_slug == company_name_slug,
            )
        )
        .first()
    )
    if existing_company_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Company name already exists'
        )

    # 2. Autogenerate a unique API key
    token_chars = string.ascii_letters + string.digits
    api_key_suffix = ''.join(secrets.choice(token_chars) for _ in range(32))
    generated_api_key = f'shbkp_{api_key_suffix}'

    # 3. Check for uniqueness of the generated API key (extremely unlikely, but good practice)
    existing_api_key = (
        db.query(Company)
        .filter(
            Company.company_api_key == generated_api_key,
        )
        .first()
    )
    if existing_api_key:
        # In a real app, you might want to retry generation
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not generate a unique API key. Please try again.',
        )

    # 4. Set the start and end dates
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=365)  # A simple way to get a year from today

    # 5. Generate a unique ID
    company_id = str(uuid.uuid4())
    base_url_config = request.base_url

    # 6. Create an instance of the ORM model from the Pydantic data
    db_company = Company(
        id=company_id,
        company_slug=company_name_slug,
        company_api_key=generated_api_key,
        start_date=start_date,
        end_date=end_date,
        base_url=base_url_config,
        **company_data.model_dump(),
    )

    # 7. Add and commit to the database
    db.add(db_company)
    db.flush()
    db.refresh(db_company)
    setattr(validated_token, 'company_id', db_company.id)
    db.add(validated_token)
    db.commit()
    db.refresh(validated_token)

    return {
        'company_api_key': db_company.company_api_key,
        'api_base_url': db_company.base_url,
    }


@router.post(
    '/api/register',
    response_model=CompanyOut,
    status_code=status.HTTP_201_CREATED,
)
async def handleRegistration(
    request: Request,
    background_tasks: BackgroundTasks,
    token: str = Form(),
    companyName: str = Form(max_length=65),
    db: Session = Depends(get_db),
):
    """
    Registers a new company and downloads a file that can be shared
    """
    get_quota_config = db.query(UploaderConfig).filter_by(is_active=True).first()
    if not get_quota_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='No active uploader configuration found.',
        )
    s3_client = client(
        's3',
        aws_access_key_id=get_quota_config.aws_access_key,
        aws_secret_access_key=get_quota_config.aws_secret_key,
        region_name=get_quota_config.aws_bucket_region,
    )
    total_content_size = get_bucket_size(
        s3_client=s3_client, bucket_name=get_quota_config.aws_bucket_name
    )
    if total_content_size is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Please check for the correct configuration',
        )
    company_to_register = CompanyRegister(
        company_name=companyName,
        aws_access_key=str(get_quota_config.aws_access_key),
        aws_secret_key=str(get_quota_config.aws_secret_key),
        aws_bucket_name=str(get_quota_config.aws_bucket_name),
        aws_bucket_region=str(get_quota_config.aws_bucket_region),
    )
    # Register the company using the API logic
    registered_company = await register_company(
        request=request, company_data=company_to_register, db=db, token=token
    )
    downloadable_key = get_api_key_file(
        company_api_key=str(registered_company.get('company_api_key')),
        base_url=str(registered_company.get('api_base_url')),
        background_tasks=background_tasks,
    )
    return downloadable_key


@router.post('/generate-presigned-url/')
async def generate_presigned_upload_url(
    request: PresignedURLRequest,
    s3_client,
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    db: Session = Depends(get_db),
):
    """
    Generates a presigned URL for uploading a file to S3.
    """
    try:
        found_company: Company = await find_company_by_api_key(
            company_api_key=company_api_key, db=db
        )
        response = s3_client.generate_presigned_post(
            Bucket=found_company.aws_bucket_name,
            Key=request.file_name,
            Fields={'Content-Type': request.content_type},
            Conditions=[{'Content-Type': request.content_type}],
            ExpiresIn=3600,  # URL expires in 1 hour (3600 seconds)
        )
        return response
    except ClientError as e:
        raise HTTPException(
            status_code=500, detail=f'Error generating presigned URL: {e}'
        )


@router.get('/generate-presigned-download-url/{object_key}')
async def generate_presigned_download_url(
    object_key: str, s3_client, company_api_key, db: Session = Depends(get_db)
):
    """
    Generates a presigned URL for downloading a file from S3.
    """
    try:
        found_company = await find_company_by_api_key(
            company_api_key=company_api_key, db=db
        )
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': found_company.aws_bucket_name, 'Key': object_key},
            ExpiresIn=3600,  # URL expires in 1 hour (3600 seconds)
        )
        return {'url': url}
    except ClientError as e:
        raise HTTPException(
            status_code=500, detail=f'Error generating presigned URL: {e}'
        )
