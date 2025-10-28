import time
import uuid

from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.config import IS_DEBUG
from app.routes import auth, company, filemeta

# Import the SQLAlchemy models and Pydantic schemas
from . import models
from .logging import lifespan, logger

# Create the database tables on startup
if IS_DEBUG:
    models.Base.metadata.create_all(bind=models.engine)
app = (
    FastAPI(title='ShKrypt API', version='1.0.0', lifespan=lifespan)
    if IS_DEBUG
    else FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
)
app.add_middleware(CorrelationIdMiddleware)  # type: ignore
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(filemeta.router)


@app.middleware('http')
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response: Response = await call_next(request)
    process_time = time.time() - start_time
    response.headers['X-Process-Time'] = str(round(process_time, 4))
    return response


@app.middleware('http')
async def logging_middleware(request: Request, call_next):
    request_id = correlation_id.get() or str(uuid.uuid4())
    start_time = time.time()

    client_ip = request.client.host if request.client else 'unknown'
    user_agent = request.headers.get('user-agent', 'unknown')

    try:
        logger.info(
            'request_started',
            extra={
                'correlation_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'base_url': str(request.base_url),
                'client_ip': client_ip,
                'user_agent': user_agent,
            },
        )

        response: Response = await call_next(request)

        process_time = round(time.time() - start_time, 4)
        response.headers['X-Process-Time'] = str(process_time)

        logger.info(
            'request_completed',
            extra={
                'correlation_id': request_id,
                'status_code': response.status_code,
                'process_time': process_time,
                'client_ip': client_ip,
                'user_agent': user_agent,
            },
        )

        return response

    except Exception as e:
        process_time = round(time.time() - start_time, 4)
        logger.error(
            'request_error',
            extra={
                'correlation_id': request_id,
                'error': str(e),
                'method': request.method,
                'path': request.url.path,
                'client_ip': client_ip,
                'user_agent': user_agent,
                'process_time': process_time,
            },
        )
        raise e


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = correlation_id.get()
    client_ip = request.client.host if request.client else 'unknown'
    user_agent = request.headers.get('user-agent', 'unknown')

    logger.error(
        'unhandled_exception',
        extra={
            'correlation_id': request_id,
            'error': str(exc),
            'method': request.method,
            'path': request.url.path,
            'client_ip': client_ip,
            'user_agent': user_agent,
        },
    )

    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error', 'correlation_id': request_id},
    )
