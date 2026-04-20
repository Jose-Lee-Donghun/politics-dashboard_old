import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

KST = timezone(timedelta(hours=9))
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def get_channel_id(handle: str) -> str | None:
    handle = handle.lstrip("@")
    url = f"https://www.youtube.com/@{handle}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        m = re.search(r'"channelId":"(UC[\w-]+)"', r.text)
        if m:
            return m.group(1)
        m = re.search(r'"externalId":"(UC[\w-]+)"', r.text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)
        channel_name = root.findtext("atom:title", namespaces=NS) or ""
        videos = []
        for entry in root.findall("atom:entry", NS):
            video_id = entry.findtext("yt:videoId", namespaces=NS)
            title = entry.findtext("atom:title", namespaces=NS)
            published = entry.findtext("atom:published", namespaces=NS)
            link_el = entry.find("atom:link", NS)
            link = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

            pub_dt = None
            if published:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(KST)

            views = None
            media_group = entry.find("media:group", NS)
            if media_group is not None:
                stats = media_group.find("media:statistics", NS)
                if stats is not None:
                    v = stats.get("views")
                    if v:
                        views = int(v)

            videos.append({
                "video_id": video_id,
                "title": title,
                "published": pub_dt,
                "link": link,
                "channel": channel_name,
                "views": views,
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
            })
        return videos
    except Exception:
        return []


def fetch_channel_videos(handle: str, hours: int = 48) -> list[dict]:
    channel_id = get_channel_id(handle)
    if not channel_id:
        return []
    videos = fetch_rss(channel_id)
    cutoff = datetime.now(KST) - timedelta(hours=hours)
    return [v for v in videos if v["published"] and v["published"] >= cutoff]


def fetch_all(handles: list[str], hours: int = 48) -> list[dict]:
    all_videos = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_channel_videos, h, hours): h for h in handles}
        for f in as_completed(futures):
            all_videos.extend(f.result())

    all_videos.sort(key=lambda x: x["views"] or 0, reverse=True)
    return all_videos
