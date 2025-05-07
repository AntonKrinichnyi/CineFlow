import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.models.orders import OrderModel, OrderItemModel
from database.models.accounts import UserModel
from database.models.movies import MovieModel
from database.models.carts import CartModel, CartItemModel
from schemas.orders import OrderBaseSchema, MessageSchema


@pytest.mark.asyncio
async def test_create_order_success():
    user = UserModel(id=1)
    cart = CartModel(id=1, user_id=1)
    movie = MovieModel(id=1, name="Test Movie", price=9.99)
    cart_item = CartItemModel(movie_id=1)
    cart.cart_items = [cart_item]
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=cart))),
        MagicMock(scalars=MagicMock(all=MagicMock(return_value=[cart_item]))),
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=None)))
    ] * len(cart.cart_items)
    db.scalar_one_or_none.return_value = movie
    
    result = OrderBaseSchema(user_id=1, total_amount=9.99, status="pending")
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    assert isinstance(result, OrderBaseSchema)
    assert result.user_id == 1
    assert result.total_amount == 9.99
    assert db.add.call_count >= 2
    db.commit.assert_called()

@pytest.mark.asyncio
async def test_create_order_cart_not_found():
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = MagicMock(scalars=MagicMock(first=MagicMock(return_value=None)))
    
    with pytest.raises(HTTPException) as exc_info:
        order = OrderBaseSchema(user_id=1, total_amount=0, status="pending")
        db.add(order)
        await db.commit()
        await db.refresh(order)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Cart not found"


@pytest.mark.asyncio
async def test_cancel_order_success():
    order = OrderModel(id=1, user_id=1, status="pending")
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = MagicMock(scalars=MagicMock(first=MagicMock(return_value=order)))
    
    order = select(OrderModel).where(and_(user_id=1, order_id=1,))
    result = await db.execute(order)
    order = result.scalar_one_or_none()
    order.status = "canceled"
    
    assert order.status == "canceled"
    db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_orders_success():
    user = UserModel(id=1)
    order = OrderModel(id=1, user_id=1, total_amount=9.99, status="pending")
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=user))),  # User query
        MagicMock(scalars=MagicMock(all=MagicMock(return_value=[order])))  # Orders query
    ]
    
    orders = select(OrderModel).where(OrderModel.user_id == 1)
    result = await db.execute(orders)
    orders = result.scalars().all()
    
    assert isinstance(orders, list)
    assert len(orders) == 1
    assert orders[0].user_id == 1


@pytest.mark.asyncio
@patch('orders.stripe.checkout.Session.create')
@patch('orders.EmailSender.send_email_payment_success')
async def test_pay_order_success(email_sender, stripe_session):
    user = UserModel(id=1, email="test@example.com")
    order = OrderModel(id=1, user_id=1, total_amount=9.99, status="pending")
    order_item = OrderItemModel(id=1, order_id=1, movie_id=1, price_at_order=9.99)
    movie = MovieModel(id=1, name="Test Movie")
    
    stripe_session.return_value = MagicMock(success_url="http://success.com")
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=user))),
        MagicMock(scalars=MagicMock(all=MagicMock(return_value=[order_item]))),
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=movie))),
        MagicMock(scalars=MagicMock(first=MagicMock(return_value=order)))
    ]
    
    result = await stripe_session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": movie.name,
                    },
                    "unit_amount": int(order.total_amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="http://success.com",
        cancel_url="http://cancel.com",
    )
    
    assert isinstance(result, MessageSchema)
    assert result.message == "Payment successful"
    stripe_session.assert_called_once()
    email_sender.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called()

@pytest.mark.asyncio
@patch('orders.stripe.checkout.Session.create')
async def test_pay_order_failure(stripe_session):
    stripe_session.side_effect = Exception("Stripe error")
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = MagicMock(scalars=MagicMock(first=MagicMock(return_value=MagicMock())))
    
    with pytest.raises(HTTPException) as exc_info:
        result = await stripe_session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": movie.name,
                    },
                    "unit_amount": int(order.total_amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="http://success.com",
        cancel_url="http://cancel.com",
    )
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Failed to process payment"
