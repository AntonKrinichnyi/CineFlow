from pydantic import BaseModel


class PaymentResponseSchema(BaseModel):
    order_id: int
    amount: float
    status: str
    created_at: str

    class Config:
        orm_mode = True