import streamlit as st
from openai import OpenAI
import requests
from collections import Counter
from datetime import date
import re
import urllib.parse

# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("DJ 캐릭터와 함께, 취향을 학습하는 음악 추천 🎶")

# ==================================================
# DJ 캐릭터
# ==================================================
DJ_CHARACTERS = {
    "힙합 DJ": "당신은 힙합과 스트릿 감성에 강한 DJ입니다.",
    "감성 DJ": "당신은 새벽 감성과 감정선을 중시하는 DJ입니다.",
    "클럽 DJ": "당신은 클럽에서 분위기를 터뜨리는 DJ입니다.",
    "카페 DJ": "당신은 카페 플레이리스트 전문가 DJ입니다."
}

GENRES = ["KPOP", "POP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM", "무관"]

# ==================================================
# 사이드바
# ==================================================
with st.sidebar:
    dj = st.selectbox("🎧 DJ 캐릭터", list(DJ_CHARACTERS.keys()))
    genre = st.selectbox("🎵 장르", GENRES)
    song_count = st.slider("🎶 추천 곡 수", 3, 30, 10)
    city = st.text_input("🌦️ 도시", "Seoul")

    if st.button("🗑️ 전체 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

# ==================================================
# Secrets
# ==================================================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==================================================
# 날씨
# ==================================================
def get_weather(city):
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": st.secrets["OPENWEATHER_API_KEY"],
                "units": "metric",
                "lang": "kr"
            },
            timeout=5
        ).json()
        return res["weather"][0]["description"]
    except:
        return "알 수 없음"

weather = get_weather(city)

# ==================================================
# session_state 초기화
# ==================================================
for key, default in {
    "taste_good": [],
    "taste_bad": [],
    "daily_playlists": {},
    "song_ratings": {},
    "playlist_counter": 0
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================================================
# 취향 요약
# ==================================================
def summarize(lst):
    c = Counter(lst)
    return ", ".join([k for k, _ in c.most_common(5)]) or "없음"

# ==================================================
# 시스템 프롬프트
# ==================================================
def build_system_prompt():
    return (
        f"{DJ_CHARACTERS[dj]}\n\n"
        f"- 장르: {genre} (무관이면 자유)\n"
        f"- 날씨: {weather}\n"
        f"- 좋아요 취향: {summarize(st.session_state.taste_good)}\n"
        f"- 싫어요 취향: {summarize(st.session_state.taste_bad)}\n\n"
        f"❗ 반드시 정확히 {song_count}곡을 출력하세요.\n"
        f"❗ {song_count}곡이 아니면 잘못된 답변입니다.\n\n"
        "형식:\n"
        "1️⃣ 곡 제목 - 아티스트\n"
        "💬 한 줄 설명\n"
    )

# ==================================================
# 사용자 입력
# ==================================================
user_input = st.chat_input("지금 기분이나 상황을 말해줘 🎶")

if user_input:
    st.session_state.playlist_counter += 1
    playlist_id = f"{date.today()}_{st.session_state.playlist_counter}"

    # 재시도 최대 3회
    for _ in range(3):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": user_input}
            ]
        )

        raw = response.choices[0].message.content
        songs = []

        lines = raw.split("\n")
        i = 0
        while i < len(lines):
            m = re.match(r"\d️⃣\s(.+?)\s-\s(.+)", lines[i])
            if m and i + 1 < len(lines) and lines[i + 1].startswith("💬"):
                title, artist = m.groups()
                desc = lines[i + 1].replace("💬", "").strip()
                songs.append((title, artist, desc))
                i += 2
            else:
                i += 1

        if len(songs) == song_count:
            break

    st.session_state.daily_playlists[playlist_id] = songs
    st.session_state.current_playlist = playlist_id

# ==================================================
# 플레이리스트 출력
# ==================================================
if "current_playlist" in st.session_state:
    pid = st.session_state.current_playlist
    songs = st.session_state.daily_playlists[pid]

    st.subheader(f"🎧 플레이리스트 ({pid})")

    for idx, (title, artist, desc) in enumerate(songs, 1):
        song_id = f"{pid}_{idx}"
        rating = st.session_state.song_ratings.get(song_id)

        query = urllib.parse.quote_plus(f"{title} {artist}")
        youtube_url = f"https://www.youtube.com/results?search_query={query}"

        st.markdown(f"### {idx}. {title} - {artist}")
        st.caption(desc)

        c1, c2, c3, c4 = st.columns([0.8, 0.8, 1.4, 4])

        with c1:
            if st.button("👍", key=f"like_{song_id}", disabled=rating):
                st.session_state.taste_good.append(artist)
                st.session_state.song_ratings[song_id] = "like"

        with c2:
            if st.button("👎", key=f"dislike_{song_id}", disabled=rating):
                st.session_state.taste_bad.append(artist)
                st.session_state.song_ratings[song_id] = "dislike"

        with c3:
            if rating == "like":
                st.markdown("🟢 좋아요")
            elif rating == "dislike":
                st.markdown("🔴 싫어요")
            else:
                st.markdown("⚪ 미평가")

        with c4:
            st.link_button("▶ YouTube", youtube_url)
