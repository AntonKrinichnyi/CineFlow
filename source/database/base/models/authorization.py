import enum
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    String,
    Boolean,
    DateTime,
    Enum,
    Integer,
    func,
    Text,
    Date,
    UniqueConstraint
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    validates
)

from database import Base
from database import account_validators
from database.security.passwords import hash_password, verify_password
from database.security.utils import generate_secure_token

class UserGroupsEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserGenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroupModel(Base):
    __tablename__ = "user_groups"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, authoincrement=True)
    name: Mapped[UserGroupsEnum] = mapped_column(Enum(UserGroupsEnum), nullable=False, unique=True)
    
    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")
    
    def __repr__(self):
        return f"<UserGroupModel(id={self.id}, name={self.name})>"


class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, authoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    _hashed_password: Mapped[str] = mapped_column("hashed_password", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    group: Mapped["UserGroupModel"] = relationship("UserGroupModel", back_populates="user")
    profile: Mapped["UserProfileModel"] = relationship(
        "UserProfileModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})"
    
    @classmethod
    def create(cls, email: str, raw_password: str, group_id: int | Mapped[int]) -> "UserModel":
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user
    
    @property
    def password(self) -> None:
        raise AttributeError("Password is write only. Use the setter to set the password")
    
    @password.setter
    def password(self, raw_password: str) -> None:
        account_validators.validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)
    
    def verify_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self._hashed_password)
    
    @account_validators("email")
    def validate_email(self, key, value):
        return account_validators.validate_email(value.lower())
    
    def has_group(self, group_name: UserGroupsEnum) -> bool:
        return self.group.name == group_name


class UserProfileModel(Base):
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, authoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[UserGenderEnum]] = mapped_column(Enum(UserGenderEnum))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (UniqueConstraint("user_id"),)


class TokenBaseModel(Base):
    __abstract__ = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, authoincrement=True)
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=generate_secure_token
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default= lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)