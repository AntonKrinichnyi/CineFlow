from typing import cast
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from source.config.dependencies import get_settings
from source.config.settings import BaseAppSetinggs
from database.session_sqlite import get_sqlite_db
from source.shemas.accounts import (
    UserRegistrationResponseShema,
    UserRegistrationRequestShema
)

router = APIRouter()


@router.post(
    "register/",
    response_model=UserRegistrationResponseShema,
    summary="User Registration",
    description="Registerr a new user with an emil and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "aplication/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "aplication/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        },
    }
)
async def register_user(
    user_data: UserRegistrationRequestShema,
    db: AsyncSession = Depends(get_sqlite_db),
):
    pass
