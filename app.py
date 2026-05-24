from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import mysql.connector
import os
import hashlib
import secrets
import socket

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "merajaan102@",
    "database": "youtube_analytics"
}


# PASSWORD HELPERS (stdlib only — no external deps)

def hash_password(password):
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + pwd_hash.hex()

def check_password(password, stored):
    try:
        salt_hex, hash_hex = stored.split(':')
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return secrets.compare_digest(pwd_hash.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# DATABASE HELPERS

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


def init_users_table():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        new_hash = hash_password("admin123")
        if admin is None:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                ("admin", new_hash)
            )
            conn.commit()
            print("Default user 'admin' created")
        elif not check_password("admin123", admin['password_hash']):
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = 'admin'",
                (new_hash,)
            )
            conn.commit()
            print("Admin password hash updated to new format")
        cursor.close()
        conn.close()
    except Exception as e:
        print("DB init error:", e)


# LOGIN REQUIRED DECORATOR

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_videos():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM youtube_videos")
    videos = cursor.fetchall()
    cursor.close()
    conn.close()

    return videos


init_users_table()


# LOGIN PAGE

@app.route('/login', methods=['GET', 'POST'])

def login():

    if request.method == 'POST':
        session.clear()
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            print("Login DB error:", e)
            return render_template('login.html', error="Database error. Try again.")

        if user and check_password(password, user['password_hash']):
            session['logged_in'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")

    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    return render_template('login.html')


# SIGNUP PAGE

@app.route('/signup', methods=['GET', 'POST'])

def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if not username or not password:
            return render_template('login.html', error="All fields are required.", signup=True)
        if password != confirm:
            return render_template('login.html', error="Passwords do not match.", signup=True)
        if len(password) < 4:
            return render_template('login.html', error="Password must be at least 4 characters.", signup=True)

        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return render_template('login.html', error="Username already taken.", signup=True)

            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hash_password(password))
            )
            conn.commit()
            cursor.close()
            conn.close()
            return render_template('login.html', signup_ok="Account created! Sign in below.")
        except Exception as e:
            print("Signup error:", e)
            return render_template('login.html', error="Database error. Try again.", signup=True)

    return render_template('login.html', signup=True)


# LOGOUT

@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('login'))


# DASHBOARD PAGE

@app.route('/')

@login_required

def dashboard():

    videos = get_videos()

    total_views = sum(video['views'] for video in videos)
    total_likes = sum(video['likes'] for video in videos)
    total_comments = sum(video['comments'] for video in videos)

    return render_template(
        'index.html',
        videos=videos,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments
    )


# ANALYTICS PAGE

@app.route('/analytics')

@login_required

def analytics():

    videos = get_videos()

    total_views = sum(video['views'] for video in videos)
    total_likes = sum(video['likes'] for video in videos)
    total_comments = sum(video['comments'] for video in videos)

    return render_template(
        'analytics.html',
        videos=videos,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments
    )


# VIDEOS PAGE

@app.route('/videos')

@login_required

def videos_page():

    videos = get_videos()

    return render_template(
        'videos.html',
        videos=videos
    )


# REPORTS PAGE

@app.route('/reports')

@login_required

def reports():

    videos = get_videos()
    n = len(videos)
    if n == 0:
        return render_template('reports.html', videos=[], empty=True)

    # TOTALS

    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)

    # AVERAGES

    avg_views = round(total_views / n)
    avg_likes = round(total_likes / n)
    avg_comments = round(total_comments / n)

    # TOP / LOWEST BY VIEWS

    top_video = max(videos, key=lambda x: x['views'])
    lowest_video = min(videos, key=lambda x: x['views'])
    most_liked = max(videos, key=lambda x: x['likes'])

    # ENGAGEMENT

    engagement_rate = round(((total_likes + total_comments) / total_views) * 100, 2)

    for v in videos:
        v['engagement_rate'] = round(((v['likes'] + v['comments']) / v['views']) * 100, 2)

    videos_by_engagement = sorted(videos, key=lambda x: x['engagement_rate'], reverse=True)

    top_engagement = videos_by_engagement[0] if videos_by_engagement else None
    avg_engagement = round(sum(v['engagement_rate'] for v in videos) / n, 2)

    # RATIOS

    likes_per_view = round(total_likes / total_views, 4)
    comments_per_view = round(total_comments / total_views, 4)

    return render_template(

        'reports.html',

        videos=videos,
        n=n,

        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,

        avg_views=avg_views,
        avg_likes=avg_likes,
        avg_comments=avg_comments,

        top_video=top_video,
        most_liked=most_liked,
        lowest_video=lowest_video,

        engagement_rate=engagement_rate,
        videos_by_engagement=videos_by_engagement,
        top_engagement=top_engagement,
        avg_engagement=avg_engagement,

        likes_per_view=likes_per_view,
        comments_per_view=comments_per_view,

        empty=False
    )

DEFAULT_CHANNEL_ID = "UC2pIWZxKrWhNNzbxEjBnP7w"
DEFAULT_API_KEY = "AIzaSyD7ebL023x73FynVFqrDFKRNspKvAuOFwM"

def init_settings_table():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                channel_id VARCHAR(255) NOT NULL DEFAULT '',
                api_key VARCHAR(255) NOT NULL DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM channel_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO channel_config (channel_id, api_key) VALUES (%s, %s)",
                (DEFAULT_CHANNEL_ID, DEFAULT_API_KEY)
            )
            conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Settings table init error:", e)


def load_channel_config():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT channel_id, api_key FROM channel_config LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {
                "channel_id": row["channel_id"] or DEFAULT_CHANNEL_ID,
                "api_key": row["api_key"] or DEFAULT_API_KEY
            }
        return {"channel_id": DEFAULT_CHANNEL_ID, "api_key": DEFAULT_API_KEY}
    except:
        return {"channel_id": DEFAULT_CHANNEL_ID, "api_key": DEFAULT_API_KEY}


init_settings_table()


# SETTINGS PAGE

@app.route('/settings', methods=['GET', 'POST'])

@login_required

def settings():

    if request.method == 'POST':
        channel_id = request.form.get('channel_id', '')
        api_key = request.form.get('api_key', '')
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE channel_config SET channel_id = %s, api_key = %s WHERE id = 1", (channel_id, api_key))
            conn.commit()
            cursor.close()
            conn.close()
            return render_template('settings.html', config={"channel_id": channel_id, "api_key": api_key}, saved=True)
        except Exception as e:
            print("Save settings error:", e)

    config = load_channel_config()
    return render_template('settings.html', config=config)





# FETCH YOUTUBE DATA

@app.route('/fetch-data')

@login_required

def fetch_youtube_data():
    from googleapiclient.discovery import build
    from datetime import datetime

    config = load_channel_config()
    api_key = config.get("api_key")
    channel_id = config.get("channel_id")

    if not api_key or not channel_id:
        return jsonify({"success": False, "error": "Channel ID or API Key not configured."})

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        search_request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=10,
            order="date",
            type="video"
        )
        search_response = search_request.execute()

        conn = get_db()
        cursor = conn.cursor()
        inserted = 0

        for item in search_response.get('items', []):
            try:
                video_id = item['id']['videoId']

                video_request = youtube.videos().list(
                    part="statistics,snippet",
                    id=video_id
                )
                video_response = video_request.execute()

                if not video_response.get('items'):
                    continue

                video_data = video_response['items'][0]
                title = video_data['snippet']['title']
                published_at = video_data['snippet']['publishedAt']
                publish_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                stats = video_data.get('statistics', {})
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                comments = int(stats.get('commentCount', 0))

                cursor.execute("""
                    INSERT INTO youtube_videos (video_id, video_title, views, likes, comments, publish_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        video_title = VALUES(video_title),
                        views = VALUES(views),
                        likes = VALUES(likes),
                        comments = VALUES(comments),
                        publish_date = VALUES(publish_date)
                """, (video_id, title, views, likes, comments, publish_date))
                inserted += 1

            except Exception as e:
                print(f"Error processing video: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": f"Fetched and saved {inserted} videos."})

    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower():
            error_msg = "API quota exceeded. Try again later."
        elif "key" in error_msg.lower():
            error_msg = "Invalid API Key."
        elif "channel" in error_msg.lower():
            error_msg = "Channel not found or invalid Channel ID."
        return jsonify({"success": False, "error": error_msg})


# SHARE INFO

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


@app.route('/api/share-info')

@login_required

def share_info():
    ip = get_local_ip()
    port = 5000
    return jsonify({
        "url": f"http://{ip}:{port}",
        "ip": ip,
        "port": port
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)