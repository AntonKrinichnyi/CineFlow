import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.accounts import UserModel, UserGroupsEnum, UserGroupModel
from database.models.movies import MovieModel
from database.models.carts import CartModel, CartItemModel
from schemas.carts import CartResponseSchema
from notifications.interfaces import EmailSenderInterface

@pytest.mark.asyncio
async def test_create_cart_success():
    user = UserModel(id=1)
    movie = MovieModel(id=1, name="Test Movie")
    cart = CartModel(id=1, user_id=1)
    
    db = AsyncMock(spec=AsyncSession)
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=movie)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    
    from carts import create_cart
    result = await create_cart(
        cart_data=MagicMock(user_id=1, movie_id=1),
        db=db
    )
    
    assert result == {"message": "Test Movie added in cart successfully"}
    assert db.add.call_count == 2
    db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_cart_user_not_found():
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    
    from carts import create_cart
    with pytest.raises(HTTPException) as exc_info:
        await create_cart(
            cart_data=MagicMock(user_id=1, movie_id=1),
            db=db
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "User not found."


@pytest.mark.asyncio
async def test_get_cart_success():
    user = UserModel(id=1)
    user.group = UserGroupModel(name=UserGroupsEnum.USER)
    cart = CartModel(id=1, user_id=1)
    movie = MovieModel(id=1, name="Test Movie", price=9.99, year=2023)
    cart_item = CartItemModel(movie=movie)
    cart.cart_items = [cart_item]
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=user))),
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=cart))),
    ]
    
    assert isinstance(cart, CartResponseSchema)
    assert cart.id == 1
    assert len(cart.items) == 1
    assert cart.items[0].title == "Test Movie"

@pytest.mark.asyncio
async def test_get_cart_unauthorized():
    user = UserModel(id=2)
    user.group = UserGroupModel(name=UserGroupsEnum.USER)
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = MagicMock(scalar=MagicMock(first=MagicMock(return_value=user)))
    cart = CartModel(id=1, user_id=1)
    with pytest.raises(HTTPException) as exc_info:
        await cart(user_id=1, db=db)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Not authorized."

@pytest.mark.asyncio
async def test_clear_cart_success():
    user = UserModel(id=1)
    cart = CartModel(id=1, user_id=1)
    cart_item = CartItemModel(id=1)
    cart.cart_items = [cart_item]
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=user))),  # User query
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=cart))),  # Cart query
    ]
    
    result = await cart(user_id=1, db=db)
    
    assert result == {"detail": "Cart cleared successfully."}
    db.delete.assert_called_once()
    db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_clear_cart_empty():
    user = UserModel(id=1)
    cart = CartModel(id=1, user_id=1)
    cart.cart_items = []
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=user))),
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=cart))),
    ]
    
    with pytest.raises(HTTPException) as exc_info:
        await cart(user_id=1, db=db)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Cart is already empty."

@pytest.mark.asyncio
async def test_remove_movie_from_cart_success():
    user = UserModel(id=1)
    movie = MovieModel(id=1, name="Test Movie")
    cart = CartModel(id=1, user_id=1)
    cart_item = CartItemModel(id=1, movie=movie)
    moderator = UserModel(email="moderator@test.com")
    moderator.group = UserGroupModel(name=UserGroupsEnum.MODERATOR)
    
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=user))),
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=movie))),
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=cart))),
        MagicMock(scalar=MagicMock(first=MagicMock(return_value=cart_item))),
        MagicMock(scalar=MagicMock(all=MagicMock(return_value=[moderator]))),
    ]
    
    email_sender = MagicMock(spec=EmailSenderInterface)
    background_tasks = MagicMock()
    
    result = await cart_item(
        movie_id=1,
        cart_id=1,
        background_tasks=background_tasks,
        user_id=1,
        db=db,
        email_sender=email_sender
    )
    
    assert result == {"message": "Test Movie removed from cart id 1 successfully"}
    db.delete.assert_called_once_with(cart_item)
    db.commit.assert_called_once()
    background_tasks.add_task.assert_called_once()
