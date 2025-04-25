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