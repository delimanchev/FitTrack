from contextlib import asynccontextmanager
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
from pydantic import ValidationError

from auth import current_user
from goal_status import weight_status, workout_status
from schemas import Goal, GoalInput, GoalPatch, Reminder, ReminderInput, WeightStatus, WorkoutStatus


GOAL_COLUMNS = 'id, goal_type AS "goalType", target, start_weight_kg AS "startWeightKg"'
REMINDER_COLUMNS = 'id, day_of_week AS "dayOfWeek", left(reminder_time::text, 5) AS "time", enabled'


@asynccontextmanager
async def lifespan(app: FastAPI):
    names = (
        "DATABASE_URL", "JWT_SECRET", "JWT_ISSUER", "JWT_AUDIENCE",
        "PROGRESS_SERVICE_URL", "WORKOUT_SERVICE_URL",
        "GOALS_TO_PROGRESS_TOKEN", "GOALS_TO_WORKOUT_TOKEN",
    )
    settings = {name: os.environ[name] for name in names}
    for name, value in settings.items():
        if not value.strip():
            raise RuntimeError(f"{name} must not be empty")
    if len(settings["JWT_SECRET"].encode()) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")
    for name in ("PROGRESS_SERVICE_URL", "WORKOUT_SERVICE_URL"):
        url = httpx.URL(settings[name])
        if url.scheme not in ("http", "https") or not url.host:
            raise RuntimeError(f"{name} must be an HTTP or HTTPS URL")
        settings[name] = settings[name].rstrip("/")

    with ConnectionPool(
        settings["DATABASE_URL"], kwargs={"row_factory": dict_row},
        min_size=1, max_size=4, open=False,
    ) as pool, httpx.Client(timeout=2.0) as client:
        pool.wait(timeout=10)
        migrations = Path(__file__).parent / "migrations"
        with pool.connection() as connection:
            # Run migrations one at a time if two instances start together.
            connection.execute("SELECT pg_advisory_xact_lock(41008)")
            for migration in sorted(migrations.glob("*.sql")):
                connection.execute(migration.read_text(encoding="utf-8"))

        app.state.settings = settings
        app.state.pool = pool
        app.state.client = client
        yield


app = FastAPI(
    title="FitTrack Goals",
    lifespan=lifespan,
    responses={400: {"description": "Invalid request"}, "4XX": {"description": "Request rejected"}},
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


def owned_goal(db: Connection, goal_id: int, user_id: str, for_update: bool = False):
    sql = f"SELECT {GOAL_COLUMNS}, user_id FROM goals WHERE id = %s"
    if for_update:
        sql += " FOR UPDATE"
    goal = db.execute(sql, (goal_id,)).fetchone()
    if goal is None:
        raise HTTPException(404, "Goal not found")
    if goal["user_id"] != user_id:
        raise HTTPException(403, "This goal belongs to another user")
    return goal


def with_reminders(db: Connection, goals: list[dict]):
    if not goals:
        return []
    by_goal = {goal["id"]: [] for goal in goals}
    reminders = db.execute(
        f"SELECT goal_id, {REMINDER_COLUMNS} FROM goal_reminders WHERE goal_id = ANY(%s) ORDER BY id",
        (list(by_goal),),
    ).fetchall()
    for reminder in reminders:
        by_goal[reminder.pop("goal_id")].append(reminder)
    return [{**goal, "reminders": by_goal[goal["id"]]} for goal in goals]


def update_goal(db: Connection, goal_id: int, input_goal: GoalInput):
    goal = db.execute(
        f"""
        UPDATE goals SET goal_type = %s, target = %s, start_weight_kg = %s
        WHERE id = %s RETURNING {GOAL_COLUMNS}
        """,
        (input_goal.goalType, input_goal.target, input_goal.startWeightKg, goal_id),
    ).fetchone()
    return with_reminders(db, [goal])[0]


@app.get("/api/goals", response_model=list[Goal])
def list_goals(
    user_id: User, db: Database, limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2_147_483_647),
):
    goals = db.execute(
        f"SELECT {GOAL_COLUMNS} FROM goals WHERE user_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    ).fetchall()
    return with_reminders(db, goals)


@app.post("/api/goals", response_model=Goal, status_code=201)
def create_goal(goal: GoalInput, user_id: User, db: Database):
    created = db.execute(
        f"""
        INSERT INTO goals (user_id, goal_type, target, start_weight_kg)
        VALUES (%s, %s, %s, %s) RETURNING {GOAL_COLUMNS}
        """,
        (user_id, goal.goalType, goal.target, goal.startWeightKg),
    ).fetchone()
    return {**created, "reminders": []}


@app.get(
    "/api/goals/{goal_id}/status", response_model=WeightStatus | WorkoutStatus,
    responses={503: {"description": "Required service is unavailable or returned invalid data"}},
)
def get_status(goal_id: int, request: Request, user_id: User):
    with request.app.state.pool.connection() as db:
        goal = owned_goal(db, goal_id, user_id)

    if goal["goalType"] == "weight":
        return weight_status(request, user_id, goal)
    return workout_status(request, user_id, goal)


@app.put("/api/goals/{goal_id}", response_model=Goal)
def replace_goal(goal_id: int, goal: GoalInput, user_id: User, db: Database):
    owned_goal(db, goal_id, user_id, for_update=True)
    return update_goal(db, goal_id, goal)


@app.patch("/api/goals/{goal_id}", response_model=Goal)
def edit_goal(goal_id: int, goal: GoalPatch, user_id: User, db: Database):
    changes = goal.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "Provide at least one field to update")
    current = owned_goal(db, goal_id, user_id, for_update=True)
    fields = {key: current[key] for key in ("goalType", "target", "startWeightKg")}
    try:
        updated = GoalInput.model_validate({**fields, **changes})
    except ValidationError as error:
        raise HTTPException(400, error.errors()[0]["msg"]) from None
    return update_goal(db, goal_id, updated)


@app.delete("/api/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, user_id: User, db: Database):
    owned_goal(db, goal_id, user_id, for_update=True)
    db.execute("DELETE FROM goals WHERE id = %s", (goal_id,))
    return Response(status_code=204)


@app.post("/api/goals/{goal_id}/reminders", response_model=Reminder, status_code=201)
def add_reminder(goal_id: int, reminder: ReminderInput, user_id: User, db: Database):
    owned_goal(db, goal_id, user_id, for_update=True)
    return db.execute(
        f"""
        INSERT INTO goal_reminders (goal_id, day_of_week, reminder_time, enabled)
        VALUES (%s, %s, %s, %s) RETURNING {REMINDER_COLUMNS}
        """,
        (goal_id, reminder.dayOfWeek, reminder.time, reminder.enabled),
    ).fetchone()


@app.put("/api/goals/{goal_id}/reminders/{reminder_id}", response_model=Reminder)
def replace_reminder(goal_id: int, reminder_id: int, reminder: ReminderInput, user_id: User, db: Database):
    owned_goal(db, goal_id, user_id, for_update=True)
    updated = db.execute(
        f"""
        UPDATE goal_reminders SET day_of_week = %s, reminder_time = %s, enabled = %s
        WHERE goal_id = %s AND id = %s RETURNING {REMINDER_COLUMNS}
        """,
        (reminder.dayOfWeek, reminder.time, reminder.enabled, goal_id, reminder_id),
    ).fetchone()
    if updated is None:
        raise HTTPException(404, "Reminder not found")
    return updated


@app.delete("/api/goals/{goal_id}/reminders/{reminder_id}", status_code=204)
def delete_reminder(goal_id: int, reminder_id: int, user_id: User, db: Database):
    owned_goal(db, goal_id, user_id, for_update=True)
    result = db.execute(
        "DELETE FROM goal_reminders WHERE goal_id = %s AND id = %s",
        (goal_id, reminder_id),
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Reminder not found")
    return Response(status_code=204)
