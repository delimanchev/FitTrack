import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from main import app


SECRET = "nutrition-tests-only-secret-32-bytes"
DAY = "2026-11-28"
MEAL = {"name": "Lunch", "meal_date": DAY}
ITEM = {
    "name": "Rice", "quantity": 2, "calories": 130,
    "protein": 3, "carbs": 28, "fat": 1,
}


class UserStub(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.last_request = (self.path, self.headers.get("X-Service-Token"))
        if self.headers.get("X-Service-Token") != "nutrition-test-token":
            status = 403
        elif self.path.startswith("/users/missing-"):
            status = 404
        elif self.path.startswith("/users/offline-"):
            return  # Close the connection before sending a response.
        else:
            status = 200
        self.send_response(status)
        self.end_headers()

    def log_message(self, format, *args):
        pass


class NutritionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user_server = ThreadingHTTPServer(("127.0.0.1", 0), UserStub)
        cls.addClassCleanup(cls.user_server.server_close)
        thread = Thread(target=cls.user_server.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(thread.join)
        cls.addClassCleanup(cls.user_server.shutdown)
        cls.enterClassContext(patch.dict(os.environ, {
            "DATABASE_URL": os.environ["NUTRITION_TEST_DATABASE_URL"],
            "JWT_SECRET": SECRET,
            "JWT_ISSUER": "fittrack-test",
            "JWT_AUDIENCE": "fittrack-api-test",
            "USER_SERVICE_URL": f"http://127.0.0.1:{cls.user_server.server_port}",
            "NUTRITION_TO_USER_TOKEN": "nutrition-test-token",
            "USER_TO_NUTRITION_TOKEN": "user-test-token",
        }))
        cls.client = cls.enterClassContext(TestClient(app))

    def setUp(self):
        self.user_id = str(uuid4())
        self.headers = self.auth(self.user_id)

    def auth(self, user_id, expires_in_minutes=5):
        token = jwt.encode({
            "sub": user_id,
            "iss": "fittrack-test",
            "aud": "fittrack-api-test",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        }, SECRET, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def create_meal(self, **changes):
        response = self.client.post("/api/meals", headers=self.headers, json={**MEAL, **changes})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_meal_crud_filters_and_ownership(self):
        meal = self.create_meal()
        url = f"/api/meals/{meal['id']}"
        self.assertEqual(
            self.user_server.last_request, (f"/users/{self.user_id}", "nutrition-test-token")
        )
        self.create_meal(meal_date="2026-11-27")
        response = self.client.get("/api/meals", params={"date": DAY}, headers=self.headers)
        self.assertEqual([row["id"] for row in response.json()], [meal["id"]])
        updated = self.client.put(url, headers=self.headers, json={**MEAL, "name": "Dinner"})
        self.assertEqual(updated.json()["name"], "Dinner")
        patched = self.client.patch(url, headers=self.headers, json={"name": "Snack"})
        self.assertEqual(patched.json()["meal_date"], DAY)
        self.assertEqual(self.client.get(url, headers=self.headers).json()["name"], "Snack")
        other_user = self.auth(str(uuid4()))
        self.assertEqual(self.client.get(url, headers=other_user).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=other_user).status_code, 403)
        self.assertEqual(self.client.get("/api/meals", headers=other_user).json(), [])
        self.assertEqual(self.client.delete(url, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get(url, headers=self.headers).status_code, 404)

    def test_items_and_totals(self):
        meal = self.create_meal(items=[ITEM])
        url = f"/api/meals/{meal['id']}"
        self.assertEqual(meal["totals"], {"calories": 260, "protein": 6, "carbs": 56, "fat": 2})
        created = self.client.post(f"{url}/items", headers=self.headers, json=ITEM)
        self.assertEqual(created.status_code, 201)
        item_url = f"{url}/items/{created.json()['id']}"
        edited = self.client.put(item_url, headers=self.headers, json={**ITEM, "quantity": 1})
        self.assertEqual(edited.status_code, 200, edited.text)
        details = self.client.get(url, headers=self.headers).json()
        self.assertEqual(details["totals"], {"calories": 390, "protein": 9, "carbs": 84, "fat": 3})
        other_meal = self.create_meal()
        wrong_url = f"/api/meals/{other_meal['id']}/items/{created.json()['id']}"
        self.assertEqual(self.client.delete(wrong_url, headers=self.headers).status_code, 404)
        self.assertEqual(self.client.delete(item_url, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get(url, headers=self.headers).json()["totals"]["calories"], 260)
        self.assertEqual(self.client.delete(url, headers=self.headers).status_code, 204)

    def test_invalid_input_and_unavailable_user_service(self):
        self.assertEqual(self.client.get("/api/meals").status_code, 401)
        expired = self.auth(self.user_id, expires_in_minutes=-5)
        self.assertEqual(self.client.get("/api/meals", headers=expired).status_code, 401)
        bad_meal = {**MEAL, "items": [{**ITEM, "quantity": 0}]}
        self.assertEqual(self.client.post("/api/meals", headers=self.headers, json=bad_meal).status_code, 400)
        for prefix, status in (("missing-", 404), ("offline-", 503)):
            headers = self.auth(prefix + self.user_id)
            response = self.client.post("/api/meals", headers=headers, json=MEAL)
            self.assertEqual(response.status_code, status, response.text)
            self.assertEqual(self.client.get("/api/meals", headers=headers).json(), [])

    def test_internal_summary_and_openapi(self):
        self.create_meal()
        self.create_meal(meal_date="2026-11-27")
        headers = {"X-Service-Token": "user-test-token", "X-User-Id": self.user_id}
        url = f"/meals/summary?date={DAY}"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(url, headers={"X-Service-Token": "user-test-token"}).status_code, 400)
        self.assertEqual(self.client.get(url, headers=headers).json(), {"date": DAY, "meal_count": 1})
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        self.assertEqual(set(paths["/api/meals"]), {"get", "post"})
        self.assertEqual(set(paths["/api/meals/{meal_id}"]), {"get", "put", "patch", "delete"})
        self.assertEqual(set(paths["/api/meals/{meal_id}/items"]), {"post"})
        self.assertEqual(set(paths["/api/meals/{meal_id}/items/{item_id}"]), {"put", "delete"})
        self.assertIn("get", paths["/meals/summary"])
        self.assertNotIn("422", paths["/api/meals"]["post"]["responses"])
