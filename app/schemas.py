from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


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


# New schema for the registration API endpoint (no more API key or dates)
class CompanyRegister(BaseModel):
    company_name: str = Field(..., description='Name of the company.')
    total_usage_quota: int = 250 * 1024 * 1024
    used_quota: int = 0
    aws_bucket_name: str
    aws_bucket_region: str
    aws_access_key: str
    aws_secret_key: str


# Output model for a company (no change here)
class CompanyOut(CompanyBase):
    id: str
    created_at: datetime
    company_api_key: str
    base_url: str

    class Config:
        from_attributes = True


# Pydantic models for other endpoints (as before)
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


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: int

    class Config:
        from_attributes = True


class CurrentUser(BaseModel):
    username: str
    email: str
    is_active: bool


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
    file_name: str
    content_type: str
