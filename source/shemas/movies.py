from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class GenreShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_atributes": True,
    }


class DirectorShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_atributes": True,
    }


class StarShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_atributes": True,
    }


class CertificationShema(BaseModel):
    id: int
    name: str
    
    model_config = {
        "from_atributes": True,
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
        "from_atributes": True,
    }
    
    @field_validator("year")
    @classmethod
    def validate_year(cls, value):
        current_year = datetime.now(timezone.utc).year
        if value > current_year + 1:
            raise ValueError(f"The year in 'year' cannot be greater than {current_year + 1}.")
        return value
