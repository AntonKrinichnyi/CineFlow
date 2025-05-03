from pydantic import BaseModel


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
