import streamlit as st
import os
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
from datetime import datetime, timezone, timedelta
from fetcher import fetch_all
from channels import CHANNELS

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="한국 정치 유튜브 대시보드", page_icon="📺", layout="wide")

st.title("📺 한국 정치 유튜브 대시보드")
st.caption(f"최근 업로드 영상 조회수 순위 · 기준시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST")

col1, col2 = st.columns([1, 3])
with col1:
    hours = st.selectbox("기간", [24, 48, 72], format_func=lambda x: f"최근 {x}시간")
with col2:
    min_views = st.number_input("최소 조회수", min_value=0, value=1000, step=500)

if st.button("🔄 새로고침", type="primary") or "videos" not in st.session_state:
    with st.spinner("채널 스캔 중..."):
        st.session_state.videos = fetch_all(CHANNELS, hours=hours)
    st.session_state.fetched_at = datetime.now(KST).strftime("%H:%M:%S")

videos = st.session_state.get("videos", [])
fetched_at = st.session_state.get("fetched_at", "")

if fetched_at:
    st.caption(f"마지막 갱신: {fetched_at}")

filtered = [v for v in videos if (v["views"] or 0) >= min_views]

if not filtered:
    st.info("해당 조건에 맞는 영상이 없습니다.")
else:
    # 보기 모드 선택
    view_mode = st.radio("보기 모드", ["전체 순위", "채널별 보기"], horizontal=True)
    st.markdown(f"**총 {len(filtered)}개** 영상")
    st.divider()

    cols_per_row = 3

    if view_mode == "전체 순위":
        for i in range(0, len(filtered), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(filtered):
                    break
                v = filtered[idx]
                with col:
                    st.image(v["thumbnail"], use_container_width=True)
                    views_str = f"{v['views']:,}" if v["views"] is not None else "조회수 없음"
                    pub_str = v["published"].strftime("%m/%d %H:%M") if v["published"] else ""
                    st.markdown(f"**[{v['title']}]({v['link']})**")
                    st.markdown(f"📺 {v['channel']}　👁 {views_str}　🕐 {pub_str}")
                    st.divider()

    else:  # 채널별 보기
        # 채널 목록 (등장한 채널만)
        channels_in_data = sorted(set(v["channel"] for v in filtered))
        selected = st.selectbox("채널 선택", ["전체"] + channels_in_data)

        channel_filtered = filtered if selected == "전체" else [v for v in filtered if v["channel"] == selected]

        # 채널별로 그룹화
        from collections import defaultdict
        grouped = defaultdict(list)
        for v in channel_filtered:
            grouped[v["channel"]].append(v)

        for ch_name, ch_videos in sorted(grouped.items(), key=lambda x: -sum(v["views"] or 0 for v in x[1])):
            with st.expander(f"📺 {ch_name}  ({len(ch_videos)}개)", expanded=(selected != "전체")):
                for i in range(0, len(ch_videos), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx >= len(ch_videos):
                            break
                        v = ch_videos[idx]
                        with col:
                            st.image(v["thumbnail"], use_container_width=True)
                            views_str = f"{v['views']:,}" if v["views"] is not None else "조회수 없음"
                            pub_str = v["published"].strftime("%m/%d %H:%M") if v["published"] else ""
                            st.markdown(f"**[{v['title']}]({v['link']})**")
                            st.markdown(f"👁 {views_str}　🕐 {pub_str}")
                            st.divider()
