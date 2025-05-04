from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer, ForeignKey, UniqueConstraint, DateTime, func
)

from source.database.base import Base
from source.database.models.accounts import UserModel 
from source.database.models.movies import MovieModel


class CartModel(Base):
    __tablename__ = "carts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer,
                                         ForeignKey("users.id"),
                                         unique=True,
                                         nullable=False)
    
    cart_items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan"
    )
    user: Mapped[UserModel] = relationship(
        UserModel,
        back_populates="cart"
    )
    
    __table_args__ = (UniqueConstraint("user_id"),)
     
    def __repr__(self) -> str:
        return f"<Cart(id: {self.id}, user_id: {self.user_id}, cart_items: {self.cart_items})>"


class CartItemModel(Base):
    __tablename__ = "cart_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("cart.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movie.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    cart: Mapped[CartModel] = relationship(CartModel, back_populates="cart_items")
    movie: Mapped[MovieModel] = relationship(MovieModel, back_populates="cart_items")
    
    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)
    
    def __repr__(self):
        return f"<CartItem(id={self.id}, cart_id={self.cart_id},\
            movie_id={self.movie_id}, added_at={self.added_at})>"
