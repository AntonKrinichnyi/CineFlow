from typing import List

from pydantic import BaseModel


class CartItemResponseSchema(BaseModel):
    id: int
    title: str
    price: float
    genre: List[str]
    release_year: int


class CartResponseSchema(BaseModel):
    id: int
    items: List[CartItemResponseSchema]


class CartCreateSchema(BaseModel):
    user_id: int
    movie_id: int