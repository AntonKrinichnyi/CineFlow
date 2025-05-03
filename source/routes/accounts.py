from typing import cast
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from source.config.dependencies import (get_settings,
                                        get_accounts_email_notificator,
                                        get_jwt_auth_manager)
from source.config.settings import BaseAppSettings
from database.session_sqlite import get_sqlite_db
from source.shemas.accounts import (
    UserRegistrationResponseShema,
    UserRegistrationRequestShema,
    MessageResponseShema,
    UserActivationRequestShema,
    PasswordResetRequestShema,
    PasswordResetCompleteRequestShema,
    UserLoginResponseShema,
    UserLoginRequestShema
)
from source.database.base.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupsEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)
from source.notifications.email_sender import EmailSender
from source.notifications.interfaces import EmailSenderInterface
from source.security.interfaces import JWTAuthManagerInterface

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


@router.post(
    "/activate/",
    response_model=MessageResponseShema,
    summary="Activate user account.",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad request - The activation token is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "aplication/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account already active.",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    },
)
async def active_account(
    activation_data: UserActivationRequestShema,
    db: AsyncSession = Depends(get_sqlite_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseShema:
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == activation_data.email,
            ActivationTokenModel.token == activation_data.token
        )
    )
    result = await db.execute(stmt)
    token_record = result.scalars().first()
    
    now_utc = datetime.now(datetime.timezone.utc)
    if not token_record or cast(datetime, token_record.expires_at).replace(tzinfo=datetime.timezone.utc) < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )
        
    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )
    
    user.is_active = True
    await db.delete(token_record)
    await db.commit()
    
    login_link = "http://127.0.0.1/accounts/login/"
    
    await EmailSender.send_activation_complete_email(
        str(activation_data.email),
        login_link
    )
    
    return MessageResponseShema(message="User account activated succesfuly.")


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseShema,
    summary="Reques password reset token.",
    description=(
            "Allows a user to request a password reset token. If the user exists and is active, "
            "a new token will be generated and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
)
async def request_password_reset_token(
    data: PasswordResetRequestShema,
    db: AsyncSession = Depends(get_sqlite_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseShema:
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not user.is_active:
        return MessageResponseShema(
            message="If you are registered, you will receive an email with instructions."
        )
    
    await db.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id))
    
    reset_token = PasswordResetTokenModel(user_id=cast(int, user.id))
    db.add(reset_token)
    await db.commit()
    
    password_reset_complete_link = "http://127.0.0.1/accounts/password-reset-complete/"
    
    await EmailSender.send_password_reset_email(
        str(data.email),
        password_reset_complete_link
    )
    
    return MessageResponseShema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseShema,
    summary="Reset user password",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses= {
        400: {
            "description": (
                 "Bad Request - The provided email or token is invalid, "
                "the token has expired, or the user account is not active."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid email or token.",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        },
                        "expires_token": {
                            "summary": "Token is expired",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            },
        },
    },
)
async def reset_password(
    data: PasswordResetCompleteRequestShema,
    db: AsyncSession = Depends(get_sqlite_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseShema:
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )
    
    stmt = select(PasswordResetTokenModel).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()
    
    if not token_record or token_record.token != data.token:
        if token_record:
            await db.run_sync(lambda s: s.delete(token_record))
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )
    
    expires_at = cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token"
        )
    
    try:
        user.password = data.password
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback(),
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )

    login_link = "http://127.0.0.1/accounts/login/"
    
    await EmailSender.send_password_reset_complete_email(
        str(data.email),
        login_link
    )
    
    return MessageResponseShema(
        message="Password reset successfuly"
    )


@router.post(
    "/login/",
    response_model=UserLoginResponseShema,
    summary="User login.",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password"
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is not activated."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
async def login_user(
    login_data: UserLoginRequestShema,
    db: AsyncSession = Depends(get_sqlite_db),
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager), 
) -> UserLoginResponseShema:
    stmt = select(UserModel).filter_by(email=login_data.email)
    result = db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password or email."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated."
        )
    
    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})
    
    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )
    
    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseShema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token
    )
