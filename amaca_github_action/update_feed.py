import re
import sys
import hashlib
import html
from datetime import datetime, timezone
from pathlib import Path
from email.utils import format_datetime
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

PAGE_URL = "https://www.repubblica.it/rubriche/l-amaca/2024/05/16/rubrica/lamaca-422978093/"
FEED_PATH = Path("feed.xml")
SITE_FEED_URL = "https://scumaci74.github.io/amaca-feed/feed.xml"

CHANNEL_TITLE = "L'Amaca - Feed personale"
CHANNEL_LINK = "https://www.repubblica.it/rubriche/l-amaca/"
CHANNEL_DESCRIPTION = "Feed RSS personale per ascoltare L'Amaca su client podcast."
CHANNEL_AUTHOR = "Michele Serra"

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("content", CONTENT_NS)
ET.register_namespace("atom", ATOM_NS)

MP3_RE = re.compile(r'https?://[^"\'>\s]+?\.mp3(?:\?[^"\'>\s]*)?', re.I)

TITLE_PATTERNS = [
    re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S),
    re.compile(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', re.I | re.S),
]

def fetch_page() -> str:
    req = Request(
        PAGE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AmacaFeedBot/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")

def find_mp3s(page: str):
    urls = []
    for match in MP3_RE.findall(page):
        clean = html.unescape(match)
        if "amacaserra" in clean.lower() or "amaca" in clean.lower():
            if clean not in urls:
                urls.append(clean)
    return urls

def title_from_url(url: str) -> str:
    # Example: 1286166-mp3-audio-128-amacaserra_06_06_2026.mp3
    m = re.search(r'(\d{2})_(\d{2})_(\d{4})\.mp3', url)
    if m:
        dd, mm, yyyy = m.groups()
        return f"L'Amaca del {dd}/{mm}/{yyyy}"
    return "L'Amaca"

def pubdate_from_url(url: str) -> str:
    m = re.search(r'(\d{2})_(\d{2})_(\d{4})\.mp3', url)
    if m:
        dd, mm, yyyy = m.groups()
        dt = datetime(int(yyyy), int(mm), int(dd), 6, 0, 0, tzinfo=timezone.utc)
        return format_datetime(dt)
    return format_datetime(datetime.now(timezone.utc))

def ensure_feed():
    if FEED_PATH.exists():
        return ET.parse(FEED_PATH)

    rss = ET.Element("rss", {
        "version": "2.0",
        f"xmlns:itunes": ITUNES_NS,
        f"xmlns:content": CONTENT_NS,
        f"xmlns:atom": ATOM_NS,
    })
    ch = ET.SubElement(rss, "channel")
    ET.SubElement(ch, "title").text = CHANNEL_TITLE
    ET.SubElement(ch, "link").text = CHANNEL_LINK
    ET.SubElement(ch, f"{{{ATOM_NS}}}link", {
        "href": SITE_FEED_URL,
        "rel": "self",
        "type": "application/rss+xml",
    })
    ET.SubElement(ch, "description").text = CHANNEL_DESCRIPTION
    ET.SubElement(ch, "language").text = "it-IT"
    ET.SubElement(ch, "copyright").text = "Contenuti di GEDI Gruppo Editoriale. Feed personale non ufficiale."
    ET.SubElement(ch, f"{{{ITUNES_NS}}}author").text = CHANNEL_AUTHOR
    ET.SubElement(ch, f"{{{ITUNES_NS}}}summary").text = CHANNEL_DESCRIPTION
    ET.SubElement(ch, f"{{{ITUNES_NS}}}explicit").text = "false"
    ET.SubElement(ch, f"{{{ITUNES_NS}}}type").text = "episodic"
    ET.SubElement(ch, f"{{{ITUNES_NS}}}category", {"text": "News"})
    image = ET.SubElement(ch, "image")
    ET.SubElement(image, "url").text = "https://www.repubblica.it/favicon.ico"
    ET.SubElement(image, "title").text = CHANNEL_TITLE
    ET.SubElement(image, "link").text = CHANNEL_LINK
    owner = ET.SubElement(ch, f"{{{ITUNES_NS}}}owner")
    ET.SubElement(owner, f"{{{ITUNES_NS}}}name").text = "Feed personale"
    ET.SubElement(owner, f"{{{ITUNES_NS}}}email").text = "noreply@example.com"
    return ET.ElementTree(rss)

def existing_guids(channel):
    return {item.findtext("guid") for item in channel.findall("item") if item.findtext("guid")}

def add_item(channel, url):
    guid = "amaca-" + hashlib.sha1(url.encode("utf-8")).hexdigest()
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title_from_url(url)
    ET.SubElement(item, "description").text = "Episodio audio de L'Amaca individuato automaticamente."
    content = ET.SubElement(item, f"{{{CONTENT_NS}}}encoded")
    content.text = "Episodio audio de L'Amaca individuato automaticamente."
    ET.SubElement(item, "pubDate").text = pubdate_from_url(url)
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
    ET.SubElement(item, f"{{{ITUNES_NS}}}author").text = CHANNEL_AUTHOR
    ET.SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "false"
    ET.SubElement(item, "enclosure", {
        "url": url,
        "length": "2500000",
        "type": "audio/mpeg",
    })
    # Inserisce i nuovi episodi in alto.
    first_item = channel.find("item")
    if first_item is None:
        channel.append(item)
    else:
        idx = list(channel).index(first_item)
        channel.insert(idx, item)
    return guid

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def main():
    tree = ensure_feed()
    channel = tree.getroot().find("channel")
    if channel is None:
        raise RuntimeError("feed.xml non contiene channel")

    page = fetch_page()
    mp3s = find_mp3s(page)

    if not mp3s:
        print("Nessun MP3 trovato nella pagina. Il feed resta invariato.")
        return 0

    guids = existing_guids(channel)
    added = 0
    for url in mp3s[:10]:
        guid = "amaca-" + hashlib.sha1(url.encode("utf-8")).hexdigest()
        if guid not in guids:
            add_item(channel, url)
            added += 1

    # aggiorna lastBuildDate
    lbd = channel.find("lastBuildDate")
    if lbd is None:
        lbd = ET.SubElement(channel, "lastBuildDate")
    lbd.text = format_datetime(datetime.now(timezone.utc))

    if added:
        indent(tree.getroot())
        tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
        print(f"Aggiunti {added} nuovi episodi.")
    else:
        print("Nessun nuovo episodio da aggiungere.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
