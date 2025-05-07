from fastapi import (APIRouter,
                     Depends,
                     HTTPException,
                     status,
                     BackgroundTasks)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from database.session_sqlite import get_sqlite_db
from database.models.accounts import UserModel, UserGroupsEnum, UserGroupModel
from database.models.movies import MovieModel
from config.dependencies import get_accounts_email_notificator
from schemas.carts import CartResponseSchema, CartItemResponseSchema
from notifications.interfaces import EmailSenderInterface
from database.models.carts import (PurchasedModel,
                                          CartModel,
                                          CartItemModel)

router = APIRouter()


@router.post(
    "/cart/",
    summary="Add movie to the cart.",
    description="Create cart item to the cart",
    responses={
        400: {
            "description": "You have already bought this movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You have already bought this movie."
                    }
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found"
                    }
                }
            },
        }
    },
    status_code=status.HTTP_201_CREATED
)
async def create_cart(
    movie_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_sqlite_db),
):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    stmt = select(PurchasedModel).where(and_(PurchasedModel.movie_id == movie_id,
                                             PurchasedModel.user_id == user_id))
    result = await db.cxecute(stmt)
    purchase = result.scalar().first()
    if purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already bought this movie"
        )

    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.cxecute(stmt)
    movie = result.scalar().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie not found"
        )

    stmt = select(CartModel).where(user_id == user_id)
    result = await db.cxecute(stmt)
    cart = result.scalar().first()
    if not cart:
        cart = CartModel(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    stmt = select(CartItemModel).where(and_(CartItemModel.cart_id == cart.id,
                                            CartItemModel.user_id == user_id))
    result = await db.cxecute(stmt)
    item_is_exist = result.scalar().first()
    if item_is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie is already in the cart."
        )

    try:
        cart_item = CartItemModel(cart_id=cart.id, movie_id=movie_id)
        db.add(cart_item)
        await db.commit()
        return {
            "message": f"{movie.name} added in cart successfully"
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )


@router.get(
    "/{cart_id}/",
    summary="Get movie from the cart",
    description="Get cart item from cart",
    response_model=CartResponseSchema,
    responses={
        403: {
            "description": "Not authorized.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authorized."
                    }
                }
            },
        },
        404: {
            "description": "User not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK
)
async def get_cart(
    user_id: int,
    db: AsyncSession = Depends(get_sqlite_db)
):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if user.group.name == UserGroupsEnum.ADMIN or user.id == user_id:
        stmt = select(CartModel).where(user_id == user_id)
        result = await db.cxecute(stmt)
        cart = result.scalar().first()
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found."
            )
        cart_items = cart.cart_items

        movies_data = [
            CartItemResponseSchema(
                id=item.movie.id,
                title=item.movie.name,
                price=item.movie.price,
                genre=[genre.name for genre in item.movie.genres],
                release_year=item.movie.year
            )
            for item in cart_items if item.movie
        ]

        return CartResponseSchema(id=cart.id, items=movies_data)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized."
        )


@router.delete(
    "/{cart_id}/clear/",
    summary="Clear cart items.",
    description="Clear a cart from all cart items.",
    responses={
        400: {
            "description": "Cart is already empty.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cart is already empty."
                    }
                }
            },
        },
        404: {
            "description": "Cart not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cart not found."
                    }
                }
            },
        },
        500: {
            "description": "Failed to clear cart",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to clear cart"
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK
)
async def clear_cart(
    user_id: int,
    db: AsyncSession = Depends(get_sqlite_db)
):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    stmt = select(CartModel).where(user_id == user_id)
    result = await db.cxecute(stmt)
    cart = result.scalar().first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found."
        )
    if not cart.cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is already empty."
        )

    try:
        for item in cart.cart_items:
            await db.delete(item)
        await db.commit()

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart."
        )

    return {"detail": "Cart cleared successfully."}


@router.delete(
    "/{cart_id}/{movie_id}/",
    summary="Cart item remove",
    description="Remove a cart item from cart.",
    responses={
        404: {
            "description": "User not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            },
        },
        500: {
            "description": "Request failed.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Request failed."
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK
)
async def remove_movie_from_cart(
    movie_id: int,
    cart_id: int,
    background_tasks: BackgroundTasks,
    user_id: int,
    db: AsyncSession = Depends(get_sqlite_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.cxecute(stmt)
    movie = result.scalar().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

    stmt = select(CartModel).where(user_id == user_id)
    result = await db.cxecute(stmt)
    cart = result.scalar().first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found."
        )

    stmt = select(CartItemModel).where(and_(cart_id == cart.id, movie_id == movie_id))
    result = await db.cxecute(stmt)
    cart_item = result.scalar().first()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found."
        )

    try:
        await db.delete(cart_item)
        await db.commit()

        stmt = (select(UserModel)
                .join(UserGroupModel)
                .filter(UserGroupModel == UserGroupsEnum.MODERATOR))
        result = await db.execute(stmt)
        moderators = result.scalar().all()
        for moderator in moderators:
            background_tasks.add_task(
                email_sender.send_remove_movie,
                moderator.email,
                movie.name,
                cart_id
            )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request failed."
        )

    return {
        "message": f"{movie.name} removed from cart id {cart.id} successfully"
    }
