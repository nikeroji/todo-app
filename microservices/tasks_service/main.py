from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from publisher import publish_task_created

from database import Base, engine, get_db
from models import Todo
from schemas import TodoCreate, TodoRead, TodoStatusUpdate, TodoUpdate

from fastapi.middleware.cors import CORSMiddleware

from cache import (
    get_cached_tasks,
    cache_tasks,
    invalidate_tasks_cache,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(title="Список задач — REST API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8081"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


def get_todo_or_404(todo_id: int, db: Session) -> Todo:
    todo = db.get(Todo, todo_id)

    if todo is None:
        raise HTTPException(
            status_code=404,
            detail="Задача не найдена",
        )

    return todo


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}


@app.get("/api/tasks", response_model=list[TodoRead])
def read_todos(
    response: Response,
    db: Session = Depends(get_db),
):
    cached_tasks = get_cached_tasks()

    if cached_tasks is not None:
        print("[cache] HIT: список получен из Redis", flush=True)
        response.headers["X-Cache"] = "HIT"
        return cached_tasks

    print("[cache] MISS: запрос списка к PostgreSQL", flush=True)

    todos = db.scalars(
        select(Todo).order_by(Todo.id.desc())
    ).all()

    tasks = [
        TodoRead.model_validate(todo).model_dump(mode="json")
        for todo in todos
    ]

    cache_tasks(tasks)

    response.headers["X-Cache"] = "MISS"
    return tasks


@app.get("/api/tasks/{todo_id}", response_model=TodoRead)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
    return get_todo_or_404(todo_id, db)


@app.post("/api/tasks", response_model=TodoRead, status_code=201)
def create_todo(
    data: TodoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    todo = Todo(
        title=data.title,
        description=data.description,
        due_date=data.due_date,
    )

    db.add(todo)
    db.commit()
    invalidate_tasks_cache()
    db.refresh(todo)

    background_tasks.add_task(
        publish_task_created,
        todo.id,
        todo.title,
    )

    return todo


@app.put("/api/tasks/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    data: TodoUpdate,
    db: Session = Depends(get_db),
):
    todo = get_todo_or_404(todo_id, db)

    todo.title = data.title
    todo.description = data.description
    todo.due_date = data.due_date
    todo.is_completed = data.is_completed

    db.commit()
    invalidate_tasks_cache()
    db.refresh(todo)

    return todo


@app.patch("/api/tasks{todo_id}", response_model=TodoRead)
def update_todo_status(
    todo_id: int,
    data: TodoStatusUpdate,
    db: Session = Depends(get_db),
):
    todo = get_todo_or_404(todo_id, db)
    todo.is_completed = data.is_completed

    db.commit()
    invalidate_tasks_cache()
    db.refresh(todo)

    return todo


@app.delete("/api/tasks{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    todo = get_todo_or_404(todo_id, db)

    db.delete(todo)
    invalidate_tasks_cache()
    db.commit()

    return Response(status_code=204)
