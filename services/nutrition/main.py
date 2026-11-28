from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated
import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from auth import current_user, internal_user, verify_user
from schemas import DailySummary, Item, ItemInput, Meal, MealCreate, MealInput, MealPatch, MealSummary


@asynccontextmanager
async def lifespan(app: FastAPI):
    names = (
        "DATABASE_URL", "JWT_SECRET", "JWT_ISSUER", "JWT_AUDIENCE",
        "USER_SERVICE_URL", "NUTRITION_TO_USER_TOKEN", "USER_TO_NUTRITION_TOKEN",
    )
    settings = {name: os.environ[name] for name in names}
    for name, value in settings.items():
        if not value.strip():
            raise RuntimeError(f"{name} must not be empty")
    if len(settings["JWT_SECRET"].encode()) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")

    with ConnectionPool(
        settings["DATABASE_URL"], kwargs={"row_factory": dict_row},
        min_size=1, max_size=4, open=False,
    ) as pool, httpx.Client(
        base_url=settings["USER_SERVICE_URL"],
        headers={"X-Service-Token": settings["NUTRITION_TO_USER_TOKEN"]},
        timeout=2.0,
    ) as user_api:
        pool.wait(timeout=10)
        migrations = Path(__file__).parent / "migrations"
        with pool.connection() as connection:
            # Run migrations one at a time if two instances start together.
            connection.execute("SELECT pg_advisory_xact_lock(41007)")
            for migration in sorted(migrations.glob("*.sql")):
                connection.execute(migration.read_text(encoding="utf-8"))

        app.state.settings = settings
        app.state.pool = pool
        app.state.user_api = user_api
        yield


app = FastAPI(
    title="FitTrack Nutrition",
    lifespan=lifespan,
    responses={
        400: {"description": "Invalid request"},
        "4XX": {"description": "Request rejected"},
    },
)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    errors = [
        {"field": ".".join(map(str, entry["loc"])), "message": entry["msg"]}
        for entry in error.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": "Invalid request", "errors": errors})


def database(request: Request):
    with request.app.state.pool.connection() as connection:
        yield connection


Database = Annotated[Connection, Depends(database, scope="function")]
User = Annotated[str, Depends(current_user)]
InternalUser = Annotated[str, Depends(internal_user)]


def owned_meal(db: Connection, meal_id: int, user_id: str, for_update: bool = False):
    sql = "SELECT id, user_id, name, meal_date FROM meals WHERE id = %s"
    if for_update:
        sql += " FOR UPDATE"
    meal = db.execute(sql, (meal_id,)).fetchone()
    if meal is None:
        raise HTTPException(404, "Meal not found")
    if meal["user_id"] != user_id:
        raise HTTPException(403, "This meal belongs to another user")
    return meal


def meal_details(db: Connection, meal: dict):
    items = db.execute(
        """
        SELECT id, name, quantity, calories, protein, carbs, fat
        FROM meal_items WHERE meal_id = %s ORDER BY id
        """,
        (meal["id"],),
    ).fetchall()
    totals = {
        field: round(sum(item["quantity"] * item[field] for item in items), 3)
        for field in ("calories", "protein", "carbs", "fat")
    }
    return {**meal, "items": items, "totals": totals}


def add_item(db: Connection, meal_id: int, item: ItemInput):
    return db.execute(
        """
        INSERT INTO meal_items (meal_id, name, quantity, calories, protein, carbs, fat)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, name, quantity, calories, protein, carbs, fat
        """,
        (meal_id, item.name, item.quantity, item.calories, item.protein, item.carbs, item.fat),
    ).fetchone()


@app.get("/api/meals", response_model=list[MealSummary])
def list_meals(
    user_id: User,
    db: Database,
    meal_date: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2_147_483_647),
):
    return db.execute(
        """
        SELECT id, name, meal_date FROM meals
        WHERE user_id = %s AND (%s::date IS NULL OR meal_date = %s)
        ORDER BY meal_date DESC, id DESC LIMIT %s OFFSET %s
        """,
        (user_id, meal_date, meal_date, limit, offset),
    ).fetchall()


@app.get("/api/meals/{meal_id}", response_model=Meal)
def get_meal(meal_id: int, user_id: User, db: Database):
    return meal_details(db, owned_meal(db, meal_id, user_id))


@app.post(
    "/api/meals", response_model=Meal, status_code=201,
    responses={404: {"description": "User not found"}, 503: {"description": "User Service unavailable"}},
)
def create_meal(meal: MealCreate, request: Request, user_id: User):
    verify_user(request, user_id)
    with request.app.state.pool.connection() as db:
        created = db.execute(
            """
            INSERT INTO meals (user_id, name, meal_date) VALUES (%s, %s, %s)
            RETURNING id, name, meal_date
            """,
            (user_id, meal.name, meal.meal_date),
        ).fetchone()
        for item in meal.items:
            add_item(db, created["id"], item)
        return meal_details(db, created)


@app.put("/api/meals/{meal_id}", response_model=Meal)
def replace_meal(meal_id: int, meal: MealInput, user_id: User, db: Database):
    owned_meal(db, meal_id, user_id, for_update=True)
    updated = db.execute(
        """
        UPDATE meals SET name = %s, meal_date = %s WHERE id = %s
        RETURNING id, name, meal_date
        """,
        (meal.name, meal.meal_date, meal_id),
    ).fetchone()
    return meal_details(db, updated)


@app.patch("/api/meals/{meal_id}", response_model=Meal)
def edit_meal(meal_id: int, meal: MealPatch, user_id: User, db: Database):
    fields = meal.model_dump(exclude_unset=True)
    if not fields or None in fields.values():
        raise HTTPException(400, "Provide a name or meal date with a value")
    owned_meal(db, meal_id, user_id, for_update=True)
    updated = db.execute(
        """
        UPDATE meals SET name = COALESCE(%s, name), meal_date = COALESCE(%s, meal_date)
        WHERE id = %s RETURNING id, name, meal_date
        """,
        (meal.name, meal.meal_date, meal_id),
    ).fetchone()
    return meal_details(db, updated)


@app.delete("/api/meals/{meal_id}", status_code=204)
def delete_meal(meal_id: int, user_id: User, db: Database):
    owned_meal(db, meal_id, user_id, for_update=True)
    db.execute("DELETE FROM meals WHERE id = %s", (meal_id,))
    return Response(status_code=204)


@app.post("/api/meals/{meal_id}/items", response_model=Item, status_code=201)
def create_item(meal_id: int, item: ItemInput, user_id: User, db: Database):
    owned_meal(db, meal_id, user_id, for_update=True)
    return add_item(db, meal_id, item)


@app.put("/api/meals/{meal_id}/items/{item_id}", response_model=Item)
def replace_item(meal_id: int, item_id: int, item: ItemInput, user_id: User, db: Database):
    owned_meal(db, meal_id, user_id, for_update=True)
    updated = db.execute(
        """
        UPDATE meal_items SET name = %s, quantity = %s, calories = %s,
                              protein = %s, carbs = %s, fat = %s
        WHERE meal_id = %s AND id = %s
        RETURNING id, name, quantity, calories, protein, carbs, fat
        """,
        (item.name, item.quantity, item.calories, item.protein, item.carbs, item.fat, meal_id, item_id),
    ).fetchone()
    if updated is None:
        raise HTTPException(404, "Meal item not found")
    return updated


@app.delete("/api/meals/{meal_id}/items/{item_id}", status_code=204)
def delete_item(meal_id: int, item_id: int, user_id: User, db: Database):
    owned_meal(db, meal_id, user_id, for_update=True)
    result = db.execute(
        "DELETE FROM meal_items WHERE meal_id = %s AND id = %s",
        (meal_id, item_id),
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Meal item not found")
    return Response(status_code=204)


@app.get("/meals/summary", response_model=DailySummary)
def daily_summary(user_id: InternalUser, db: Database, meal_date: date = Query(alias="date")):
    row = db.execute(
        "SELECT count(*) AS meal_count FROM meals WHERE user_id = %s AND meal_date = %s",
        (user_id, meal_date),
    ).fetchone()
    return {"date": meal_date, "meal_count": row["meal_count"]}
