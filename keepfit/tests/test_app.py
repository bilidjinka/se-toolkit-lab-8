"""Tests for KeepFit Flask app."""
import os
import sqlite3
import tempfile
import unittest
import uuid

from app import app, init_db


class KeepFitTestCase(unittest.TestCase):
    """Test cases for BMI and calorie endpoints."""

    def setUp(self):
        """Create a temporary test database for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        app.config["DATABASE"] = self.db_path
        import app as app_module
        self.original_db = app_module.DATABASE
        app_module.DATABASE = self.db_path
        init_db()
        self.client = app.test_client()
        self.user_id = str(uuid.uuid4())
        self.client.set_cookie("user_id", self.user_id, domain="localhost")

    def tearDown(self):
        """Clean up the test database."""
        import app as app_module
        app_module.DATABASE = self.original_db
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _post_bmi(self, **kwargs):
        """Helper: POST /api/bmi."""
        return self.client.post("/api/bmi", json=kwargs)

    def _post_calories(self, **kwargs):
        """Helper: POST /api/calories."""
        return self.client.post("/api/calories", json=kwargs)

    # ---- Test 1: BMI calculation ----
    def test_bmi_normal(self):
        """Height 175 cm, weight 70 kg → BMI ≈ 22.86 (Normal)."""
        resp = self._post_bmi(height=175, weight=70)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertAlmostEqual(data["bmi"], 22.86, places=1)
        self.assertEqual(data["category"], "Normal")

    def test_bmi_underweight(self):
        """Height 170 cm, weight 45 kg → BMI ≈ 15.57 (Underweight)."""
        resp = self._post_bmi(height=170, weight=45)
        data = resp.get_json()
        self.assertEqual(data["category"], "Underweight")

    def test_bmi_overweight(self):
        """Height 170 cm, weight 90 kg → BMI ≈ 31.14 (Obese)."""
        resp = self._post_bmi(height=170, weight=90)
        data = resp.get_json()
        self.assertEqual(data["category"], "Obese")

    def test_bmi_missing_fields(self):
        """Missing height → 400 error."""
        resp = self._post_bmi(weight=70)
        self.assertEqual(resp.status_code, 400)

    def test_bmi_negative_values(self):
        """Negative height → 400 error."""
        resp = self._post_bmi(height=-175, weight=70)
        self.assertEqual(resp.status_code, 400)

    # ---- Test 2: Calorie logging ----
    def test_calories_log(self):
        """Log 550 calories for today → saved and returned in recent list."""
        resp = self._post_calories(date="2026-04-05", calories=550)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["today_total"], 550)
        self.assertEqual(len(data["recent"]), 1)
        self.assertEqual(data["recent"][0]["calories"], 550)

    def test_calories_invalid_date(self):
        """Invalid date format → 400 error."""
        resp = self._post_calories(date="05-04-2026", calories=550)
        self.assertEqual(resp.status_code, 400)

    def test_calories_non_integer(self):
        """Non-integer calories → 400 error."""
        resp = self._post_calories(date="2026-04-05", calories="abc")
        self.assertEqual(resp.status_code, 400)

    # ---- Test 3: Database persistence via /api/history ----
    def test_history_returns_entries(self):
        """After posting BMI and calorie entries, /api/history returns them."""
        self._post_bmi(height=180, weight=80)
        self._post_calories(date="2026-04-05", calories=2000)

        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["bmi"]), 1)
        self.assertAlmostEqual(data["bmi"][0]["bmi"], 24.69, places=1)
        self.assertEqual(len(data["calories"]), 1)
        self.assertEqual(data["calories"][0]["calories"], 2000)

    def test_history_isolated_per_user(self):
        """Different users see different histories."""
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        client_a = app.test_client()
        client_a.set_cookie("user_id", user_a, domain="localhost")
        client_b = app.test_client()
        client_b.set_cookie("user_id", user_b, domain="localhost")

        client_a.post("/api/bmi", json={"height": 175, "weight": 70})
        client_b.post("/api/bmi", json={"height": 180, "weight": 90})

        resp_a = client_a.get("/api/history")
        resp_b = client_b.get("/api/history")

        self.assertEqual(resp_a.get_json()["bmi"][0]["bmi"], 22.86)
        self.assertEqual(resp_b.get_json()["bmi"][0]["bmi"], 27.78)

    # ---- Index page ----
    def test_index(self):
        """GET / returns 200 with HTML content and sets user_id cookie."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"KeepFit", resp.data)
        self.assertIn("user_id", resp.headers.get("Set-Cookie", ""))

    # ---- Test V2: Recommendation ----
    def test_recommendation_weight_loss(self):
        """Male, 175cm, 80kg → 70kg in 90 days, moderately active."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 175,
            "current_weight_kg": 80,
            "target_weight_kg": 70,
            "target_date": "2026-07-04",
            "activity_level": "moderately_active",
            "gender": "male",
            "age": 30,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertAlmostEqual(data["current_bmi"], 26.12, places=1)
        self.assertEqual(data["current_bmi_category"], "Overweight")
        self.assertGreater(data["tdee"], 0)
        self.assertGreater(data["daily_calories_needed"], 0)
        self.assertLess(data["weekly_change_kg"], 0)  # losing weight
        self.assertIn("lose", data["recommendation_text"].lower())

    def test_recommendation_weight_gain(self):
        """Female, 165cm, 50kg → 55kg in 120 days, lightly active."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 165,
            "current_weight_kg": 50,
            "target_weight_kg": 55,
            "target_date": "2026-08-03",
            "activity_level": "lightly_active",
            "gender": "female",
            "age": 22,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["weekly_change_kg"], 0)  # gaining weight
        self.assertIn("gain", data["recommendation_text"].lower())

    def test_recommendation_default_age(self):
        """Age defaults to 25 if not provided."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 180,
            "current_weight_kg": 75,
            "target_weight_kg": 75,
            "target_date": "2027-01-01",
            "activity_level": "sedentary",
            "gender": "male",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("maintain", data["recommendation_text"].lower())

    def test_recommendation_past_date(self):
        """Past target date → 400 error."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 175,
            "current_weight_kg": 80,
            "target_weight_kg": 70,
            "target_date": "2020-01-01",
            "activity_level": "sedentary",
            "gender": "male",
        })
        self.assertEqual(resp.status_code, 400)

    def test_recommendation_missing_fields(self):
        """Missing required field → 400 error."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 175,
            "current_weight_kg": 80,
        })
        self.assertEqual(resp.status_code, 400)

    def test_recommendation_invalid_gender(self):
        """Invalid gender → 400 error."""
        resp = self.client.post("/api/recommendation", json={
            "height_cm": 175,
            "current_weight_kg": 80,
            "target_weight_kg": 70,
            "target_date": "2027-01-01",
            "activity_level": "sedentary",
            "gender": "other",
        })
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
