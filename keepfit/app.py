import os
import sqlite3
import uuid
from datetime import date, datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, request

load_dotenv()

app = Flask(__name__)
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "0") == "1"
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keepfit.db")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open a new database connection with row factory."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bmi_entries (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT    NOT NULL DEFAULT 'anonymous',
            height    REAL    NOT NULL,
            weight    REAL    NOT NULL,
            bmi_value REAL    NOT NULL,
            date      TEXT    NOT NULL DEFAULT (date('now')),
            notes     TEXT
        );

        CREATE TABLE IF NOT EXISTS calorie_entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT    NOT NULL DEFAULT 'anonymous',
            date       TEXT    NOT NULL,
            calories   INTEGER NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             TEXT    NOT NULL DEFAULT 'anonymous',
            height              REAL    NOT NULL,
            current_weight      REAL    NOT NULL,
            target_weight       REAL    NOT NULL,
            target_date         TEXT    NOT NULL,
            activity_level      TEXT    NOT NULL,
            gender              TEXT    NOT NULL,
            age                 INTEGER NOT NULL DEFAULT 25,
            recommended_calories INTEGER NOT NULL,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def ensure_user_id(response=None):
    """Ensure the request has a user_id cookie; set one if missing."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
    if response is not None:
        response.set_cookie("user_id", user_id, max_age=365 * 24 * 3600)
    return user_id


# ---------------------------------------------------------------------------
# BMI helpers
# ---------------------------------------------------------------------------

def calculate_bmi(height_cm, weight_kg):
    """Return BMI value rounded to 2 decimals."""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 2)


def bmi_category(bmi):
    """Return human-readable BMI category."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"


# ---------------------------------------------------------------------------
# Recommendation helpers (Version 2)
# ---------------------------------------------------------------------------

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
}


def calculate_bmr(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor equation."""
    if gender == "female":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def calculate_recommendation(height_cm, current_weight, target_weight,
                              target_date_str, activity_level, gender, age=25):
    """Return personalized calorie recommendation dict."""
    current_bmi = calculate_bmi(height_cm, current_weight)
    current_cat = bmi_category(current_bmi)

    bmr = calculate_bmr(current_weight, height_cm, age, gender)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    tdee = round(bmr * multiplier)

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    today = date.today()
    days = (target_date - today).days
    if days <= 0:
        return None

    weight_change = target_weight - current_weight
    daily_adjustment = (weight_change * 7700) / days
    daily_calories = round(tdee + daily_adjustment)

    weekly_change = round(weight_change / (days / 7), 2)

    if daily_calories < 1200:
        recommendation = (
            f"Warning: {daily_calories} kcal/day is below the safe minimum (1200). "
            f"Consider extending your target date or adjusting your goal."
        )
    elif weight_change > 0:
        recommendation = (
            f"To gain {abs(weight_change):.1f} kg by {target_date_str}, "
            f"eat {daily_calories} kcal/day (+{abs(daily_adjustment):.0f} above maintenance). "
            f"Expected weekly gain: +{abs(weekly_change):.2f} kg."
        )
    elif weight_change < 0:
        recommendation = (
            f"To lose {abs(weight_change):.1f} kg by {target_date_str}, "
            f"eat {daily_calories} kcal/day (-{abs(daily_adjustment):.0f} below maintenance). "
            f"Expected weekly loss: -{abs(weekly_change):.2f} kg."
        )
    else:
        recommendation = (
            f"Your target weight matches your current weight. "
            f"Maintain at {tdee} kcal/day."
        )

    return {
        "current_bmi": current_bmi,
        "current_bmi_category": current_cat,
        "tdee": tdee,
        "daily_calories_needed": daily_calories,
        "weekly_change_kg": weekly_change,
        "recommendation_text": recommendation,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main page with a user_id cookie."""
    resp = make_response(render_template("index.html"))
    ensure_user_id(resp)
    return resp


@app.route("/api/bmi", methods=["POST"])
def post_bmi():
    """Accept {height, weight, notes?}, calculate BMI, save, return result."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    height = data.get("height")
    weight = data.get("weight")
    notes = data.get("notes", "")

    if height is None or weight is None:
        return jsonify({"error": "height and weight are required"}), 400

    try:
        height = float(height)
        weight = float(weight)
    except (TypeError, ValueError):
        return jsonify({"error": "height and weight must be numbers"}), 400

    if height <= 0 or weight <= 0:
        return jsonify({"error": "height and weight must be positive"}), 400

    bmi_val = calculate_bmi(height, weight)
    category = bmi_category(bmi_val)
    user_id = ensure_user_id()

    conn = get_db()
    conn.execute(
        "INSERT INTO bmi_entries (user_id, height, weight, bmi_value, notes) VALUES (?, ?, ?, ?, ?)",
        (user_id, height, weight, bmi_val, notes),
    )
    conn.commit()
    conn.close()

    return jsonify({"bmi": bmi_val, "category": category})


@app.route("/api/calories", methods=["POST"])
def post_calories():
    """Accept {date, calories}, save, return success + today's total."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    entry_date = data.get("date")
    calories = data.get("calories")

    if entry_date is None or calories is None:
        return jsonify({"error": "date and calories are required"}), 400

    try:
        calories = int(calories)
    except (TypeError, ValueError):
        return jsonify({"error": "calories must be an integer"}), 400

    # Validate date format YYYY-MM-DD
    try:
        datetime.strptime(entry_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400

    user_id = ensure_user_id()

    conn = get_db()
    conn.execute(
        "INSERT INTO calorie_entries (user_id, date, calories) VALUES (?, ?, ?)",
        (user_id, entry_date, calories),
    )
    conn.commit()

    # Today's total (for this user)
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(calories), 0) AS total FROM calorie_entries WHERE date = ? AND user_id = ?",
        (today, user_id),
    ).fetchone()
    today_total = row["total"]

    # Last 10 calorie entries (for this user)
    rows = conn.execute(
        "SELECT id, date, calories FROM calorie_entries WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,),
    ).fetchall()
    recent = [{"id": r["id"], "date": r["date"], "calories": r["calories"]} for r in rows]

    conn.close()

    return jsonify({"success": True, "today_total": today_total, "recent": recent})


@app.route("/api/history", methods=["GET"])
def get_history():
    """Return last 10 BMI entries and last 10 calorie entries for this user."""
    user_id = ensure_user_id()
    conn = get_db()

    bmi_rows = conn.execute(
        "SELECT id, height, weight, bmi_value, date, notes FROM bmi_entries WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,),
    ).fetchall()
    bmi_history = [
        {"id": r["id"], "height": r["height"], "weight": r["weight"],
         "bmi": r["bmi_value"], "date": r["date"], "notes": r["notes"]}
        for r in bmi_rows
    ]

    cal_rows = conn.execute(
        "SELECT id, date, calories FROM calorie_entries WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,),
    ).fetchall()
    cal_history = [
        {"id": r["id"], "date": r["date"], "calories": r["calories"]}
        for r in cal_rows
    ]

    conn.close()

    return jsonify({"bmi": bmi_history, "calories": cal_history})


@app.route("/api/recommendation", methods=["POST"])
def post_recommendation():
    """Accept user params, calculate calorie recommendation, save, return result."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    height = data.get("height_cm")
    current_weight = data.get("current_weight_kg")
    target_weight = data.get("target_weight_kg")
    target_date = data.get("target_date")
    activity_level = data.get("activity_level")
    gender = data.get("gender")
    age = data.get("age", 25)

    if not all([height, current_weight, target_weight, target_date, activity_level, gender]):
        return jsonify({"error": "All fields except age are required"}), 400

    if gender not in ("male", "female"):
        return jsonify({"error": "gender must be 'male' or 'female'"}), 400

    if activity_level not in ACTIVITY_MULTIPLIERS:
        return jsonify({"error": f"activity_level must be one of: {', '.join(ACTIVITY_MULTIPLIERS)}"}), 400

    try:
        height = float(height)
        current_weight = float(current_weight)
        target_weight = float(target_weight)
        age = int(age)
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric fields must be valid numbers"}), 400

    result = calculate_recommendation(height, current_weight, target_weight,
                                       target_date, activity_level, gender, age)
    if result is None:
        return jsonify({"error": "Target date must be in the future"}), 400

    user_id = ensure_user_id()
    conn = get_db()
    conn.execute(
        "INSERT INTO recommendations (user_id, height, current_weight, target_weight, "
        "target_date, activity_level, gender, age, recommended_calories) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, height, current_weight, target_weight, target_date,
         activity_level, gender, age, result["daily_calories_needed"]),
    )
    conn.commit()
    conn.close()

    return jsonify(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="0.0.0.0", port=port)
