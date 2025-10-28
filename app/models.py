from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from app.config import (
    DATABASE_HOST,
    DATABASE_NAME,
    DATABASE_PASSWORD,
    DATABASE_PORT,
    DATABASE_USER,
)

if not any(
    [DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT, DATABASE_NAME]
):
    raise ValueError('Database configuration are not set properly.')

# The database URL for SQLAlchemy
SQLALCHEMY_DATABASE_URL = (
    f'mariadb+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}'
    f'@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
)

# Create a SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for our models
Base = declarative_base()


class UploaderConfig(Base):
    __tablename__ = 'uploader_config'
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
    __tablename__ = 'companies'

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


class FileMeta(Base):
    __tablename__ = 'files_meta'

    id = Column(String(40), primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False, default=func.now())
    file_name = Column(String(255), nullable=True)
    file_size = Column(BigInteger, nullable=False, default=0)
    file_key = Column(String(255), nullable=False)
    file_txn_type = Column(SmallInteger, nullable=False, default=1)
    file_txn_meta = Column(String(255), nullable=True)

    # Foreign Key
    company_id = Column(String(40), ForeignKey('companies.id'))


# Dependency to get a database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
