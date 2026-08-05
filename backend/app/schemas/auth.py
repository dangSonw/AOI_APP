import re
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from app.schemas.base import ApiSchema


WORK_EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def validate_work_email(value: str) -> str:
    normalized_value = value.strip().lower()
    if len(normalized_value) > 320 or not WORK_EMAIL_PATTERN.fullmatch(normalized_value):
        raise ValueError('Enter a valid work email address.')
    return normalized_value


WorkEmail = Annotated[str, AfterValidator(validate_work_email)]


class LoginRequest(ApiSchema):
    email: WorkEmail
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(LoginRequest):
    full_name: str = Field(min_length=1, max_length=120)


class PasswordResetRequest(ApiSchema):
    email: WorkEmail


class UserResponse(ApiSchema):
    id: int
    email: WorkEmail
    full_name: str
    is_active: bool


class AuthSessionResponse(ApiSchema):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    user: UserResponse


class MessageResponse(ApiSchema):
    message: str