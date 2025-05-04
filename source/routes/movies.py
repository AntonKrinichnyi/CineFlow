import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from source.database.session_sqlite import get_sqlite_db
from source.config.dependencies import get_current_user
from source.database.base.models.accounts import UserModel
from source.database.base.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    LikeModel,
    DislikeModel,
    RatingModel,
    CommentModel
)
from source.shemas.movies import (
    MovieListItemShema,
    MovieListResponseShema,
    MovieDetailShema,
    MovieCreateShema,
    MovieUpdateShema
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


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailShema,
    summary="Get movie details by ID",
    description=(
            "<h3>Fetch detailed information about a specific movie by its unique ID. "
            "This endpoint retrieves all available details for the movie, such as "
            "its name, genre, crew, budget, and revenue. If the movie with the given "
            "ID is not found, a 404 error will be returned.</h3>"
    ),
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        }
    }
)
async def get_movie_by_id(
        movie_id: int,
        db: AsyncSession = Depends(get_sqlite_db),
) -> MovieDetailShema:
    stmt = select(MovieModel).where(MovieModel.id == movie_id).options(
        joinedload(MovieModel.certification),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.directors),
        selectinload(MovieModel.stars),
        selectinload(MovieModel.comments).joinedload(CommentModel.user),
    )
    result = await db.execute(stmt)
    movie = result.scalar().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    for comment in movie.comments:
        comment.user_email = comment.user.email

    stmt = select(func.count()).where(LikeModel.movie_id == movie_id)
    result = await db.execute()
    likes = result.scalar() or 0

    stmt = select(func.count()).where(DislikeModel.movie_id == movie_id)
    result = await db.execute(stmt)
    dislikes = result.scalar() or 0

    stmt = select(func.avg(RatingModel.rating)).where(RatingModel.movie_id == movie_id)
    result = await db.execute(stmt)
    rating = result.scalar()
    if rating:
        rating = round(float(rating), 1)

    movie_detail = MovieDetailShema.model_validate(movie)
    movie_detail.likes = likes
    movie_detail.dislikes = dislikes
    movie_detail.rating = rating

    return movie_detail


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
            "<h3>Delete a specific movie from the database by its unique ID.</h3>"
            "<p>If the movie exists, it will be deleted. If it does not exist, "
            "a 404 error will be returned.</p>"
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Movie deleted successfully."
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    },
)
async def delete_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_sqlite_db),
):

    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch(
    "/movies/{movie_id}/",
    summary="Update a movie by ID",
    description=(
            "<h3>Update details of a specific movie by its unique ID.</h3>"
            "<p>This endpoint updates the details of an existing movie. If the movie with "
            "the given ID does not exist, a 404 error is returned.</p>"
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie updated successfully."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    }
)
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdateShema,
        db: AsyncSession = Depends(get_sqlite_db),
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id).options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.directors),
            selectinload(MovieModel.stars)
        )
    result = await db.execute(stmt)
    movie = result.scalar().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        if field not in ["genres", "directors", "stars", "certification"]:
            setattr(movie, field, value)

    if movie_data.certification:
        stmt = select(CertificationModel).where(CertificationModel.name == movie_data.certification)
        result = await db.execute(stmt)
        certificate = result.scalar_one_or_none()
        if not certificate:
            certificate = CertificationModel(name=movie_data.certification)
            db.add(certificate)
            await db.flush()
        movie.certification_id = certificate.id

    if movie_data.genres is not None:
        genres = []
        for genre_name in movie_data.genres:
            stmt = select(GenreModel).where(GenreModel.name == genre_name)
            result = await db.execute(stmt)
            genre = result.scalar().first()
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)
        movie.genres = genres

    if movie_data.directors is not None:
        directors = []
        for director_name in movie_data.directors:
            stmt = select(DirectorModel).where(DirectorModel.name == director_name)
            result = await db.execute(stmt)
            director = result.scalar().first()
            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                await db.flush()
            directors.append(director)
        movie.directors = directors

    if movie_data.stars is not None:
        stars = []
        for star_name in movie_data.stars:
            stmt = select(StarModel).where(StarModel.name == star_name)
            result = await db.execute(stmt)
            star = result.scalar().first()
            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                await db.flush()
            stars.append(star)
        movie.stars = stars

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(IntegrityError)
        )

    return MovieDetailShema.model_validate(movie)


@router.post(
    "/{movie_id}/like",
    summary="Likes",
    description="Likes a movie by ID",
    responses= {
        400: {
            "description": "Movie already liked.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie already liked."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        }
    }
)
async def like_movie(
    movie_id: int,
    user_id: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_sqlite_db)
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    stmt = select(LikeModel).where(and_(LikeModel.user_id == user_id, LikeModel.movie_id == movie_id))
    result = await db.execut(stmt)
    like_is_exist = result.scalars().first()
    if like_is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie already liked."
        )
    try:
        new_like = LikeModel(movie_id=movie_id, user_id=user_id)
        db.add(new_like)
        await db.commit()
        await db.refresh(new_like)

        return {"message": "Movie liked", "like_id": new_like.id}

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.post(
    "/{movie_id}/dislike",
    summary="Dislikes",
    description="Dislikes a movie by ID",
    responses= {
        400: {
            "description": "Movie is already disliked.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie is already disliked."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        }
    }
)
async def dislike_movie(
    movie_id: int,
    user_id: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_sqlite_db)
):
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    stmt = select(DislikeModel).where(and_(DislikeModel.user_id == user_id,
                                           DislikeModel.movie_id == movie_id))
    result = await db.execut(stmt)
    dislike_is_exist = result.scalars().first()
    if dislike_is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie is already disliked."
        )
    try:
        new_dislike = DislikeModel(movie_id=movie_id, user_id=user_id)
        db.add(new_dislike)
        await db.commit()
        await db.refresh(new_dislike)

        return {"message": "Movie disliked", "dislike_id": new_dislike.id}

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
