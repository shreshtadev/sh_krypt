from fastapi import FastAPI, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import uuid
import secrets
import string
from datetime import date, timedelta
from typing import Annotated

# Import the SQLAlchemy models and Pydantic schemas
from . import models, schemas
from .shbkp import engine, get_db

# Create the database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Company and File Metadata API", version="1.0.0")

# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------


# 1. API to find a company by its API key
@app.get("/companies/by-api-key", response_model=schemas.CompanyOut)
async def find_company_by_api_key(
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    db: Session = Depends(get_db),
):
    """
    Find a company by its unique API key.
    """
    if not company_api_key:
        raise HTTPException(
            status_code=400, detail="Company API key header is required"
        )
    company = (
        db.query(models.Company)
        .filter(models.Company.company_api_key == company_api_key)
        .first()
    )

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


# 2. API to insert new file metadata
@app.post(
    "/filemeta", response_model=schemas.FileMetaOut, status_code=status.HTTP_201_CREATED
)
async def insert_file_metadata(
    file_data: schemas.FileMetaBase,
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    db: Session = Depends(get_db),
):
    """
    Insert new file metadata.
    """
    # Optional: Check if the company_id, company_api_key exists
    if not company_api_key:
        raise HTTPException(
            status_code=400, detail="Company API key header is required"
        )
    company = (
        db.query(models.Company)
        .filter(models.Company.company_api_key == company_api_key)
        .first()
    )
    if not company:
        raise HTTPException(status_code=400, detail="Company ID not found")

    # Generate a unique ID for the new file
    file_id = str(uuid.uuid4())

    # Create an instance of the ORM model from the Pydantic data
    db_file_meta = models.FileMeta(id=file_id, **file_data.model_dump())
    db_file_meta.company_id = company.id

    db.add(db_file_meta)
    db.commit()
    db.refresh(db_file_meta)

    return db_file_meta


# 3. API to update a company's quota
@app.patch("/companies/quota", response_model=schemas.CompanyOut)
async def update_company_quota(
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    quota_update: schemas.CompanyQuotaUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the total and/or used quota for a company.
    """
    # Optional: Check if the company_id, company_api_key exists
    if not company_api_key:
        raise HTTPException(
            status_code=400, detail="Company API key header is required"
        )
    company = (
        db.query(models.Company)
        .filter(models.Company.company_api_key == company_api_key)
        .first()
    )

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Update the fields if they are provided in the request body

    if quota_update.used_quota is not None:
        if quota_update.file_txn_type == 1:
            setattr(company, "used_quota", company.used_quota + quota_update.used_quota)
        else:
            setattr(company, "used_quota", company.used_quota - quota_update.used_quota)

    db.commit()
    db.refresh(company)

    return company


@app.post(
    "/register/company",
    response_model=schemas.CompanyOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    company_data: schemas.CompanyRegister, db: Session = Depends(get_db)
):
    """
    Registers a new company.
    The company_api_key, start_date, and end_date are auto-generated.
    - **company_name**: Name of the company (must be unique).
    """
    # 1. Check for existing company name
    existing_company_name = (
        db.query(models.Company)
        .filter(models.Company.company_name == company_data.company_name)
        .first()
    )
    if existing_company_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Company name already exists"
        )

    # 2. Autogenerate a unique API key
    token_chars = string.ascii_letters + string.digits
    api_key_suffix = "".join(secrets.choice(token_chars) for _ in range(32))
    generated_api_key = f"shbkp_{api_key_suffix}"

    # 3. Check for uniqueness of the generated API key (extremely unlikely, but good practice)
    existing_api_key = (
        db.query(models.Company)
        .filter(models.Company.company_api_key == generated_api_key)
        .first()
    )
    if existing_api_key:
        # In a real app, you might want to retry generation
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique API key. Please try again.",
        )

    # 4. Set the start and end dates
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=365)  # A simple way to get a year from today

    # 5. Generate a unique ID
    company_id = str(uuid.uuid4())

    # 6. Create an instance of the ORM model from the Pydantic data
    db_company = models.Company(
        id=company_id,
        company_api_key=generated_api_key,
        start_date=start_date,
        end_date=end_date,
        **company_data.model_dump(),
    )

    # 7. Add and commit to the database
    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    return db_company
