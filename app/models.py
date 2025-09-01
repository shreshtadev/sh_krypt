from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    Date,
    TIMESTAMP,
    ForeignKey,
    SmallInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .shbkp import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(40), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    company_name = Column(String(144), nullable=False)
    company_api_key = Column(String(255), nullable=False)
    local_folder_path = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    total_usage_quota = Column(BigInteger, nullable=True)
    used_quota = Column(BigInteger, nullable=True)
    aws_bucket_name = Column(String(64), nullable=True)
    aws_bucket_region = Column(String(50), nullable=True)
    aws_access_key = Column(String(25), nullable=True)
    aws_secret_key = Column(String(45), nullable=True)

    # Relationship to files_meta table
    files = relationship("FileMeta", back_populates="company")


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

    # Relationship to companies table
    company = relationship("Company", back_populates="files")
