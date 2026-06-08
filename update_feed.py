import json
import requests
from datetime import datetime
from email.utils import format_datetime

JSON_URL = "https://www.repubblica.it/json/rubriche/l-amaca/2024/05/16/rubrica/lamaca-422978093/"
FEED_FILE = "feed.xml"

data = requests.get(JSON_URL, timeout=30).json()

episodes = data["data"][:50]

items = []

for ep in episodes:
    title = ep["title"]
    mp3 = ep["audio_url"]
    pub_date = ep["pub_date"]
    duration = ep.get("duration", "")
    guid = ep["original_id"]

    try:
        dt = datetime.strptime(pub_date, "%d/%m/%Y")
        rss_date = format_datetime(dt)
    except:
        rss_date = pub_date

    items.append(f"""
    <item>
      <title><![CDATA[{title}]]></title>
      <guid>{guid}</guid>
      <pubDate>{rss_date}</pubDate>
      <enclosure url="{mp3}" type="audio/mpeg"/>
      <description><![CDATA[{duration}]]></description>
    </item>
    """)

rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>L'Amaca - Michele Serra</title>
<link>https://www.repubblica.it/rubriche/l-amaca/</link>
<description>Feed RSS personale generato automaticamente</description>
<language>it-it</language>

{''.join(items)}

</channel>
</rss>
"""

with open(FEED_FILE, "w", encoding="utf-8") as f:
    f.write(rss)

print(f"Feed aggiornato con {len(episodes)} episodi")
