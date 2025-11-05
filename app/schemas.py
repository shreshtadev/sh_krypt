from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# A base model for common company fields (no change here)
class CompanyBase(BaseModel):
    company_name: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    total_usage_quota: int | None = None
    used_quota: int | None = None
    aws_bucket_name: str | None = None
    aws_bucket_region: str | None = None
    aws_access_key: str | None = None
    aws_secret_key: str | None = None


class CompanyRegister(BaseModel):
    company_name: str = Field(..., description='Name of the company.')
    company_key_prefix: str


class CompanyOut(CompanyBase):
    id: str
    created_at: datetime
    company_api_key: str
    company_slug: str
    base_url: str

    class Config:
        from_attributes = True


class CompanyQuotaUpdate(BaseModel):
    used_quota: int | None = None
    file_txn_type: int = 1  # 1 for upload, 2 for delete


class FileMetaBase(BaseModel):
    file_name: str | None = None
    file_size: int
    file_key: str
    file_txn_type: int = 1
    file_txn_meta: str | None = None


class FileMetaOut(FileMetaBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploaderConfigBase(BaseModel):
    total_quota: int | None = None
    default_quota: int | None = None
    aws_bucket_name: str | None = None
    aws_bucket_region: str | None = None
    aws_access_key: str | None = None
    aws_secret_key: str | None = None
    is_active: int = 1


class UploaderConfigOut(UploaderConfigBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AWSConfig(BaseModel):
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str
    total_quota: int
    default_quota: int


class ErrorResponse(BaseModel):
    username: str
    status: int
    details: str


class PresignedURLRequest(BaseModel):
    loc_tag: str
    file_name: str
    content_type: str | None = None
    content_size: int


class FileDeleteRequest(BaseModel):
    loc_tag: str


class AdminClientRequest(BaseModel):
    client_id: str
    client_secret: str


class AdminClientResponse(BaseModel):
    client_id: str
    message: str | None = None


class HashData(BaseModel):
    data: str


class HashResult(BaseModel):
    original_data: str
    sha256_hash: str


# Pydantic model for verification input
class VerifyData(BaseModel):
    data: str
    known_hash: str


# Pydantic model for the verification result
class VerifyResult(BaseModel):
    match: bool
    status: Literal['Match', 'No Match']
