import json
import os
import unittest
from datetime import UTC, date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from main import app


SECRET = "goals-tests-only-key-at-least-32-bytes"
WEIGHT_GOAL = {"goalType": "weight", "target": 80, "startWeightKg": 90}
WORKOUT_GOAL = {"goalType": "weekly_workouts", "target": 4}
REMINDER = {"dayOfWeek": 1, "time": "08:30"}


class DependenciesStub(BaseHTTPRequestHandler):
    def do_GET(self):
        user_id = self.headers.get("X-User-Id", "")
        token = self.headers.get("X-Service-Token")
        self.server.last_request = (self.path, token, user_id)
        path = urlsplit(self.path).path
        if user_id.startswith("offline-"):
            return  # Close the connection before sending a response.
        if path == "/progress/latest" and token == "test-progress-token":
            if user_id.startswith("missing-"):
                self.send_response(404)
                self.end_headers()
                return
            payload = {"id": 1, "weightKg": 85, "measuredAt": "2026-11-28"}
        elif path == "/workouts/completed" and token == "test-workout-token":
            payload = [{"id": 1}, {"id": 2}, {"id": 3}]
        else:
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, format, *args):
        pass


class GoalsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = ThreadingHTTPServer(("127.0.0.1", 0), DependenciesStub)
        cls.addClassCleanup(cls.stub.server_close)
        thread = Thread(target=cls.stub.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(thread.join)
        cls.addClassCleanup(cls.stub.shutdown)
        base_url = f"http://127.0.0.1:{cls.stub.server_port}"
        cls.enterClassContext(patch.dict(os.environ, {
            "DATABASE_URL": os.environ["GOALS_TEST_DATABASE_URL"],
            "JWT_SECRET": SECRET,
            "JWT_ISSUER": "fittrack-test",
            "JWT_AUDIENCE": "fittrack-api-test",
            "PROGRESS_SERVICE_URL": base_url,
            "WORKOUT_SERVICE_URL": base_url,
            "GOALS_TO_PROGRESS_TOKEN": "test-progress-token",
            "GOALS_TO_WORKOUT_TOKEN": "test-workout-token",
        }))
        cls.client = cls.enterClassContext(TestClient(app))

    def setUp(self):
        self.user_id = str(uuid4())
        self.headers = self.auth(self.user_id)

    def auth(self, user_id, minutes=5):
        token = jwt.encode({
            "sub": user_id, "iss": "fittrack-test", "aud": "fittrack-api-test",
            "exp": datetime.now(UTC) + timedelta(minutes=minutes),
        }, SECRET, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def create_goal(self, data, headers=None):
        response = self.client.post("/api/goals", headers=headers or self.headers, json=data)
        self.assertEqual(response.status_code, 201, response.text)
        return f"/api/goals/{response.json()['id']}"

    def test_goal_and_reminder_crud_enforce_ownership(self):
        url = self.create_goal(WEIGHT_GOAL)
        other = self.auth(str(uuid4()))
        self.assertEqual(self.client.get("/api/goals", headers=other).json(), [])
        self.assertEqual(self.client.get(f"{url}/status", headers=other).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=other).status_code, 403)

        created = self.client.post(f"{url}/reminders", headers=self.headers, json=REMINDER)
        self.assertEqual(created.status_code, 201, created.text)
        reminder_id = created.json()["id"]
        reminder_url = f"{url}/reminders/{reminder_id}"
        self.assertEqual(self.client.put(reminder_url, headers=other, json=REMINDER).status_code, 403)
        changed = {**REMINDER, "time": "19:45", "enabled": False}
        edited = self.client.put(reminder_url, headers=self.headers, json=changed)
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json(), {**changed, "id": reminder_id})

        goal = self.client.get("/api/goals", headers=self.headers).json()[0]
        self.assertEqual(goal["reminders"], [edited.json()])
        put = self.client.put(url, headers=self.headers, json=WORKOUT_GOAL)
        self.assertEqual(put.status_code, 200)
        self.assertEqual(put.json()["goalType"], "weekly_workouts")
        patched = self.client.patch(url, headers=self.headers, json={"target": 5})
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["target"], 5)

        self.assertEqual(self.client.delete(reminder_url, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.delete(reminder_url, headers=self.headers).status_code, 404)
        self.assertEqual(self.client.delete(url, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get(f"{url}/status", headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get("/api/goals", headers=self.headers).json(), [])

    def test_weight_progress_in_both_directions_and_missing_measurement(self):
        url = self.create_goal(WEIGHT_GOAL)
        status = self.client.get(f"{url}/status", headers=self.headers)
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()["weightKg"], 85)
        self.assertEqual(status.json()["percent"], 50)
        self.assertEqual(self.stub.last_request, ("/progress/latest", "test-progress-token", self.user_id))
        self.client.put(url, headers=self.headers, json={**WEIGHT_GOAL, "startWeightKg": 80, "target": 90})
        self.assertEqual(self.client.get(f"{url}/status", headers=self.headers).json()["percent"], 50)
        self.client.patch(url, headers=self.headers, json={"target": 82})
        self.assertEqual(self.client.get(f"{url}/status", headers=self.headers).json()["percent"], 100)

        missing = self.auth("missing-" + self.user_id)
        missing_url = self.create_goal(WEIGHT_GOAL, missing)
        unavailable_weight = self.client.get(f"{missing_url}/status", headers=missing)
        self.assertEqual(unavailable_weight.status_code, 200)
        self.assertIsNone(unavailable_weight.json()["weightKg"])
        self.assertIsNone(unavailable_weight.json()["percent"])

    def test_weekly_goal_counts_workouts_for_the_utc_week(self):
        url = self.create_goal(WORKOUT_GOAL)
        response = self.client.get(f"{url}/status", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "goalId": int(url.split("/")[-1]), "target": 4, "completed": 3, "percent": 75,
        })
        path, token, user_id = self.stub.last_request
        self.assertEqual((token, user_id), ("test-workout-token", self.user_id))
        parsed = urlsplit(path)
        self.assertEqual(parsed.path, "/workouts/completed")
        query = parse_qs(parsed.query)
        start = date.fromisoformat(query["from"][0])
        end = date.fromisoformat(query["to"][0])
        self.assertEqual(start.weekday(), 0)
        self.assertEqual(end - start, timedelta(days=7))

    def test_validation_outages_and_openapi(self):
        self.assertEqual(self.client.get("/api/goals").status_code, 401)
        expired = self.auth(self.user_id, minutes=-5)
        self.assertEqual(self.client.get("/api/goals", headers=expired).status_code, 401)
        for bad in [
            {**WEIGHT_GOAL, "target": 90},
            {"goalType": "weight", "target": 80},
            {**WORKOUT_GOAL, "target": 3.5},
        ]:
            self.assertEqual(self.client.post("/api/goals", headers=self.headers, json=bad).status_code, 400)
        url = self.create_goal(WORKOUT_GOAL)
        self.assertEqual(self.client.patch(url, headers=self.headers, json={}).status_code, 400)
        self.assertEqual(self.client.post(
            f"{url}/reminders", headers=self.headers, json={**REMINDER, "time": "25:00"},
        ).status_code, 400)
        offline = self.auth("offline-" + self.user_id)
        for goal in (WEIGHT_GOAL, WORKOUT_GOAL):
            url = self.create_goal(goal, offline)
            self.assertEqual(self.client.get(f"{url}/status", headers=offline).status_code, 503)
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertEqual(set(paths["/api/goals"]), {"get", "post"})
        self.assertEqual(set(paths["/api/goals/{goal_id}"]), {"put", "patch", "delete"})
        self.assertEqual(set(paths["/api/goals/{goal_id}/status"]), {"get"})
        self.assertEqual(set(paths["/api/goals/{goal_id}/reminders"]), {"post"})
        self.assertEqual(set(paths["/api/goals/{goal_id}/reminders/{reminder_id}"]), {"put", "delete"})
        self.assertNotIn("422", paths["/api/goals"]["post"]["responses"])
