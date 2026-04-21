import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

KST = timezone(timedelta(hours=9))
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


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
                community = media_group.find("media:community", NS)
                if community is not None:
                    stats = community.find("media:statistics", NS)
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


def fetch_channel_videos(handle: str, channel_id: str, hours: int = 48) -> list[dict]:
    videos = fetch_rss(channel_id)
    cutoff = datetime.now(KST) - timedelta(hours=hours)
    return [v for v in videos if v["published"] and v["published"] >= cutoff]


def fetch_all(channels: dict[str, str], hours: int = 48) -> list[dict]:
    all_videos = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_channel_videos, h, cid, hours): h for h, cid in channels.items()}
        for f in as_completed(futures):
            all_videos.extend(f.result())
    all_videos.sort(key=lambda x: x["views"] or 0, reverse=True)
    return all_videos


def _parse_votes(votes) -> int:
    if not votes:
        return 0
    s = str(votes).strip().replace(",", "")
    try:
        if s.endswith("K"):
            return int(float(s[:-1]) * 1000)
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except Exception:
        return 0


def fetch_comments(video_id: str) -> dict:
    try:
        from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR, SORT_BY_RECENT

        dl = YoutubeCommentDownloader()
        url = f"https://www.youtube.com/watch?v={video_id}"

        popular, recent = [], []
        for c in dl.get_comments_from_url(url, sort_by=SORT_BY_POPULAR):
            popular.append(c)
            if len(popular) >= 5:
                break

        for c in dl.get_comments_from_url(url, sort_by=SORT_BY_RECENT):
            recent.append(c)
            if len(recent) >= 5:
                break

        return {"popular": popular, "recent": recent}
    except Exception as e:
        import traceback
        return {"popular": [], "recent": [], "error": traceback.format_exc()}
