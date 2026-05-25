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


# DOWNLOAD PDF REPORT

@app.route('/download-report')

@login_required

def download_report():
    from fpdf import FPDF
    from datetime import datetime
    from io import BytesIO
    from flask import send_file

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np

    videos = get_videos()
    n = len(videos)
    if n == 0:
        return jsonify({"success": False, "error": "No videos in database."})

    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)
    avg_views = round(total_views / n)
    avg_likes = round(total_likes / n)
    avg_comments = round(total_comments / n)
    engagement_rate = round(((total_likes + total_comments) / total_views) * 100, 2)
    top_video = max(videos, key=lambda x: x['views'])
    lowest_video = min(videos, key=lambda x: x['views'])
    most_liked = max(videos, key=lambda x: x['likes'])

    for v in videos:
        v['engagement_rate'] = round(((v['likes'] + v['comments']) / v['views']) * 100, 2)
    videos_by_engagement = sorted(videos, key=lambda x: x['engagement_rate'], reverse=True)
    likes_per_view = round(total_likes / total_views, 4)
    comments_per_view = round(total_comments / total_views, 4)
    avg_eng = round(sum(v['engagement_rate'] for v in videos) / n, 2)

    video_titles = [v['video_title'] for v in videos]
    video_views = [v['views'] for v in videos]
    video_likes = [v['likes'] for v in videos]
    video_comments = [v['comments'] for v in videos]
    video_engagement = [v['engagement_rate'] for v in videos]

    def make_chart(fig, dpi=120):
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='#060913', edgecolor='none')
        buf.seek(0)
        plt.close(fig)
        return buf

    def style_ax(ax):
        ax.set_facecolor('#060913')
        ax.tick_params(colors='#94a3b8', labelsize=8)
        ax.spines['bottom'].set_color((1, 1, 1, 0.08))
        ax.spines['top'].set_color('none')
        ax.spines['left'].set_color((1, 1, 1, 0.08))
        ax.spines['right'].set_color('none')
        ax.xaxis.label.set_color('#94a3b8')
        ax.yaxis.label.set_color('#94a3b8')
        ax.title.set_color('#f8fafc')
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontsize(8)

    colors = ['#ff003c','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ec4899','#3b82f6','#14b8a6','#84cc16','#a855f7']
    CHART_W = 4.0
    CHART_H = 2.8

    def new_chart():
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
        fig.patch.set_facecolor('#060913')
        style_ax(ax)
        return fig, ax

    chart_images = []

    if n > 0:
        # --- CHART 1: Views & Engagement Trend ---
        fig, ax = new_chart()
        short_titles = [t[:16] + '...' if len(t) > 16 else t for t in video_titles]
        xs = list(range(len(video_views)))
        ax.plot(xs, video_views, color='#ff003c', linewidth=1.5, marker='o', markersize=2.5, label='Views')
        ax.plot(xs, video_likes, color='#06b6d4', linewidth=1.5, marker='s', markersize=2, label='Likes')
        ax.fill_between(xs, video_views, alpha=0.07, color='#ff003c')
        ax.set_xticks(xs)
        ax.set_xticklabels(short_titles, rotation=15, ha='right', fontsize=5.5)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        ax.legend(facecolor='#0d1426', labelcolor='#94a3b8', fontsize=6, framealpha=0.8, loc='upper left')
        ax.set_title('Views & Engagement Trend', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 2: Likes Distribution (Pie) ---
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
        fig.patch.set_facecolor('#060913')
        wedges, texts, autotexts = ax.pie(
            video_likes, labels=None, autopct='%1.1f%%',
            colors=colors[:n], startangle=90, pctdistance=0.7,
            wedgeprops={'linewidth': 1.5, 'edgecolor': '#060913'}
        )
        for t in autotexts:
            t.set_color('#f8fafc')
            t.set_fontsize(5.5)
        ax.set_title('Likes Distribution', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        centre_circle = plt.Circle((0, 0), 0.4, fc='#060913')
        ax.add_artist(centre_circle)
        ax.text(0, -0.12, f'{total_likes:,}', ha='center', va='center', fontsize=12, fontweight='bold', color='#f8fafc')
        ax.text(0, -0.25, 'Total Likes', ha='center', va='center', fontsize=5.5, color='#94a3b8')
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 3: Comments Volume (Horizontal Bar) ---
        fig, ax = new_chart()
        short_titles_h = [t[:14] + '...' if len(t) > 14 else t for t in video_titles]
        ax.barh(short_titles_h[::-1], video_comments[::-1], height=0.5, color=colors[:n])
        ax.set_title('Comments Volume', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 4: Views Timeline ---
        fig, ax = new_chart()
        zipped = sorted(zip(video_titles, video_views, [v['publish_date'] for v in videos]), key=lambda x: x[2])
        tl_views = [v for _, v, _ in zipped]
        tl_labels = [d.strftime('%b %Y') if hasattr(d, 'strftime') else str(d)[:7] for _, _, d in zipped]
        xs = list(range(len(tl_views)))
        ax.plot(xs, tl_views, color='#10b981', linewidth=1.5, marker='o', markersize=3)
        ax.fill_between(xs, tl_views, alpha=0.08, color='#10b981')
        ax.set_xticks(xs)
        ax.set_xticklabels(tl_labels, fontsize=6)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        ax.set_title('Views Timeline', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 5: Engagement Rate per Video ---
        fig, ax = new_chart()
        er_sorted = sorted(zip(video_titles, video_engagement), key=lambda x: x[1], reverse=True)
        er_titles, er_vals = zip(*er_sorted)
        er_labels = [t[:14] + '...' if len(t) > 14 else t for t in er_titles[:7]]
        er_vals = list(er_vals[:7])
        colors_er = ['#10b981' if v >= 5 else '#06b6d4' if v >= 2 else '#64748b' for v in er_vals]
        ax.barh(er_labels[::-1], er_vals[::-1], height=0.5, color=colors_er[::-1])
        ax.set_title('Engagement Rate per Video (Top 7)', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 6: Views vs Likes ---
        fig, ax = new_chart()
        sizes = [max(15, min(120, c/4)) for c in video_comments]
        ax.scatter(video_views, video_likes, s=sizes, c='#8b5cf6', alpha=0.55, edgecolors='#8b5cf6', linewidth=0.5)
        ax.set_xlabel('Views')
        ax.set_ylabel('Likes')
        ax.set_title('Views vs Likes (size = Comments)', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        fig.tight_layout()
        chart_images.append(make_chart(fig))

        # --- CHART 7: Engagement Density ---
        fig, ax = new_chart()
        density = [round((l + c) / max(v, 1) * 100, 2) for l, c, v in zip(video_likes, video_comments, video_views)]
        short_d = [t[:12] + '...' if len(t) > 12 else t for t in video_titles]
        ax.bar(short_d, density, color=colors[:n], width=0.5)
        ax.set_title('Engagement Density', fontsize=9, fontweight='bold', color='#f8fafc', pad=6)
        ax.set_xticklabels(short_d, rotation=15, ha='right', fontsize=5.5)
        fig.tight_layout()
        chart_images.append(make_chart(fig))

    # --- BUILD PDF (2 pages: text + all charts in rows of 2) ---
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margin(15)
    pdf.add_page()

    red = (255, 0, 60)
    dark = (15, 23, 42)
    gray = (100, 116, 139)

    chart_labels = [
        ('Views & Engagement Trend', 'Views and likes tracked across all analyzed videos showing performance patterns'),
        ('Likes Distribution', 'Proportional breakdown of total likes each video has received'),
        ('Comments Volume', 'Total number of comments generated per video in the channel'),
        ('Views Timeline', 'Channel viewership trend plotted chronologically by publish date'),
        ('Engagement Rate per Video', 'Top 7 videos ranked by engagement rate (likes + comments / views)'),
        ('Views vs Likes Correlation', 'Bubble chart showing relationship between views, likes, and comments'),
        ('Engagement Density', 'Engagement rate distribution across each video in the channel'),
    ]

    # ============ PAGE 1: Title + Summary + Charts 1-2 ============
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(248, 250, 252)
    pdf.set_y(8)
    pdf.cell(0, 10, 'YouTube Analytics Report', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(148, 163, 184)
    dt = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pdf.cell(0, 5, f'Generated: {dt}  |  {n} videos analyzed', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_y(34)

    pdf.set_draw_color(*red)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    # --- Summary Table ---
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*dark)
    pdf.cell(0, 7, 'Channel Summary', new_x="LMARGIN", new_y="NEXT")
    cw = [30, 22, 30, 22, 30, 22]
    pdf.set_font('Helvetica', 'B', 6)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(*dark)
    for i, h in enumerate(['Metric','Value','Metric','Value','Metric','Value']):
        pdf.cell(cw[i], 5, h, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font('Helvetica', '', 6)
    rows = [
        ['Total Views', f'{total_views:,}', 'Total Likes', f'{total_likes:,}', 'Total Comments', f'{total_comments:,}'],
        ['Avg Views', f'{avg_views:,}', 'Avg Likes', f'{avg_likes:,}', 'Avg Comments', f'{avg_comments:,}'],
        ['Engagement Rate', f'{engagement_rate}%', 'Likes/View', f'{likes_per_view}', 'Comments/View', f'{comments_per_view}'],
    ]
    for row in rows:
        for i, v in enumerate(row):
            pdf.cell(cw[i], 5, v, border=1, align='C')
        pdf.ln()
    pdf.ln(5)

    # --- Performance Leaders ---
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*dark)
    pdf.cell(0, 6, 'Performance Leaders', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 6.5)
    for label, clr, v in [('Top', red, top_video), ('Lowest', gray, lowest_video)]:
        pdf.set_text_color(*clr)
        pdf.cell(7, 4, f'[{label}]')
        pdf.set_text_color(*dark)
        t = v['video_title'][:55] + '...' if len(v['video_title']) > 55 else v['video_title']
        pdf.cell(80, 4, t)
        pdf.set_text_color(*gray)
        pdf.cell(0, 4, f"Views: {v['views']:,}  Likes: {v['likes']:,}  Comments: {v['comments']:,}  ER: {v['engagement_rate']}%", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(236, 72, 153)
    pdf.cell(7, 4, '[Liked]')
    pdf.set_text_color(*dark)
    t = most_liked['video_title'][:55] + '...' if len(most_liked['video_title']) > 55 else most_liked['video_title']
    pdf.cell(80, 4, t)
    pdf.set_text_color(*gray)
    pdf.cell(0, 4, f"Likes: {most_liked['likes']:,}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Diagnostics ---
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*dark)
    pdf.cell(0, 6, 'Channel Diagnostics', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 6.5)
    pdf.set_text_color(71, 85, 105)
    summary = (
        f"{total_views:,} total views, {total_likes:,} likes, {total_comments:,} comments across {n} videos. "
        f"Overall engagement: {engagement_rate}%. "
        f"Top: \"{top_video['video_title'][:45]}\" at {top_video['views']:,} views ({top_video['engagement_rate']}% ER)."
    )
    pdf.multi_cell(0, 3.5, summary)
    pdf.ln(3)

    def place_chart_pair(idx1, idx2, y_start):
        pdf.set_y(y_start)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*dark)
        pdf.set_xy(15, y_start)
        pdf.cell(82, 4, chart_labels[idx1][0], align='C')
        pdf.set_xy(105, y_start)
        pdf.cell(82, 4, chart_labels[idx2][0], align='C')
        pdf.set_font('Helvetica', '', 5.5)
        pdf.set_text_color(*gray)
        pdf.set_xy(15, y_start + 4)
        pdf.cell(82, 3, chart_labels[idx1][1], align='C')
        pdf.set_xy(105, y_start + 4)
        pdf.cell(82, 3, chart_labels[idx2][1], align='C')
        img_y = y_start + 8
        buf1 = chart_images[idx1]
        buf1.seek(0)
        pdf.image(buf1, x=15, y=img_y, w=82)
        buf1.close()
        buf2 = chart_images[idx2]
        buf2.seek(0)
        pdf.image(buf2, x=105, y=img_y, w=82)
        buf2.close()

    ch_h = 82 * CHART_H / CHART_W

    # --- Charts 1 & 2 side by side ---
    place_chart_pair(0, 1, pdf.get_y())

    # ============ PAGE 2: Charts 3-7 ============
    pdf.add_page()
    place_chart_pair(2, 3, 15)
    place_chart_pair(4, 5, 15 + ch_h + 14)
    # Chart 7 centered at bottom
    y7 = 15 + 2 * (ch_h + 14)
    pdf.set_y(y7)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*dark)
    pdf.cell(0, 4, chart_labels[6][0], new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 5.5)
    pdf.set_text_color(*gray)
    pdf.cell(0, 3, chart_labels[6][1], new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(2)
    buf7 = chart_images[6]
    buf7.seek(0)
    pdf.image(buf7, x=38, w=135)
    buf7.close()

    pdf_buf = BytesIO(bytes(pdf.output()))
    pdf_buf.seek(0)
    return send_file(
        pdf_buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'youtube_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)