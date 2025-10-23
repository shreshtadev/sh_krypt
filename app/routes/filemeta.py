import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

# Import the SQLAlchemy models and Pydantic schemas
from app.models import Company, FileMeta
from app.schemas import FileMetaBase, FileMetaOut
from app.shbkp import get_db

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
    company_api_key: Annotated[str | None, Header(convert_underscores=False)],
    db: Session = Depends(get_db),
):
    """
    Insert new file metadata.
    """
    # Optional: Check if the company_id, company_api_key exists
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
            status_code=status.HTTP_400_BAD_REQUEST, detail='Company ID not found'
        )

    # Generate a unique ID for the new file
    file_id = str(uuid.uuid4())

    # Create an instance of the ORM model from the Pydantic data
    db_file_meta = FileMeta(id=file_id, **file_data.model_dump())
    db_file_meta.company_id = company.id

    db.add(db_file_meta)
    db.commit()
    db.refresh(db_file_meta)

    return db_file_meta
