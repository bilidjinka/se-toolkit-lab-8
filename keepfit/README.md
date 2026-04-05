# KeepFit

A simple BMI calculator and daily calorie tracker with personalized calorie recommendations.

## Demo

![BMI Calculator and Calorie Logger](docs/screenshots/bmi-calories.png)
*Main page: BMI Calculator and Calorie Logger sections.*

![Calorie Target Planner](docs/screenshots/planner.png)
*Calorie Target Planner: personalized daily calorie recommendation.*

> **Note:** Replace the placeholder screenshots above with actual screenshots of your running app.
> Take them with: open the app in browser → screenshot the page → save to `docs/screenshots/`.

## Product Context

**End users:** Sportsmen and people who track their eating habits.

**Problem:** People may not need a full calorie-tracking app. They may want to quickly check their BMI, log daily calories, or get a personalized calorie target — without installing heavy apps or creating accounts.

**Solution:** A lightweight web tool that does three things well:

1. Calculates BMI and saves measurements
2. Logs daily calorie intake with a running total
3. Recommends a daily calorie target based on the user's goal (target weight + date)

## Features

### Implemented (V1 + V2)

| Feature | Description |
|---|---|
| **BMI Calculator** | Enter height (cm) and weight (kg) → get BMI value and category (underweight / normal / overweight / obese). Saved to database. |
| **Calorie Logger** | Log calories with a date picker. Shows today's total and last 10 entries. |
| **Personal History** | Each browser gets its own private history (cookie-based user ID). No login required. |
| **Calorie Target Planner** | Personalized daily calorie recommendation based on BMR (Mifflin-St Jeor), TDEE, activity level, target weight, and target date. Shows expected weekly change and safe-calorie warnings. |
| **Responsive UI** | Clean, mobile-friendly interface. No external frameworks. |
| **Docker support** | Production-ready Dockerfile for easy deployment. |

### Not yet implemented

| Feature | Description |
|---|---|
| **Charts / graphs** | Visual calorie and BMI trends over time. |
| **User accounts** | Login/password for cross-device history sync. |
| **Export data** | Download history as CSV. |
| **Meal logging** | Log individual meals instead of daily totals. |
| **Water intake tracker** | Track daily water consumption. |

## Usage

### Local development

```bash
# 1. Clone and enter the project
cd keepfit

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python3 app.py
```

Open **<http://localhost:5000>** in your browser.

### API Endpoints

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| `GET` | `/` | — | Main HTML page |
| `POST` | `/api/bmi` | `{height, weight, notes?}` | `{bmi, category}` |
| `POST` | `/api/calories` | `{date, calories}` | `{success, today_total, recent}` |
| `GET` | `/api/history` | — | `{bmi: [...], calories: [...]}` |
| `POST` | `/api/recommendation` | `{height_cm, current_weight_kg, target_weight_kg, target_date, activity_level, gender, age?}` | `{current_bmi, current_bmi_category, tdee, daily_calories_needed, weekly_change_kg, recommendation_text}` |

### Testing

```bash
python3 -m unittest tests/test_app.py -v
```

17 tests cover all endpoints, validation, and user isolation.

## Deployment

### Target environment

- **OS:** Ubuntu 24.04 LTS (same as university VMs)
- **Docker:** 24+ (with `docker compose` plugin)
- **Python:** 3.9+ (for local development only)
- **Cloudflare:** `cloudflared` binary for public tunnel (optional)

### Step-by-step deployment on a fresh VM

#### 1. Install Docker

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
```

#### 2. Copy project files to the VM

```bash
# From your local machine:
scp -r keepfit/ root@<vm-ip>:/opt/keepfit/
```

Or clone from Git if the repo is pushed:

```bash
ssh root@<vm-ip>
git clone <repo-url> /opt/keepfit
cd /opt/keepfit/keepfit
```

#### 3. Build and run the Docker container

```bash
cd /opt/keepfit
docker build -t keepfit .
docker run -d \
  --name keepfit \
  -p 5000:5000 \
  --restart unless-stopped \
  keepfit
```

The app is now available at `http://<vm-ip>:5000`.

#### 4. (Optional) Set up a public URL with Cloudflare Tunnel

```bash
# Download cloudflared
curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /tmp/cloudflared
chmod +x /tmp/cloudflared

# Start the tunnel (runs in background)
nohup /tmp/cloudflared tunnel --url http://127.0.0.1:5000 > /tmp/cf-keepfit.log 2>&1 &

# Get the public URL
grep 'trycloudflare' /tmp/cf-keepfit.log
```

This gives you a URL like `https://xxxx-xxxx-xxxx-xxxx.trycloudflare.com` accessible from anywhere.

#### 5. Verify

```bash
# Check container is running
docker ps --filter name=keepfit

# Test the API
curl -s http://localhost:5000/api/bmi \
  -H "Content-Type: application/json" \
  -d '{"height":175,"weight":70}'
# Expected: {"bmi":22.86,"category":"Normal"}
```

### Updating the app

```bash
cd /opt/keepfit
# Update files (git pull or scp)
docker rm -f keepfit
docker build -t keepfit .
docker run -d --name keepfit -p 5000:5000 --restart unless-stopped keepfit
# Restart cloudflared tunnel if needed
pkill -f cloudflared
nohup /tmp/cloudflared tunnel --url http://127.0.0.1:5000 > /tmp/cf-keepfit.log 2>&1 &
```

## Project structure

```
keepfit/
├── app.py              # Flask backend: routes, DB logic, recommendation engine
├── Dockerfile          # Production-ready Docker image
├── requirements.txt    # Python dependencies (flask, python-dotenv)
├── README.md           # This file
├── .gitignore          # Ignores venv, .db, .env, __pycache__
├── .env.example        # Environment variable template
├── templates/
│   └── index.html      # Single-page app with forms and fetch API
├── static/
│   └── style.css       # Clean, responsive styles (no frameworks)
└── tests/
    └── test_app.py     # 17 unit tests (V1 + V2)
```
