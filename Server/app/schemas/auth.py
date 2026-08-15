from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.core.config import get_settings

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9 \-]{6,20}$")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_password_policy(v: str) -> str:
    minimum = get_settings().password_min_length
    if len(v) < minimum:
        raise ValueError(f"password must be at least {minimum} characters")
    return v


class UserRegister(InputModel):
    email: EmailStr = Field(max_length=254)
    # Upper bound is a denial-of-service control: argon2 on a 10 MB "password"
    # is a free CPU burn for the attacker.
    password: str = Field(min_length=12, max_length=128)
    first_name: Name
    last_name: Name
    birth_date: date | None = None
    phone: Phone | None = None

    @field_validator("password")
    @classmethod
    def _meets_policy(cls, v: str) -> str:
        return _validate_password_policy(v)

    @field_validator("birth_date")
    @classmethod
    def _plausible(cls, v: date | None) -> date | None:
        if v is None:
            return v
        today = date.today()
        if v < date(1900, 1, 1) or v > today.replace(year=today.year - 13):
            raise ValueError("birth_date is out of range")
        return v


class UserPublic(BaseModel):
    user_id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: Literal["admin", "customer"]
    email_verified: bool
    created_at: datetime


class LoginRequest(InputModel):
    email: EmailStr = Field(max_length=254)
    # No policy minimum here. Login validates the password against the stored
    # hash, never against the current rules — otherwise the error itself tells
    # an attacker the policy, and an older short password can never sign in.
    password: str = Field(min_length=1, max_length=128)


class ChallengeResponse(BaseModel):
    challenge_token: str
    expires_in: int


class VerifyRequest(InputModel):
    challenge_token: str = Field(min_length=1, max_length=2048)
    code: Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ForgotRequest(InputModel):
    email: EmailStr = Field(max_length=254)


class ForgotResponse(BaseModel):
    detail: str = "If that email is registered, check your inbox for reset instructions."


class ResetRequest(InputModel):
    token: str = Field(min_length=20, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _meets_policy(cls, v: str) -> str:
        return _validate_password_policy(v)


class ResetResponse(BaseModel):
    detail: str = "Password updated. You can now log in."
