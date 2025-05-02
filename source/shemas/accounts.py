from pydantic import BaseModel, EmailStr, field_validator

from database import account_validators


class BaseEmailPasswordShema(BaseModel):
    email: EmailStr
    password: str
    
    model_config = {
        "from_attributes": True
    }
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return account_validators.validate_password_strength(value)


class UserRegistrationRequestShema(BaseEmailPasswordShema):
    pass


class PasswordResetRequesShema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestShema(BaseEmailPasswordShema):
    token: str


class UserLoginRequestShema(BaseEmailPasswordShema):
    pass


class UserLoginResponseShema(BaseModel):
    acces_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseShema(BaseModel):
    id: int
    email: EmailStr
    
    model_config = {
        "from_attributes": True
    }


class UserActivationRequestShema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseShema(BaseModel):
    message: str


class TokenRefreshRequestShema(BaseModel):
    regresh_token: str


class TokenRefreshResponseShema(BaseModel):
    acces_token: str
    token_type: str = "bearer"
    