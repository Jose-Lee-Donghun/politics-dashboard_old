import streamlit as st
import os
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
from datetime import datetime, timezone, timedelta
from fetcher import fetch_all, fetch_comments, suggest_titles
from channels import CHANNELS

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="한국 정치 유튜브", page_icon="📺", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #000; color: #e0e0e0; }
.stApp { background-color: #000000; }
.block-container { padding: 1rem 1.5rem; }
h1, h2, h3 { color: #ffffff; }
.video-card {
    background: #0a0a0a;
    border: 1px solid #1a1a2e;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 10px;
}
.video-title { font-size: 0.78rem; font-weight: 600; color: #e0e0e0; line-height: 1.3; }
.video-meta { font-size: 0.68rem; color: #888; margin-top: 3px; }
.channel-header {
    background: linear-gradient(90deg, #0d1b2a 0%, #000 100%);
    border-left: 3px solid #1565c0;
    padding: 6px 12px;
    margin: 16px 0 8px 0;
    border-radius: 0 4px 4px 0;
    font-size: 0.9rem;
    font-weight: 700;
    color: #90caf9;
}
.stButton button {
    background: #1565c0;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.75rem;
    padding: 4px 10px;
}
.stButton button:hover { background: #1976d2; }
.comment-box {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 8px 10px;
    margin: 4px 0;
    font-size: 0.75rem;
    color: #ccc;
}
.title-suggest {
    background: linear-gradient(135deg, #0d1b2a, #0a1628);
    border: 1px solid #1565c0;
    border-radius: 6px;
    padding: 10px 12px;
    margin: 6px 0;
    font-size: 0.8rem;
    font-weight: 600;
    color: #90caf9;
}
div[data-testid="stSidebar"] { background: #050505; border-right: 1px solid #111; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='margin-bottom:4px'>📺 한국 정치 유튜브 대시보드</h2>", unsafe_allow_html=True)
st.caption(f"실시간 조회수 · {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST")

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    hours = st.selectbox("기간", [24, 48, 72], format_func=lambda x: f"최근 {x}시간", label_visibility="collapsed")
with c2:
    min_views = st.number_input("최소 조회수", min_value=0, value=0, step=1000, label_visibility="collapsed")
with c3:
    refresh = st.button("🔄 새로고침", type="primary")

if refresh or "videos" not in st.session_state:
    with st.spinner("채널 스캔 중..."):
        st.session_state.videos = fetch_all(CHANNELS, hours=hours)
    st.session_state.fetched_at = datetime.now(KST).strftime("%H:%M:%S")

videos = st.session_state.get("videos", [])
filtered = [v for v in videos if (v["views"] or 0) >= min_views]

# Sidebar: selected video comments + title suggestions
with st.sidebar:
    st.markdown("### 💬 댓글 & AI 제목 추천")
    sel = st.session_state.get("selected_video")
    if sel:
        st.markdown(f"**{sel['title'][:50]}...**" if len(sel['title']) > 50 else f"**{sel['title']}**")
        st.markdown("---")

        if st.button("댓글 불러오기 & 제목 추천"):
            with st.spinner("댓글 로딩 중..."):
                result = fetch_comments(sel["video_id"])
                st.session_state.comments_result = result
            if result.get("popular") or result.get("recent"):
                all_comments = result.get("popular", []) + result.get("recent", [])
                with st.spinner("🤖 Claude가 제목 생성 중..."):
                    titles = suggest_titles(sel["title"], all_comments)
                st.session_state.suggested_titles = titles
            else:
                st.session_state.suggested_titles = []

        result = st.session_state.get("comments_result", {})
        titles = st.session_state.get("suggested_titles", [])

        if result.get("error"):
            st.error(result["error"][:300])

        if titles:
            st.markdown("#### 🎯 AI 추천 제목")
            for t in titles:
                st.markdown(f'<div class="title-suggest">✨ {t}</div>', unsafe_allow_html=True)

        popular = result.get("popular", [])
        recent = result.get("recent", [])

        if popular:
            st.markdown("#### 👍 인기 댓글 TOP 5")
            for c in popular:
                likes = c.get("votes", "")
                likes_str = f" · 👍{likes}" if likes else ""
                st.markdown(f'<div class="comment-box">{c.get("text","")[:100]}<br><small style="color:#555">{likes_str}</small></div>', unsafe_allow_html=True)

        if recent:
            st.markdown("#### 🕐 최신 댓글 5개")
            for c in recent:
                st.markdown(f'<div class="comment-box">{c.get("text","")[:100]}</div>', unsafe_allow_html=True)

        if not popular and not recent and not result.get("error") and result:
            st.info("댓글을 불러올 수 없습니다.")
    else:
        st.info("영상의 💬 버튼을 눌러 댓글과 AI 제목 추천을 확인하세요.")

# Main: channel-grouped grid
if not filtered:
    st.info("해당 조건에 맞는 영상이 없습니다.")
else:
    st.markdown(f"<small>총 **{len(filtered)}개** 영상</small>", unsafe_allow_html=True)

    from collections import defaultdict
    by_channel = defaultdict(list)
    for v in filtered:
        by_channel[v["channel"]].append(v)

    COLS = 5
    for channel_name, vids in by_channel.items():
        st.markdown(f'<div class="channel-header">📡 {channel_name} ({len(vids)}개)</div>', unsafe_allow_html=True)
        for i in range(0, len(vids), COLS):
            cols = st.columns(COLS)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(vids):
                    break
                v = vids[idx]
                with col:
                    st.image(v["thumbnail"], use_container_width=True)
                    views_str = f"{v['views']:,}" if v["views"] is not None else "-"
                    pub_str = v["published"].strftime("%m/%d %H:%M") if v["published"] else ""
                    st.markdown(
                        f'<div class="video-card">'
                        f'<div class="video-title"><a href="{v["link"]}" target="_blank" style="color:#90caf9;text-decoration:none">{v["title"]}</a></div>'
                        f'<div class="video-meta">👁 {views_str} · 🕐 {pub_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    if st.button("💬", key=f"cmtbtn_{v['video_id']}"):
                        st.session_state.selected_video = v
                        st.session_state.comments_result = {}
                        st.session_state.suggested_titles = []
                        st.rerun()
