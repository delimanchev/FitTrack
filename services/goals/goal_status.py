from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, Request


def get_from_service(request: Request, user_id: str, url: str, token: str, params=None):
    try:
        return request.app.state.client.get(
            url,
            headers={"X-Service-Token": token, "X-User-Id": user_id},
            params=params,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Required service is unavailable") from None


def service_data(response: httpx.Response):
    if response.status_code != 200:
        raise HTTPException(503, "Required service is unavailable")
    try:
        return response.json()
    except ValueError:
        raise HTTPException(503, "Invalid response from required service") from None


def weight_status(request: Request, user_id: str, goal: dict):
    settings = request.app.state.settings
    response = get_from_service(
        request, user_id, settings["PROGRESS_SERVICE_URL"] + "/progress/latest",
        settings["GOALS_TO_PROGRESS_TOKEN"],
    )
    result = {"goalId": goal["id"], "target": goal["target"]}
    if response.status_code == 404:
        return {**result, "weightKg": None, "percent": None}

    data = service_data(response)
    current = data.get("weightKg") if isinstance(data, dict) else None
    if type(current) not in (int, float) or not 0 < current <= 1000:
        raise HTTPException(503, "Invalid weight from Progress Service")

    start = goal["startWeightKg"]
    fraction = (current - start) / (goal["target"] - start)
    percent = round(min(100, max(0, 100 * fraction)), 2)
    return {**result, "weightKg": current, "percent": percent}


def workout_status(request: Request, user_id: str, goal: dict):
    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(days=7)

    settings = request.app.state.settings
    response = get_from_service(
        request, user_id, settings["WORKOUT_SERVICE_URL"] + "/workouts/completed",
        settings["GOALS_TO_WORKOUT_TOKEN"],
        params={"from": monday.isoformat(), "to": next_monday.isoformat()},
    )
    workouts = service_data(response)
    if not isinstance(workouts, list) or not all(isinstance(item, dict) for item in workouts):
        raise HTTPException(503, "Invalid workout list from Workout Service")

    target = int(goal["target"])
    completed = len(workouts)
    return {
        "goalId": goal["id"], "target": target, "completed": completed,
        "percent": round(min(100, 100 * completed / target), 2),
    }
