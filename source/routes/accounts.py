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
from source.database.base.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupsEnum,
    ActivationTokenModel
)
from source.notifications.email_sender import EmailSender
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
) -> UserRegistrationResponseShema:
    stmt = select(UserModel).where(UserModel.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )
    
    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupsEnum.USER)
    result = await db.execute(stmt)
    user_group = result.scalars().first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found"
        )

    try:
        new_user = UserModel.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        await db.flush()
        
        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)
        
        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured during user creation."
        ) from SQLAlchemyError
    else:
        activation_link = "http://127.0.0.1/accounts/activate/"
        
        await EmailSender.send_activation_email(
            new_user.email,
            activation_link
        )
        
        return UserRegistrationResponseShema.model_validate(new_user)

