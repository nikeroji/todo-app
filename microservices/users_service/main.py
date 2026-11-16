from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User
from schemas import UserCreate, UserRead, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Сервис пользователей",
    lifespan=lifespan,
    docs_url="/api/users/docs",
    openapi_url="/api/users/openapi.json",
    redoc_url=None,
)


def get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден",
        )

    return user


def save_user(user: User, db: Session) -> User:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if getattr(exc.orig, "pgcode", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Пользователь с таким email уже существует",
            ) from exc

        raise

    db.refresh(user)
    return user


@app.get("/api/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    query = select(User).order_by(User.id.desc())
    return db.scalars(query).all()


@app.get("/api/users/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(user_id, db)


@app.post("/api/users", response_model=UserRead, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    user = User(
        name=data.name,
        email=data.email,
    )

    db.add(user)
    return save_user(user, db)


@app.put("/api/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(user_id, db)

    user.name = data.name
    user.email = data.email

    return save_user(user, db)


@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = get_user_or_404(user_id, db)

    db.delete(user)
    db.commit()

    return Response(status_code=204)
