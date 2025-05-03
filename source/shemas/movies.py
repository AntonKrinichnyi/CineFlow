from datetime import datetime, timezone

from pydantic import BaseModel, field_validator, Field


class GenreShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class DirectorShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class StarShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class CertificationShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_attributes": True,
    }


class MovieBaseShema(BaseModel):
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


class CommentShema(BaseModel):
    id: int
    user_id: int
    comment: str
    answers: list[int] | None = None
    
    model_config = {
        "from_attributes": True,
    }


class MovieDetailShema(BaseModel):
    id: int
    genres: list[GenreShema]
    stars: list[StarShema]
    directors: list[DirectorShema]
    certification: CertificationShema
    comments: list[CommentShema]
    
    model_config = {
        "from_attributes": True,
    }


class MovieCreateShema(BaseModel):
    uuid: str | None = None
    name: str
    year: int
    time: int
    imdb: float = Field(..., ge=0, le=10)
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: float = Field(..., ge=0)
    likes: int
    dislikes: int
    genres: list[str]
    stars: list[str]
    directors: list[str]
    certification: str
    comments: list[CommentShema]
    
    model_config = {
        "from_attributes": True,
    }
    
    @field_validator("")
    @classmethod
    def validate_list_friends(cls, value: list[str]) -> list[str]:
        return [item.title() for item in value]