# YouTube Analytics Dashboard

A self-hosted Flask web application that fetches YouTube channel statistics via the YouTube Data API and displays them in a sleek, responsive dashboard with interactive charts and reports.

## Features

- **Dashboard** — Overview with total views, likes, comments, top-performing video, and KPI cards
- **Analytics** — Interactive charts (line, doughnut, bar, bubble, polar area, timeline, engagement rates) built with Chart.js
- **Videos** — Video feed grid with live search/filter
- **Reports** — Performance leaders comparison, engagement leaderboard, key ratios, and AI diagnostics summary
- **Settings** — Configure Channel ID & API Key (saved to MySQL), dark/light theme toggle, share dashboard link
- **Authentication** — Login/signup with PBKDF2 password hashing stored in MySQL
- **Theme** — Dark and light mode with glassmorphic design, persisted via localStorage
- **Shareable** — Access from any device on your local network (supports mobile)

## Tech Stack

| Layer    | Technology |
|----------|-----------|
| Backend  | Python, Flask, MySQL Connector |
| Frontend | HTML, CSS (custom design system), Chart.js, Font Awesome |
| Database | MySQL (`youtube_analytics`) |
| API      | YouTube Data API v3 |
| Auth     | Session-based, PBKDF2-SHA256 password hashing |

## Prerequisites

- Python 3.10+
- MySQL server running locally
- YouTube Data API key ([get one here](https://console.cloud.google.com/apis/credentials))

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd youtube-analytics-dashboard

# Install dependencies
pip install flask mysql-connector-python google-api-python-client

# Set up MySQL database
mysql -u root -p
```

```sql
CREATE DATABASE youtube_analytics;
USE youtube_analytics;
CREATE TABLE youtube_videos (
    video_id VARCHAR(100) PRIMARY KEY,
    video_title VARCHAR(255),
    views INT,
    likes INT,
    comments INT,
    publish_date DATETIME
);
```

```bash
# Update DB credentials in app.py if needed
# DB_CONFIG = {"host": "localhost", "user": "root", "password": "yourpassword", "database": "youtube_analytics"}

# Run the app
python app.py
```

Open `http://localhost:5000` in your browser.

## Default Login

| Credential | Value |
|-----------|-------|
| Username  | `admin` |
| Password  | `admin123` |

Create additional accounts via the **Sign Up** tab on the login page.

## Usage

1. **Log in** with the default credentials
2. Go to **Settings** → enter your YouTube Channel ID and API Key → click **Save**
3. Click **Fetch Data** to pull the latest 10 videos from your channel
4. Navigate through Dashboard, Analytics, Videos, and Reports

### Finding Your Channel ID

- Go to your YouTube channel page
- The URL contains `channel/UC...` — that's your Channel ID
- Or use: `https://www.youtube.com/account_advanced`

### Sharing on Your Network

1. Go to **Settings** → **Share Dashboard**
2. Click **Get Link** → copy the URL
3. Open it on any device on the same Wi-Fi network

## File Structure

```
youtube-analytics-dashboard/
├── app.py                 # Flask server, routes, auth, DB helpers
├── youtube_dashboard.py   # Standalone YouTube data fetcher script
├── README.md
├── static/
│   └── style.css          # Full design system (dark/light, glassmorphism)
└── templates/
    ├── base.html          # Layout with sidebar, theme restore, nav highlight
    ├── login.html         # Login/signup page with tab switcher
    ├── index.html         # Dashboard with hero card, KPIs, featured video
    ├── analytics.html     # 7 interactive charts + performance table
    ├── videos.html        # Video feed grid with search
    ├── reports.html       # Performance leaders, leaderboard, ratios, AI summary
    └── settings.html      # Channel config, theme toggle, share card, fetch button
```

## Security Notes

- Passwords are hashed with PBKDF2-SHA256 (100,000 iterations) before storage
- API Key and Channel ID are stored in MySQL, not hardcoded in templates
- All dashboard routes require login (except login page)
- Session-based authentication with server-generated secret key
- Change the default admin password immediately after first login
- Use environment variables or a config file for production DB credentials