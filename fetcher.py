import requests
import xml.etree.ElementTree as ET
import re
import json
import subprocess
import sys
import os

YTDLP = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

KST = timezone(timedelta(hours=9))
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


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

            videos.append({
                "video_id": video_id,
                "title": title,
                "published": pub_dt,
                "link": link,
                "channel": channel_name,
                "views": None,
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
            })
        return videos
    except Exception:
        return []


def fetch_views_ytdlp(video_ids: list[str]) -> dict[str, int]:
    if not video_ids:
        return {}
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    try:
        result = subprocess.run(
            [YTDLP, "--dump-json", "--no-playlist", "--no-warnings"] + urls,
            capture_output=True, text=True, timeout=120
        )
        views = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                views[data["id"]] = data.get("view_count", 0)
            except Exception:
                pass
        return views
    except Exception:
        return {}


def fetch_channel_videos(handle: str, hours: int = 48) -> list[dict]:
    channel_id = get_channel_id(handle)
    if not channel_id:
        return []
    videos = fetch_rss(channel_id)
    cutoff = datetime.now(KST) - timedelta(hours=hours)
    recent = [v for v in videos if v["published"] and v["published"] >= cutoff]
    return recent


def fetch_all(handles: list[str], hours: int = 48) -> list[dict]:
    all_videos = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_channel_videos, h, hours): h for h in handles}
        for f in as_completed(futures):
            all_videos.extend(f.result())

    # fetch view counts
    video_ids = [v["video_id"] for v in all_videos if v["video_id"]]
    views_map = fetch_views_ytdlp(video_ids)
    for v in all_videos:
        v["views"] = views_map.get(v["video_id"])

    all_videos.sort(key=lambda x: x["views"] or 0, reverse=True)
    return all_videos
