import enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Float, Enum, DECIMAL, Integer

from source.database.base import Base
from source.database.models.accounts import UserModel
from source.database.models.orders import OrderModel


class PaymentStatusEnum(enum.Enum):
    SUCCESSFUL = "successful"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    status: Mapped[PaymentStatusEnum] = mapped_column(Enum(PaymentStatusEnum), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    external_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)
    
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")
    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="payments")
    payment_item: Mapped["PaymentItemModel"] = relationship("PaymentItemModel", back_populates="payment")
