from pydantic import BaseModel, EmailStr, field_validator

from database import account_validators


class BaseEmailPasswordShema(BaseModel):
    email: EmailStr
    password: str
    
    model_config = {
        "from_atributes": True
    }
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return account_validators.validate_password_strength(value)