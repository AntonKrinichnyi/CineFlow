import uuid

from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.types import (
    Text,
    DECIMAL,
    String,
    Float,
    Integer,
)
from sqlalchemy.sql.schema import (ForeignKey,
                                   Table,
                                   Column,
                                   UniqueConstraint)

from source.database.base.base import Base
from source.database.base.models.accounts import UserModel


MoviesGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)

MoviesDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)

MoviesStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)


class GenresModel(Base):
    __tablename__ = "genres"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )
    
    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class StarsModel(Base):
    __tablename__ = "stars"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesStarsModel,
        back_populates="stars"
    )
    
    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class DirectorsModel(Base):
    __tablename__ = "directors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesDirectorsModel,
        back_populates="directors"
    )
    
    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class CertificationsModel(Base):
    __tablename__ = "certifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        back_populates="certification"
    )
    
    def __repr__(self):
        return f"<Certification(name='{self.name}')>"
