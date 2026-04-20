import requests
import xml.etree.ElementTree as ET
import re
import os
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

            # media:group > media:community > media:statistics[@views]
            views = None
            media_group = entry.find("media:group", NS)
            if media_group is not None:
                community = media_group.find("media:community", NS)
                if community is not None:
                    stats = community.find("media:statistics", NS)
                    if stats is not None:
                        try:
                            views = int(stats.get("views", 0))
                        except (ValueError, TypeError):
                            pass

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
    recent = [v for v in videos if v["published"] and v["published"] >= cutoff]
    return recent


def fetch_all(handles: list[str], hours: int = 48) -> list[dict]:
    all_videos = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_channel_videos, h, hours): h for h in handles}
        for f in as_completed(futures):
            all_videos.extend(f.result())

    all_videos.sort(key=lambda x: x["views"] or 0, reverse=True)
    return all_videos


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
    except Exception:
        import traceback
        return {"popular": [], "recent": [], "error": traceback.format_exc()}


def suggest_titles(video_title: str, comments: list[dict]) -> list[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ["ANTHROPIC_API_KEY 환경변수를 설정해 주세요."]

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        comment_texts = "\n".join(
            f"- {c.get('text', '')}" for c in comments[:10] if c.get("text")
        )

        prompt = f"""너는 2억 팔로워를 가진 초대형 인기 유튜버야.
시청자들의 클릭을 유도하는 강렬하고 자극적인 제목을 만드는 전문가야.

다음 영상 제목과 시청자 댓글을 보고, 더 많은 클릭을 유도할 수 있는 유튜브 제목 3개를 제안해줘.

원본 제목: {video_title}

시청자 댓글:
{comment_texts}

조건:
- 한국어로 작성
- 호기심과 긴장감을 극대화
- 숫자, 감탄사, 강조어 적극 활용
- 각 제목은 한 줄로 작성
- 번호 없이 제목만 출력 (1. 2. 3. 없이)
- 줄바꿈으로 구분해서 딱 3개만"""

        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=500,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )

        text = ""
        for block in message.content:
            if block.type == "text":
                text = block.text
                break

        titles = [t.strip() for t in text.strip().split("\n") if t.strip()]
        return titles[:3] if titles else ["제목 생성 실패"]
    except Exception:
        import traceback
        return [f"오류: {traceback.format_exc()[:200]}"]
