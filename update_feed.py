import html
import requests
from datetime import datetime, timezone
from email.utils import format_datetime

JSON_URL = "https://www.repubblica.it/json/rubriche/l-amaca/2024/05/16/rubrica/lamaca-422978093/"
FEED_FILE = "feed.xml"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.repubblica.it/rubriche/l-amaca/2024/05/16/rubrica/lamaca-422978093/"
}

response = requests.get(JSON_URL, headers=headers, timeout=30)
print("Status code:", response.status_code)
print("Content-Type:", response.headers.get("content-type"))
print("Prime 300 lettere:", response.text[:300])

response.raise_for_status()
data = response.json()
episodes = data["data"][:50]

cover_image = "https://scumaci74.github.io/amaca-feed/l-amaca.jpg"

items = []

for ep in episodes:
    title = ep["title"]
    mp3 = ep["audio_url"]
    pub_date = ep["pub_date"]
    duration = ep.get("duration", "")
    guid = ep["original_id"]
    image = ep.get("image", cover_image)

    try:
        dt = datetime.strptime(pub_date, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        rss_date = format_datetime(dt)
    except Exception:
        rss_date = pub_date

    items.append(f"""
    <item>
      <title><![CDATA[{title}]]></title>
      <guid isPermaLink="false">{html.escape(guid)}</guid>
      <pubDate>{rss_date}</pubDate>
      <author>Michele Serra</author>
      <itunes:author>Michele Serra</itunes:author>
      <itunes:duration>{html.escape(duration)}</itunes:duration>
      <itunes:image href="{html.escape(image)}"/>
      <description><![CDATA[{duration}]]></description>
      <enclosure url="{html.escape(mp3)}" type="audio/mpeg"/>
    </item>
    """)

rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>L'Amaca - Michele Serra</title>
<link>https://www.repubblica.it/rubriche/l-amaca/</link>
<description>Feed RSS personale per ascoltare L'Amaca di Michele Serra su client podcast.</description>
<language>it-it</language>
<copyright>Contenuti GEDI Gruppo Editoriale. Feed personale non ufficiale.</copyright>
<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>

<itunes:author>Michele Serra</itunes:author>
<itunes:summary>L'Amaca di Michele Serra.</itunes:summary>
<itunes:explicit>false</itunes:explicit>
<itunes:type>episodic</itunes:type>
<itunes:category text="News"/>
<itunes:image href="{html.escape(cover_image)}"/>

<image>
  <url>{html.escape(cover_image)}</url>
  <title>L'Amaca - Michele Serra</title>
  <link>https://www.repubblica.it/rubriche/l-amaca/</link>
</image>

{''.join(items)}

</channel>
</rss>
"""

with open(FEED_FILE, "w", encoding="utf-8") as f:
    f.write(rss)

print(f"Feed aggiornato con {len(episodes)} episodi")
