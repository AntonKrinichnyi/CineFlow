from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, func
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
    MovieListResponseShema
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
 