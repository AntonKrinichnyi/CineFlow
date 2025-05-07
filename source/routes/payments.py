from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from schemas.payments import PaymentResponseSchema
from database.session_sqlite import get_sqlite_db
from database.models.payments import PaymentModel
from database.models.orders import OrderModel, OrderItemModel
from database.models.movies import MovieModel

router = APIRouter()


@router.get(
    "/payments/",
    response_model=list[PaymentResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all payments",
    description="Retrieve a list of all payments made by the user.",
)
async def get_payments(user_id: int,
                       db: AsyncSession = Depends(get_sqlite_db)) -> list[PaymentResponseSchema]:
    stmt = select(PaymentModel).where(PaymentModel.user_id == user_id)
    result = await db.execute(stmt)
    payments = result.scalars().all()
    if not payments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No payments found")
    return [PaymentResponseSchema(order_id=payment.order_id,
                                  amount=payment.amount,
                                  status=payment.status,
                                  created_at=payment.created_at) for payment in payments]


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponseSchema,
    summary="Get payment by ID",
    description="Retrieve a specific payment by its ID.",
    responses={
        404: {
            "description": "Payment not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Payment not found"
                    }
                }
            }
        }
    },

)
async def retrive_paument(payment_id: int,
                          db: AsyncSession = Depends(get_sqlite_db)) -> PaymentResponseSchema:
    stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Payment not found")
    
    stmt = select(OrderModel).where(OrderModel.id == payment.order_id)
    result = await db.execute(stmt)
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Order not found")
    
    stmt = select(OrderItemModel).where(OrderItemModel.order_id == order.id)
    result = await db.execute(stmt)
    order_items = result.scalars().all()
    if not order_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Order items not found")
    
    movies = []
    for order_item in order_items:
        stmt = select(MovieModel).where(MovieModel.id == order_item.movie_id)
        result = await db.execute(stmt)
        movie = result.scalars().first()
        if not movie:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Movie not found")
        movies.append(movie.title)
    
    return PaymentResponseSchema(order_id=payment.order_id,
                                  amount=payment.amount,
                                  status=payment.status,
                                  created_at=payment.created_at,
                                  movies=movies)
