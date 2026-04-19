import sys
sys.path.insert(0, ".")
from fetcher import fetch_all
from channels import CHANNELS
from datetime import datetime, timezone, timedelta
import webbrowser, os, subprocess

KST = timezone(timedelta(hours=9))
HOURS = 48
MIN_VIEWS = 10000

print("채널 스캔 중... (1~2분 소요)")
videos = [v for v in fetch_all(CHANNELS, hours=HOURS) if (v["views"] or 0) >= MIN_VIEWS]
now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

# 채널별 그룹화 후 각 채널 내 조회수 내림차순 정렬
from collections import defaultdict
by_channel = defaultdict(list)
for v in videos:
    by_channel[v["channel"]].append(v)
for ch in by_channel:
    by_channel[ch].sort(key=lambda x: x["views"] or 0, reverse=True)
# 채널 순서: 채널 내 최고 조회수 기준 내림차순
sorted_channels = sorted(by_channel.items(), key=lambda x: max(v["views"] or 0 for v in x[1]), reverse=True)

sections = ""
for ch_name, ch_videos in sorted_channels:
    cards = ""
    for i, v in enumerate(ch_videos, 1):
        views = f"{v['views']:,}" if v["views"] is not None else "—"
        pub = v["published"].strftime("%m/%d %H:%M") if v["published"] else ""
        cards += f"""
        <div class="card">
          <a href="{v['link']}" target="_blank">
            <img src="{v['thumbnail']}" alt="">
            <div class="rank">#{i}</div>
          </a>
          <div class="info">
            <a href="{v['link']}" target="_blank" class="title">{v['title']}</a>
            <div class="meta">
              <span class="views">👁 {views}</span>
              <span class="date">🕐 {pub}</span>
            </div>
          </div>
        </div>"""
    sections += f"""
    <div class="channel-section">
      <h2 class="channel-title">📺 {ch_name} <span class="ch-count">{len(ch_videos)}개</span></h2>
      <div class="grid">{cards}</div>
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>한국 정치 유튜브 대시보드</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }}
  header {{ background: #1a1a2e; padding: 20px 30px; border-bottom: 2px solid #e50914; }}
  header h1 {{ font-size: 1.5rem; color: #fff; }}
  header p {{ color: #aaa; font-size: 0.85rem; margin-top: 4px; }}
  .channel-section {{ padding: 20px 30px 0; }}
  .channel-title {{ font-size: 1.1rem; color: #81c784; margin-bottom: 12px; border-left: 4px solid #e50914; padding-left: 10px; }}
  .ch-count {{ font-size: 0.8rem; color: #aaa; font-weight: normal; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 30px; }}
  .card {{ background: #1e1e1e; border-radius: 10px; overflow: hidden; transition: transform 0.2s; position: relative; }}
  .card:hover {{ transform: translateY(-3px); }}
  .card img {{ width: 100%; height: 160px; object-fit: cover; display: block; }}
  .rank {{ position: absolute; top: 8px; left: 8px; background: #e50914; color: #fff; font-weight: bold; font-size: 0.85rem; padding: 3px 8px; border-radius: 4px; }}
  .info {{ padding: 10px; }}
  .title {{ color: #fff; font-size: 0.88rem; font-weight: 600; line-height: 1.4; text-decoration: none; display: block; margin-bottom: 6px; }}
  .title:hover {{ color: #e50914; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 0.78rem; color: #aaa; }}
  .views {{ color: #4fc3f7; font-weight: bold; }}
</style>
</head>
<body>
<header>
  <h1>📺 한국 정치 유튜브 대시보드</h1>
  <p>최근 {HOURS}시간 영상 · 조회수 순 · 기준: {now} KST · 총 {len(videos)}개</p>
</header>
{sections}
</body>
</html>"""

base = os.path.dirname(os.path.abspath(__file__))

# GitHub Actions에서는 프로젝트 루트에만 저장
if os.environ.get("GITHUB_ACTIONS"):
    paths = [os.path.join(base, "index.html")]
else:
    paths = [
        os.path.join(base, "index.html"),
        "/mnt/c/Users/pokss/OneDrive/Desktop/정치유튜브대시보드.html",
    ]

for out in paths:
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

print(f"완료! {len(videos)}개 영상 수집")
print(f"저장 위치: {', '.join(paths)}")

# 로컬에서만 브라우저 열기
if not os.environ.get("GITHUB_ACTIONS"):
    win_path = "C:\\Users\\pokss\\OneDrive\\Desktop\\정치유튜브대시보드.html"
    subprocess.run(["cmd.exe", "/c", "start", win_path], check=False)
