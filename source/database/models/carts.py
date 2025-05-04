from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey, UniqueConstraint

from source.database.base import Base
from source.database.models.accounts import UserModel 


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

