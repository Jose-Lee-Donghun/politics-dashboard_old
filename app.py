import streamlit as st
import os
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fetcher import fetch_all, fetch_comments
from channels import CHANNELS

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="한국 정치 유튜브 대시보드", page_icon="📺", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .stApp { background: #000000; }

  /* 채널 헤더 */
  .ch-header {
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7eb3ff;
    border-bottom: 1px solid #1a1a2e;
    padding-bottom: 6px;
    margin: 18px 0 10px;
  }

  /* 영상 카드 */
  .vid-card {
    background: #0d0d14;
    border: 1px solid #1a1a2e;
    border-radius: 6px;
    padding: 8px;
    margin-bottom: 8px;
  }
  .vid-title {
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.4;
    color: #e8e8f0;
    margin: 6px 0 4px;
  }
  .vid-meta {
    font-size: 0.68rem;
    color: #5a5a7a;
    margin-bottom: 4px;
  }

  /* 댓글 */
  .comment-box {
    background: #080810;
    border-left: 2px solid #1565c0;
    border-radius: 0 4px 4px 0;
    padding: 6px 8px;
    margin: 4px 0;
  }
  .comment-section-title {
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #1565c0;
    margin: 8px 0 4px;
  }
  .comment-text {
    font-size: 0.7rem;
    color: #c0c0d0;
    line-height: 1.4;
  }
  .comment-likes {
    font-size: 0.62rem;
    color: #5a5a7a;
    margin-top: 2px;
  }

  /* 버튼 override */
  .stButton > button {
    background: transparent;
    border: 1px solid #1a1a2e;
    color: #5a7aaa;
    font-size: 0.68rem;
    padding: 2px 8px;
    border-radius: 4px;
  }
  .stButton > button:hover {
    border-color: #1565c0;
    color: #7eb3ff;
  }

  /* 구분선 */
  hr { border-color: #0d0d1a; }

  /* 필터 영역 */
  .filter-bar {
    background: #0d0d14;
    border: 1px solid #1a1a2e;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
  }
</style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size:1.3rem;font-weight:600;letter-spacing:0.05em;color:#fff;margin-bottom:2px">📺 한국 정치 유튜브 대시보드</p>', unsafe_allow_html=True)
st.markdown(f'<p style="font-size:0.72rem;color:#5a5a7a;margin-bottom:16px">기준시간: {datetime.now(KST).strftime("%Y-%m-%d %H:%M")} KST</p>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    hours = st.selectbox("기간", [24, 48, 72], format_func=lambda x: f"최근 {x}시간", label_visibility="collapsed")
with c2:
    min_views = st.number_input("최소 조회수", min_value=0, value=1000, step=500, label_visibility="collapsed")
with c3:
    refresh = st.button("⟳ 새로고침", type="primary")

if refresh or "videos" not in st.session_state:
    with st.spinner("채널 스캔 중..."):
        st.session_state.videos = fetch_all(CHANNELS, hours=hours)
    st.session_state.fetched_at = datetime.now(KST).strftime("%H:%M:%S")

videos = st.session_state.get("videos", [])
fetched_at = st.session_state.get("fetched_at", "")
if fetched_at:
    st.markdown(f'<span style="font-size:0.68rem;color:#3a3a5a">마지막 갱신: {fetched_at}</span>', unsafe_allow_html=True)

filtered = [v for v in videos if (v["views"] or 0) >= min_views]

if not filtered:
    st.info("해당 조건에 맞는 영상이 없습니다.")
else:
    st.markdown(f'<span style="font-size:0.72rem;color:#5a5a7a">{len(filtered)}개 영상</span>', unsafe_allow_html=True)

    grouped = defaultdict(list)
    for v in filtered:
        grouped[v["channel"]].append(v)

    COLS = 5

    for ch_name, ch_videos in sorted(grouped.items(), key=lambda x: -sum(v["views"] or 0 for v in x[1])):
        st.markdown(f'<div class="ch-header">📺 {ch_name} &nbsp;<span style="color:#3a3a5a;font-weight:400">({len(ch_videos)})</span></div>', unsafe_allow_html=True)

        for i in range(0, len(ch_videos), COLS):
            cols = st.columns(COLS)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(ch_videos):
                    break
                v = ch_videos[idx]
                vid = v["video_id"]
                with col:
                    st.image(v["thumbnail"], use_container_width=True)
                    views_str = f"{v['views']:,}" if v["views"] is not None else "-"
                    pub_str = v["published"].strftime("%m/%d %H:%M") if v["published"] else ""
                    st.markdown(
                        f'<div class="vid-title"><a href="{v["link"]}" target="_blank" style="color:#e8e8f0;text-decoration:none">{v["title"]}</a></div>'
                        f'<div class="vid-meta">👁 {views_str} &nbsp;·&nbsp; {pub_str}</div>',
                        unsafe_allow_html=True,
                    )

                    # 댓글 버튼
                    btn_key = f"show_{vid}"
                    if btn_key not in st.session_state:
                        st.session_state[btn_key] = False
                    if st.button("💬 댓글", key=f"btn_{vid}"):
                        st.session_state[btn_key] = not st.session_state[btn_key]

                    if st.session_state[btn_key]:
                        cache_key = f"cmts_{vid}"
                        if cache_key not in st.session_state:
                            with st.spinner(""):
                                st.session_state[cache_key] = fetch_comments(vid)
                        cmts = st.session_state[cache_key]

                        if cmts["top"]:
                            st.markdown('<div class="comment-section-title">인기 댓글</div>', unsafe_allow_html=True)
                            for c in cmts["top"]:
                                txt = (c.get("text") or "")[:120]
                                likes = c.get("like_count") or 0
                                st.markdown(
                                    f'<div class="comment-box"><div class="comment-text">{txt}</div>'
                                    f'<div class="comment-likes">👍 {likes:,}</div></div>',
                                    unsafe_allow_html=True,
                                )

                        if cmts["by_likes"]:
                            st.markdown('<div class="comment-section-title">좋아요 순</div>', unsafe_allow_html=True)
                            for c in cmts["by_likes"]:
                                txt = (c.get("text") or "")[:120]
                                likes = c.get("like_count") or 0
                                st.markdown(
                                    f'<div class="comment-box"><div class="comment-text">{txt}</div>'
                                    f'<div class="comment-likes">👍 {likes:,}</div></div>',
                                    unsafe_allow_html=True,
                                )
