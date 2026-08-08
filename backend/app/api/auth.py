from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
)


router = APIRouter(prefix='/api/auth', tags=['authentication'])


def build_auth_response(user: User) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=create_access_token(user),
        user=UserResponse.model_validate(user),
    )


@router.post('/login', response_model=AuthSessionResponse)
def login(credentials: LoginRequest, session: DatabaseSession) -> AuthSessionResponse:
    user = authenticate_user(session, str(credentials.email), credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='The email or password is incorrect.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='This account is inactive.')
    return build_auth_response(user)


@router.post('/register', response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(account: RegisterRequest, session: DatabaseSession) -> AuthSessionResponse:
    if not get_settings().allow_public_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Public account registration is disabled.',
        )
    if get_user_by_email(session, str(account.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='An account already uses this email.')

    try:
        user = create_user(session, str(account.email), account.full_name, account.password)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='An account already uses this email.',
        ) from error
    return build_auth_response(user)


@router.post('/password-reset', response_model=MessageResponse)
def request_password_reset(request: PasswordResetRequest) -> MessageResponse:
    return MessageResponse(
        message='If the account exists, a password reset link has been prepared.',
    )