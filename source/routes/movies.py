import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from source.database.session_sqlite import get_sqlite_db
from source.database.base.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel
)
from source.shemas.movies import (
    MovieListItemShema,
    MovieListResponseShema,
    MovieDetailShema,
    MovieCreateShema
)

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseShema,
    summary="Get a paginated list of movies",
    description=(
        "Get a paginated list of movies, and filter it by varios criteria"
        "and sort movies by different attributes like price or release date"
    ),
    responses={
        400: {
            "description": "Invalid sort by parameters.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid sort by parameters."
                    }
                }
            },
        },
        404: {
            "description": "Movies not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movies not found."}
                }
            },
        }
    }
)
async def get_movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
        db: AsyncSession = Depends(get_sqlite_db),
        search: str = None,
        min_rating: float = Query(None, ge=0, le=10),
        max_rating: float = Query(None, ge=0, le=10),
        certification: str = None,
        sort_by: str = Query(None, description="Sort by: price, year, imdb, votes"),
        genre: str = None,
        year: int = None,
) -> MovieListResponseShema:
    stmt = select(MovieModel).distinct()

    if min_rating:
        stmt = stmt.where(MovieModel.imdb >= min_rating)
    if max_rating:
        stmt = stmt.where(MovieModel.imdb <= max_rating)
    if genre:
        stmt = stmt.join(MovieModel.genres).where(GenreModel.name == genre)
    if year:
        stmt = stmt.where(MovieModel.year == year)
    if certification:
        stmt = stmt.join(MovieModel.certification).where(CertificationModel.name == certification)
    if search:
        stmt = stmt.join(MovieModel.directors).join(MovieModel.stars).where(
            or_(
                MovieModel.name.ilike(f"%{search}%"),
                MovieModel.description.ilike(f"%{search}%"),
                DirectorModel.name.ilike(f"%{search}%"),
                StarModel.name.ilike(f"%{search}%")
            )
        )
    if sort_by:
        sort_mapping = {
            "price": MovieModel.price,
            "year": MovieModel.year,
            "imdb": MovieModel.imdb,
            "votes": MovieModel.votes
        }
        sort_field = sort_mapping.get(sort_by.lstrip("-"))
        if sort_field is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sort_by parameter"
            )

        if sort_by.startswith("-"):
            stmt = stmt.order_by(sort_field.desc())
        else:
            stmt = stmt.order_by(sort_field.asc())
    else:
        stmt = stmt.order_by(MovieModel.year.desc())

    stmt = select(func.count(MovieModel.id))
    result = await db.execute(stmt)
    items = result.scalar() or 0

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movies not found."
        )

    result = await db.execute(stmt)
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movies not found."
        )

    total_pages = (items + per_page - 1) // per_page

    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt.options(
        joinedload(MovieModel.certification),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.directors),
        selectinload(MovieModel.stars)
    ))
    movies = result.unique().scalars().all()

    return MovieListResponseShema(
        movies=[MovieListItemShema.model_validate(movie) for movie in movies],
        prev_page=f"/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=items,
    )


@router.post(
    "/movies/",
    response_model=MovieDetailShema,
    summary="Add movie",
    description=(
         "<h3>This endpoint allows clients to add a new movie to the database. "
            "It accepts details such as name, date, genres, actors, languages, and "
            "other attributes. The associated country, genres, actors, and languages "
            "will be created or linked automatically.</h3>"),
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Movie created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        }
    },
)
async def create_movie(
        movie_data: MovieCreateShema,
        db: AsyncSession = Depends(get_sqlite_db)
) -> MovieDetailShema:

    stmt = select(MovieModel).where(
            and_(
                MovieModel.name == movie_data.name,
                MovieModel.year == movie_data.year,
                MovieModel.time == movie_data.time
            )
        )
    result = await db.execute(stmt)
    existing = result.scalar().first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That movie is already exists"
        )

    stmt = select(CertificationModel).where(CertificationModel.name == movie_data.certification)
    result = await db.execute(stmt)
    certificate = result.scalar_one_or_none()
    if not certificate:
        certificate = CertificationModel(name=movie_data.certification)
        db.add(certificate)
        await db.flush()

    try:
        genres_list = []
        for genre_name in movie_data.genres:
            stmt = select(GenreModel).where(GenreModel.name == genre_name)
            result = await db.execute(stmt)
            genre = result.scalar_one_or_none()
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres_list.append(genre)

        directors_list = []
        for director_name in movie_data.directors:
            stmt = select(DirectorModel).where(DirectorModel.name == director_name)
            result = await db.execute(stmt)
            director = result.scalar_one_or_none()
            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                await db.flush()
            directors_list.append(director)

        stars_list = []
        for star_name in movie_data.stars:
            stmt = select(StarModel).where(StarModel.name == star_name)
            result = await db.execute(stmt)
            star = result.scalar_one_or_none()
            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                await db.flush()
            stars_list.append(star)

        movie = MovieModel(
            uuid=str(uuid.uuid4()),
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification_id=certificate.id,
            genres=genres_list,
            directors=directors_list,
            stars=stars_list
        )

        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        return MovieDetailShema.model_validate(
            movie,
            ["genres", "directors", "stars"]
        )

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )
