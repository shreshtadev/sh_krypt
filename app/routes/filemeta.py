import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from types_boto3_s3 import S3Client

# Import the SQLAlchemy models and Pydantic schemas
from app.models import FileMeta, get_db
from app.schemas import CompanyOut, FileMetaBase, FileMetaOut
from app.shbkp import get_company_by_api_key, get_s3_client

router = APIRouter(prefix='/api/filemeta', tags=['filemeta'])


# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------


@router.post(
    '/',
    response_model=FileMetaOut,
    status_code=status.HTTP_201_CREATED,
)
async def insert_file_metadata(
    file_data: FileMetaBase,
    company: CompanyOut = Depends(get_company_by_api_key),
    db: Session = Depends(get_db),
):
    """
    Insert new file metadata.
    """
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Company ID not found'
        )

    # Generate a unique ID for the new file
    file_id = str(uuid.uuid4())

    # Create an instance of the ORM model from the Pydantic data
    db_file_meta = FileMeta(id=file_id, **file_data.model_dump())
    setattr(db_file_meta, 'company_id', company.id)

    db.add(db_file_meta)
    db.commit()
    db.refresh(db_file_meta)

    return db_file_meta


def get_folder_size(bucket_name: str, folder_prefix: str, s3_client: S3Client):
    """
    Calculates the total size of a folder in an S3 bucket in bytes.

    Args:
        bucket_name (str): The name of the S3 bucket.
        folder_prefix (str): The prefix of the folder (e.g., 'path/to/folder/').

    Returns:
        int: The total size of all objects in the folder in bytes.
    """
    paginator = s3_client.get_paginator('list_objects_v2')

    # Use the paginator to list all objects with the specified prefix
    pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)

    total_size = 0
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                total_size += obj['Size']  # type: ignore

    return total_size


def human_readable_size(size_bytes):
    """
    Converts a size in bytes to a human-readable string.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f'{size_bytes:3.1f} {unit}'
        size_bytes /= 1024.0
    return f'{size_bytes:.1f} PB'


@router.get('/folder/size', status_code=status.HTTP_200_OK)
async def find_folder_size(
    request: Request,
    company: CompanyOut = Depends(get_company_by_api_key),
    s3Client: S3Client = Depends(get_s3_client),
):
    loc_tag = request.query_params.get('loc_tag')
    folder_path = f'{company.company_slug}/{loc_tag}/'
    total_folder_size = get_folder_size(
        str(company.aws_bucket_name), folder_path, s3Client
    )
    total_folder_size_hr = human_readable_size(total_folder_size)
    folder_info = dict()
    folder_info['folder_path'] = folder_path
    folder_info['total_size'] = total_folder_size
    folder_info['total_size_readable'] = total_folder_size_hr
    return JSONResponse(content=folder_info)
