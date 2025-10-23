from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    SmallInteger,
    String,
)
from sqlalchemy.sql import func

from .shbkp import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(40), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    last_login_at = Column(TIMESTAMP, nullable=True, default=func.now())

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class UploaderConfig(Base):
    __tablename__ = "uploader_config"
    id = Column(String(40), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    aws_bucket_name = Column(String(64), nullable=False)
    aws_bucket_region = Column(String(50), nullable=False)
    aws_access_key = Column(String(25), nullable=False)
    aws_secret_key = Column(String(45), nullable=False)
    total_quota = Column(BigInteger, nullable=True, default=(5 * 1024 * 1024 * 1024))
    default_quota = Column(BigInteger, nullable=True, default=(250 * 1024 * 1024))
    is_active = Column(
        SmallInteger, nullable=False, default=0, index=True
    )  # 0 - Active, 1 - InActive


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(40), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    company_name = Column(String(144), nullable=False)
    company_slug = Column(String(255), nullable=False)
    company_api_key = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    total_usage_quota = Column(BigInteger, nullable=True)
    used_quota = Column(BigInteger, nullable=True, default=0)
    aws_bucket_name = Column(String(64), nullable=True)
    aws_bucket_region = Column(String(50), nullable=True)
    aws_access_key = Column(String(25), nullable=True)
    aws_secret_key = Column(String(45), nullable=True)
    base_url = Column(String(255), nullable=True)


class RegistrationToken(Base):
    __tablename__ = "registration_tokens"
    token = Column(String(255), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
    company_id = Column(String(40), ForeignKey("companies.id"), nullable=True)


class FileMeta(Base):
    __tablename__ = "files_meta"

    id = Column(String(40), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    file_name = Column(String(255), nullable=True)
    file_size = Column(BigInteger, nullable=False, default=0)
    file_key = Column(String(255), nullable=False)
    file_txn_type = Column(SmallInteger, nullable=False, default=1)
    file_txn_meta = Column(String(255), nullable=True)

    # Foreign Key
    company_id = Column(String(40), ForeignKey("companies.id"))
