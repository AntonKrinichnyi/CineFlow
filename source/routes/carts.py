from fastapi import (APIRouter,
                     Depends,
                     HTTPException,
                     status)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from source.database.session_sqlite import get_sqlite_db
from source.config.dependencies import get_current_user
from source.database.models.accounts import UserModel, UserGroupsEnum
from source.database.models.movies import MovieModel
from source.schemas.carts import CartResponseSchema, CartItemResponseSchema
from source.database.models.carts import (PurchasedModel,
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
    }
)
async def create_cart(
    movie_id: int,
    user_id: int = Depends(get_current_user),
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

    stmt = select(PurchasedModel).where(and_(movie_id == movie_id,
                                             user_id == user_id))
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

    stmt = select(CartItemModel).where(and_(cart_id == cart.id, user_id == user_id))
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
    }
)
async def get_cart(
    db: AsyncSession = Depends(get_sqlite_db),
    user_id: UserModel = Depends(get_current_user)
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
