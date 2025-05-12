from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, field_validator, Field


class GenreSchema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class DirectorSchema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class StarSchema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class CertificationSchema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class MovieBaseSchema(BaseModel):
    uuid: str | None = None
    name: str
    year: int
    time: int
    imdb: float
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: float
    
    model_config = {
        "from_attributes": True,
    }
    
    @field_validator("year")
    @classmethod
    def validate_year(cls, value):
        current_year = datetime.now(timezone.utc).year
        if value > current_year + 1:
            raise ValueError(f"The year in 'year' cannot be greater than {current_year + 1}.")
        return value


class CommentSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    
    model_config = {
        "from_attributes": True,
    }


class CommentCreateSchema(BaseModel):
    comment: str = Field(..., min_length=1, max_length=1000)


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    genres: list[GenreSchema]
    stars: list[StarSchema]
    directors: list[DirectorSchema]
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    
    model_config = {
        "from_attributes": True,
    }


class MovieCreateSchema(BaseModel):
    uuid: str | None = None
    name: str
    year: int
    time: int
    imdb: float = Field(..., ge=0, le=10)
    meta_score: float
    gross: float
    description: str
    price: float = Field(..., ge=0)
    genres: list[str]
    stars: list[str]
    directors: list[str]
    certification: int
    
    model_config = {
        "from_attributes": True,
    }


class MovieUpdateSchema(BaseModel):
    name: str | None = None
    year: int | None = None
    time: int | None = None
    imdb: float | None = Field(None, ge=0, le=10)
    meta_score: float | None = None
    gross: float | None = None
    description: str | None = None
    price: float | None = Field(None, ge=0)
    certification: int | None = None
    genres: list[str] | None = None
    directors: list[str] | None = None
    stars: list[str] | None = None
    
    model_config = {
        "from_attributes": True,
    }


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    time: int
    imdb: float
    genres: List[GenreSchema]
    directors: List[DirectorSchema]
    stars: List[StarSchema]
    
    model_config = {
        "from_attrinutes": True,
    }


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int
    
    model_config = {
        "from_attributes": True,
    }


class FavoriteSchema(MovieListItemSchema):
    created_at: datetime


class FavoriteListResponseSchema(BaseModel):
    movies: List[FavoriteSchema]
    current_page: int
    total_pages: int
    total_items: int
