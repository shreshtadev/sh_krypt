from fastapi import FastAPI, HTTPException, Request, Response, status

from app.config import IS_DEBUG
from app.routes import auth, company, filemeta

# Import the SQLAlchemy models and Pydantic schemas
from . import models
from .logging import lifespan, logger
from .shbkp import engine

# Create the database tables on startup
if IS_DEBUG:
    models.Base.metadata.create_all(bind=engine)

app = (
    FastAPI(title='ShKrypt API', version='1.0.0', lifespan=lifespan)
    if IS_DEBUG
    else FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
)
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(filemeta.router)


# ---------------------------------------------------------------------
# INTERCEPT ERRORS
# ---------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    logger.error(f'HTTPError: {exc.detail} with status code {exc.status_code}')
    return Response(
        content=exc.detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
