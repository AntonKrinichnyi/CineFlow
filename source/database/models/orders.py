import enum
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy import func
from sqlalchemy.types import (
    Integer,
    Enum,
    DateTime,
    DECIMAL
)

from database.models.base import Base
from database.models.accounts import UserModel
from database.models.movies import MovieModel


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[OrderStatusEnum] = mapped_column(Enum(OrderStatusEnum), nullable=False, unique=True)
    total_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    user: Mapped[UserModel] = relationship(UserModel, back_populates="order")
    order_items: Mapped[list["OrderItemModel"]] = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    payment: Mapped["PaymentModel"] = relationship("PaymentModel", back_populates="order")
    

class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped[OrderModel] = relationship(OrderModel, back_populates="order_items")
    movie: Mapped[MovieModel] = relationship(MovieModel, back_populates="order_items")
    payment_item: Mapped["PaymentItemModel"] = relationship("PaymentItemModel", back_populates="order_item")
