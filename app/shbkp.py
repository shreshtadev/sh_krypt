from typing import Annotated

from boto3 import client
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models import Company, get_db
from app.schemas import CompanyOut

# You would typically get these from a .env file
# (e.g., using python-dotenv library)


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
