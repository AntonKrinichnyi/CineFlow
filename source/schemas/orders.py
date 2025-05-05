from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OrderBaseSchema(BaseModel):
    user_id: int
    total_amount: float
    status: str


class MessageSchema(BaseModel):
    detail: Optional[str]
    message: str = "Success"