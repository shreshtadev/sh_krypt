import hashlib
import hmac

from fastapi import APIRouter, Depends, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas import (
    AdminClientRequest,
    AdminClientResponse,
    HashData,
    HashResult,
    VerifyData,
    VerifyResult,
)
from app.shbkp import (
    authenticate_client,
    create_access_token,
    create_client,
    get_current_client,
    get_db,
    oauth2_scheme,
)

router = APIRouter(prefix='/api/admin/auth', tags=['auth', 'sh_admin'])


@router.post(
    '/client/new',
    response_model=AdminClientResponse | None,
    status_code=status.HTTP_201_CREATED,
)
async def register_new_client(
    request: AdminClientRequest, db: Session = Depends(get_db)
):
    registered_client = create_client(
        client_id=request.client_id, client_secret=request.client_secret, db=db
    )
    if not registered_client:
        err = dict()
        err['detail'] = 'DUPLICATE_CLIENT_OR_ERROR'
        return JSONResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, content=err)
    return registered_client


@router.post(
    '/client/validate',
    response_model=AdminClientResponse | None,
    status_code=status.HTTP_201_CREATED,
)
async def validate_new_client(
    request: AdminClientRequest, db: Session = Depends(get_db)
):
    validated_client = authenticate_client(
        client_id=request.client_id, client_secret=request.client_secret, db=db
    )
    if not validated_client:
        err = dict()
        err['detail'] = 'CLIENT_NOT_FOUND_OR_ERROR'
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=err)
    return validated_client


@router.post('/token')
def token(
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    validated_client = authenticate_client(
        client_id=client_id, client_secret=client_secret, db=db
    )
    if not validated_client:
        err = dict()
        err['detail'] = 'CLIENT_UNAUTHORIZED'
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=err)
    access_token = create_access_token(
        data={
            'sub': str(validated_client.client_id),
            'role': 'client',
            'scope': 'register:company',
        }
    )
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/token/validate')
def validate_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    client_id = get_current_client(db, token)
    is_validated = AdminClientResponse(
        client_id=str(client_id), message='Token is valid'
    )
    return is_validated


@router.post(
    '/encode/sha256', response_model=HashResult, summary='Encode string to SHA-256 Hash'
)
def encode_sha256(data: HashData):
    """
    Computes the SHA-256 hash of the provided string.
    """
    # 1. Encode the string to bytes (required by hashlib)
    data_bytes = data.data.encode('utf-8')

    # 2. Compute the SHA-256 hash
    sha256_hash = hashlib.sha256(data_bytes).hexdigest()

    return HashResult(original_data=data.data, sha256_hash=sha256_hash)


@router.post(
    '/decode/sha256/verify',
    response_model=VerifyResult,
    summary='Verify string against a known SHA-256 Hash',
)
def verify_sha256(verification_data: VerifyData):
    """
    Verifies if the provided string produces the given SHA-256 hash.
    SHA-256 is one-way, so we can only check for a match.
    """

    # 1. Compute the hash of the input data
    input_hash = hashlib.sha256(verification_data.data.encode('utf-8')).hexdigest()

    # 2. Compare the computed hash with the known hash
    # Use hmac.compare_digest for constant-time comparison to mitigate timing attacks
    match = hmac.compare_digest(input_hash, verification_data.known_hash)

    status = 'Match' if match else 'No Match'

    return VerifyResult(match=match, status=status)
