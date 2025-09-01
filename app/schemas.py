from pydantic import BaseModel, Field
from datetime import datetime


# A base model for common company fields (no change here)
class CompanyBase(BaseModel):
    company_name: str
    local_folder_path: str | None = None
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
    company_name: str = Field(..., description="Name of the company.")
    local_folder_path: str | None = None
    total_usage_quota: int | None = None
    used_quota: int | None = None
    aws_bucket_name: str | None = None
    aws_bucket_region: str | None = None
    aws_access_key: str | None = None
    aws_secret_key: str | None = None


# Output model for a company (no change here)
class CompanyOut(CompanyBase):
    id: str
    created_at: datetime
    company_api_key: str

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
