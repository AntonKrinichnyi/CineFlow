from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from source.schemas.orders import OrderBaseSchema, MessageSchema
from source.database.models.orders import OrderModel, OrderItemModel
from source.database.models.accounts import UserModel
from source.database.models.movies import MovieModel
from source.database.models.carts import CartModel, CartItemModel, PurchasedModel
from source.database.session_sqlite import get_sqlite_db 

router = APIRouter()


@router.post(
    "/order/",
    summary="Create new order",
    description="Create a new order for the user",
    response_model=OrderBaseSchema,
    responses= {
        201: {
            "description": "Order created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "total_amount": 100.0,
                        "status": "pending",
                        }
                    }
                }
            },
        400: {
            "description": "Movie already purchased",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie already purchased"
                        }
                    }
                }
            },
        404: {
            "description": "Order created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cart not found"
                        }
                    }
                }
            },
        500: {
            "description": "Failed to create order",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to create order"
                        }
                    }
                }
            }
        }   
)
async def create_order(user_id: int,
                       db: AsyncSession = Depends(get_sqlite_db)):
    stmt = select(CartModel).where(CartModel.user_id == user_id)
    result = await db.execute(stmt)
    cart = result.scalars().first()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Cart not found")
    
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await db.execute(stmt)
    cart_items = result.scalars().all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Cart is empty")
    
    movies_in_order = []
    for item in cart_items:
        stmt = select(PurchasedModel).where(
            PurchasedModel.movie_id == item.movie_id,
            PurchasedModel.user_id == user_id
        )
        result = await db.execute(stmt)
        purchased = result.scalars().first()
        if purchased:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Movie already purchased")
        
        stmt = select(MovieModel).where(MovieModel.id == item.movie_id)
        result = await db.execute(stmt)
        movie = result.scalars().first()
        movies_in_order.append(movie)
    if not movies_in_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No movies available for order")
    total_amount = sum([movie.price for movie in movies_in_order])
    order = OrderModel(
        user_id=user_id,
        total_amount=total_amount,
        status="pending",
    )
    try:
        db.add(order)
        await db.commit()
        await db.refresh(order)
        for movie in movies_in_order:
            order_item = OrderItemModel(
                order_id=order.id,
                movie_id=movie.id,
                price_at_order=movie.price,
            )
            db.add(order_item)
            await db.commit()
            await db.refresh(order_item)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create order")
    return OrderBaseSchema.model_validate(
        user_id=user_id,
        total_amount=total_amount,
        status="pending",
    )


@router.post(
    "/order/cancel/",
    summary="Cencel the order",
    description="Cancel the order for the user",
    response_model=MessageSchema,
    responses={
        400: {
            "description": "Order cannot be canceled",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order cannot be canceled"
                        }
                    }
                }
            },
        404: {
            "description": "Order not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order not found"
                        }
                    }
                }
            },
        500: {
            "description": "Failed to cancel order",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to cancel order"
                        }
                    }
                }
            }
        }
)
async def cancel_order(user_id: int,
                       order_id: int,
                       db: AsyncSession = Depends(get_sqlite_db)):
    stmt = select(OrderModel).where(and_(OrderModel.user_id == user_id,
                                         OrderModel.id == order_id))
    result = await db.execute(stmt)
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Order not found")
    
    if order.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Order cannot be canceled")
    
    try:
        order.status = "canceled"
        await db.commit()
        await db.refresh(order)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to cancel order")
    
    return MessageSchema.model_validate(
        message="Order canceled successfully",
        detail=None
    )


@router.get(
    "/order/{user_id}/",
    summary="Get all orders for the user",
    description="Get all orders for the user",
    response_model=list[OrderBaseSchema],
    responses={
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found"
                        }
                    }
                }
            }
        }
)
async def get_orders(user_id: int,
                      db: AsyncSession = Depends(get_sqlite_db)):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")
    
    stmt = select(OrderModel).where(OrderModel.user_id == user_id)
    result = await db.execute(stmt)
    orders = result.scalars().all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No orders found")
    
    return [OrderBaseSchema.model_validate(
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status
    ) for order in orders]


@router.get(
    "/admin/orders/",
    response_model=list[OrderBaseSchema],
    summary="Get all orders",
    description="Get all orders, with pagination, sorting, and filtering",
)
async def get_all_orders(
    db: AsyncSession = Depends(get_sqlite_db),
    page: int = 1,
    limit: int = 10,
    sort_by: str = "created_at",
    sort_order: str = "asc",
    status: str = None,
):
    stmt = select(OrderModel)
    
    if status:
        stmt = stmt.where(OrderModel.status == status)
    
    if sort_order == "desc":
        stmt = stmt.order_by(getattr(OrderModel, sort_by).desc())
    else:
        stmt = stmt.order_by(getattr(OrderModel, sort_by))
    
    result = await db.execute(stmt.offset((page - 1) * limit).limit(limit))
    orders = result.scalars().all()
    
    return [OrderBaseSchema.model_validate(
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status
    ) for order in orders]
