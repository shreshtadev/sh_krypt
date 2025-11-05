import mimetypes
import uuid
from datetime import datetime

from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from slugify import slugify
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from types_boto3_s3 import S3Client

from app.logging import logger
from app.models import Company, UploaderConfig, get_db
from app.schemas import (
    CompanyOut,
    CompanyQuotaUpdate,
    CompanyRegister,
    FileDeleteRequest,
    PresignedURLRequest,
)
from app.shbkp import (
    get_company_by_api_key,
    get_s3_client,
    hash_secret,
    oauth2_scheme,
)

router = APIRouter(prefix='/api/companies', tags=['company'])
# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------


def is_valid_company(company_name: str, db: Session):
    found_company_exists = (
        select(Company.id)
        .where(
            and_(
                Company.company_name == company_name,
                Company.company_slug == slugify(company_name),
            )
        )
        .limit(1)
    )
    found_company = db.scalar(found_company_exists)
    return found_company is not None


@router.post('/register')
async def register_company(
    request: Request,
    registration_request: CompanyRegister,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    found_company = is_valid_company(registration_request.company_name, db)
    if not found_company:
        err = dict()
        err['detail'] = 'Company already exists'
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=err)
    company_api_key = f'{registration_request.company_key_prefix}_{hash_secret(str(uuid.uuid4()).replace("-", ""))}'
    current_date = datetime.now()
    end_date = current_date + relativedelta(years=1)
    found_aws_config = (
        db.query(UploaderConfig).where(UploaderConfig.is_active == 1).first()
    )
    if not found_aws_config:
        err = dict()
        err['detail'] = 'Active AWS Config is not found'
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=err)
    company = Company(
        id=str(uuid.uuid4()),
        company_name=registration_request.company_name,
        company_slug=slugify(registration_request.company_name),
        company_api_key=company_api_key,
        total_usage_quota=found_aws_config.default_quota,
        usage_quota=0,
        start_date=current_date,
        end_date=end_date,
        aws_bucket_name=found_aws_config.aws_bucket_name,
        aws_bucket_region=found_aws_config.aws_bucket_region,
        aws_access_key=found_aws_config.aws_access_key,
        aws_secret_key=found_aws_config.aws_secret_key,
        base_url=request.base_url,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return JSONResponse(
        content={'company_api_key': company_api_key, 'base_url': request.base_url},
        status_code=status.HTTP_201_CREATED,
    )


# 1. API to find a company by its API key
@router.get('/by-api-key', response_model=CompanyOut)
async def find_company_by_api_key(
    company: CompanyOut = Depends(get_company_by_api_key),
):
    """
    Find a company by its unique API key.
    """
    return company


@router.get('/quota/is-available')
async def is_company_quota_available(
    company: CompanyOut = Depends(get_company_by_api_key),
):
    if not company.total_usage_quota or not company.used_quota:
        err = dict()
        err['detail'] = 'Company quota is invalid'
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=err,
        )
    return {
        'is_available': company.total_usage_quota > company.used_quota,
        'usage_quota': company.used_quota,
    }


@router.patch('/quota', response_model=CompanyOut)
async def update_company_quota(
    quota_update: CompanyQuotaUpdate,
    company: CompanyOut = Depends(get_company_by_api_key),
    db: Session = Depends(get_db),
):
    """
    Update the total and/or used quota for a company.
    """
    # Optional: Check if the company_id, company_api_key exists

    if not company.total_usage_quota and not company.used_quota:
        err = dict()
        err['detail'] = 'Company quota is invalid'
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=err,
        )
    # Update the fields if they are provided in the request body

    if quota_update.used_quota is not None:
        if quota_update.file_txn_type == 1:
            setattr(
                company,
                'used_quota',
                int(str(company.used_quota)) + quota_update.used_quota,
            )
        else:
            setattr(
                company,
                'used_quota',
                quota_update.used_quota,
            )
    setattr(company, 'updated_at', datetime.now())
    db.commit()
    db.refresh(company)

    return company


def is_s3_folder_empty(bucket_name: str, folder_prefix: str, s3: S3Client) -> bool:
    """
    Checks if an S3 "folder" (prefix) contains no files.

    Args:
        bucket_name: The name of the S3 bucket.
        folder_prefix: The prefix representing the S3 "folder".
                       It should typically end with a '/'.

    Returns:
        True if the folder is empty, False otherwise.
    """

    # Ensure the prefix ends with a '/' for consistent "folder" behavior
    if not folder_prefix.endswith('/'):
        folder_prefix += '/'

    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix=folder_prefix,
        MaxKeys=1,  # We only need to know if there's at least one object
    )

    # If 'Contents' is not in the response, or if it's empty, the folder is considered empty.
    # Note: S3 console creates zero-byte objects for "folders", but direct object creation
    # doesn't always create these. Checking for 'Contents' is the reliable way to find actual files.
    return 'Contents' not in response


def delete_s3_folder_contents(
    s3_client: S3Client, bucket_name: str, folder_prefix: str
):
    """
    Deletes all objects under a specified prefix (folder) in an S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        folder_prefix (str): The prefix representing the folder to delete contents from.
                             Ensure it ends with a '/' to target only objects within the "folder".
    """
    # Ensure the folder prefix ends with a slash
    if not folder_prefix.endswith('/'):
        folder_prefix += '/'

    # Paginate through the objects and create the list using a list comprehension
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)

    for page in pages:
        if 'Contents' in page:
            objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]  # type: ignore
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete},  # type: ignore
            )
            print(f'Deleted {len(objects_to_delete)} objects.')

    print(
        f"All objects under '{folder_prefix}' have been deleted from '{bucket_name}'."
    )


@router.post('/delete/files')
async def delete_files(
    request: FileDeleteRequest,
    company: CompanyOut = Depends(get_company_by_api_key),
    s3_client=Depends(get_s3_client),
):
    """
    Deletes files from S3.
    """
    try:
        if not company:
            err = dict()
            err['detail'] = 'Company not found'
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=err)
        is_folder_empty = is_s3_folder_empty(
            str(company.aws_bucket_name),
            f'{company.company_slug}/{request.loc_tag}',
            s3_client,
        )
        if is_folder_empty:
            err = dict()
            err['detail'] = 'Folder is empty'
            return JSONResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, content=err)
        delete_s3_folder_contents(
            s3_client,
            str(company.aws_bucket_name),
            f'{company.company_slug}/{request.loc_tag}',
        )
        return Response(
            status_code=status.HTTP_200_OK, content='Files deleted successfully'
        )
    except Exception:
        err = dict()
        err['detail'] = 'Something Went Wrong'
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=err,
        )


@router.post('/generate/presigned/url/upload')
async def generate_presigned_upload_url(
    request: PresignedURLRequest,
    company: CompanyOut = Depends(get_company_by_api_key),
    s3_client: S3Client = Depends(get_s3_client),
):
    """
    Generates a presigned URL for uploading a file to S3.
    """
    if not company:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    filetype, _ = mimetypes.guess_type(request.file_name)
    try:
        s3_client.head_object(
            Bucket=str(company.aws_bucket_name),
            Key=f'{company.company_slug}/{request.loc_tag}/{request.file_name}',
        )
        logger.info(f'File found - {request.file_name}')
        error = dict()
        error['detail'] = f'File found - {request.file_name}'
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error,
        )
    except ClientError:
        logger.info(f'File not found - {request.file_name}')
        pass
    try:
        return s3_client.generate_presigned_post(
            Bucket=str(company.aws_bucket_name),
            Key=f'{company.company_slug}/{request.loc_tag}/{request.file_name}',
            Fields={'Content-Type': filetype},
            Conditions=[
                {'Content-Type': filetype},
                ['content-length-range', 1024, request.content_size],
            ],
            ExpiresIn=3600,
        )

    except ClientError as e:
        return HTTPException(
            status_code=500, detail=f'Error generating presigned URL: {e}'
        )


@router.get('/generate/presigned/url/download')
async def generate_presigned_download_url(
    request: Request,
    company: CompanyOut = Depends(get_company_by_api_key),
    s3_client: S3Client = Depends(get_s3_client),
):
    """
    Generates a presigned URL for downloading a file from S3.
    """
    try:
        object_key = request.path_params.get('object_key')
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': company.aws_bucket_name, 'Key': object_key},
            ExpiresIn=3600,
        )
        return {'url': url}
    except ClientError as e:
        raise HTTPException(
            status_code=500, detail=f'Error generating presigned URL: {e}'
        )
