from googleapiclient.discovery import build
import mysql.connector
from datetime import datetime   

# -------------------------
# API KEY
# -------------------------

API_KEY = "AIzaSyD7ebL023x73FynVFqrDFKRNspKvAuOFwM"

youtube = build('youtube', 'v3', developerKey=API_KEY)

# -------------------------
# YouTube Channel Search
# -------------------------

request = youtube.search().list(
    part="snippet",
    channelId="UC2pIWZxKrWhNNzbxEjBnP7w",
    maxResults=10,
    order="date",
    type="video"
)

response = request.execute()

# -------------------------
# MySQL Connection
# -------------------------

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="merajaan102@",
    database="youtube_analytics"
)

cursor = conn.cursor()

# -------------------------
# Insert Data into SQL
# -------------------------

for item in response['items']:

    try:

        video_id = item['id']['videoId']

        # FETCH VIDEO DETAILS

        video_request = youtube.videos().list(
            part="statistics,snippet",
            id=video_id
        )

        video_response = video_request.execute()

        if len(video_response['items']) == 0:
            continue

        video_data = video_response['items'][0]

        title = video_data['snippet']['title']

        publish_date = datetime.strptime(
            video_data['snippet']['publishedAt'],
            "%Y-%m-%dT%H:%M:%SZ"
        )

        stats = video_data['statistics']

        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))

        query = """
        INSERT INTO youtube_videos
        (video_id, video_title, views, likes, comments, publish_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            video_id,
            title,
            views,
            likes,
            comments,
            publish_date
        )

        cursor.execute(query, values)

        print(f"Inserted: {title}")

    except Exception as e:

        print("Error:", e)


conn.commit()

print("YouTube data inserted successfully!")

cursor.close()
conn.close()