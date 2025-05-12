from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OrderBaseSchema(BaseModel):
    user_id: int | None = None
    total_amount: float | None = None
    status: str | None = None


class MessageSchema(BaseModel):
    detail: Optional[str]
    message: str = "Success"