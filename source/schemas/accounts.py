from pydantic import BaseModel, EmailStr, field_validator

from database import account_validators


class BaseEmailPasswordSchema(BaseModel):
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


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    acces_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr
    
    model_config = {
        "from_attributes": True
    }


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(BaseModel):
    message: str


class TokenRefreshRequestSchema(BaseModel):
    regresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    acces_token: str
    token_type: str = "bearer"
    