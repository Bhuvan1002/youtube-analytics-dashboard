from flask import Flask, render_template
import mysql.connector

app = Flask(__name__)

# DATABASE CONNECTION

def get_videos():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="merajaan102@",
        database="youtube_analytics"
    )

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM youtube_videos")

    videos = cursor.fetchall()

    cursor.close()
    conn.close()

    return videos


# DASHBOARD PAGE

@app.route('/')

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

def videos_page():

    videos = get_videos()

    return render_template(
        'videos.html',
        videos=videos
    )


# REPORTS PAGE

@app.route('/reports')

def reports():

    videos = get_videos()

    # TOTALS

    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)

    # TOP VIDEOS

    top_video = max(
        videos,
        key=lambda x: x['views']
    )

    most_liked = max(
        videos,
        key=lambda x: x['likes']
    )

    lowest_video = min(
        videos,
        key=lambda x: x['views']
    )

    engagement_rate = round(
        (
            (total_likes + total_comments)
            / total_views
        ) * 100,
        2
    )

    return render_template(

        'reports.html',

        videos=videos,

        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,

        top_video=top_video,
        most_liked=most_liked,
        lowest_video=lowest_video,

        engagement_rate=engagement_rate
    )

# SETTINGS PAGE

@app.route('/settings')

def settings():

    return render_template('settings.html')





if __name__ == '__main__':
    app.run(debug=True)