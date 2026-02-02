import streamlit as st
from openai import OpenAI
import requests
from collections import Counter
from datetime import date
import re
import urllib.parse

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("DJ 캐릭터와 함께, 취향을 학습하는 음악 추천 🎶")

# -----------------------------
# DJ 캐릭터
# -----------------------------
DJ_CHARACTERS = {
    "힙합 DJ": "당신은 힙합과 스트릿 감성에 강한 DJ입니다. 말투는 힙하고 자신감 넘칩니다.",
    "감성 DJ": "당신은 새벽 감성과 감정선을 중시하는 DJ입니다. 말투는 부드럽고 공감적입니다.",
    "클럽 DJ": "당신은 클럽에서 분위기를 터뜨리는 DJ입니다. 말투는 에너지 넘치고 과감합니다.",
    "카페 DJ": "당신은 카페 플레이리스트 전문가 DJ입니다. 말투는 차분하고 따뜻합니다."
}

GENRES = ["KPOP", "POP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM", "무관"]

# -----------------------------
# 사이드바
# -----------------------------
with st.sidebar:
    st.header("⚙️ 설정")

    dj = st.selectbox("🎧 DJ 캐릭터", list(DJ_CHARACTERS.keys()))
    genre = st.selectbox("🎵 장르", GENRES)
    song_count = st.slider("🎶 추천 곡 수", 3, 30, 10)
    city = st.text_input("🌦️ 도시", "Seoul")

    reset = st.button("🗑️ 전체 초기화")

# -----------------------------
# Secrets
# -----------------------------
if "OPENAI_API_KEY" not in st.secrets or "OPENWEATHER_API_KEY" not in st.secrets:
    st.error("🚨 Streamlit Secrets에 API 키를 설정해주세요.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -----------------------------
# 날씨
# -----------------------------
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

# -----------------------------
# session_state
# -----------------------------
if "taste_good" not in st.session_state:
    st.session_state.taste_good = []

if "taste_bad" not in st.session_state:
    st.session_state.taste_bad = []

if "daily_playlists" not in st.session_state:
    st.session_state.daily_playlists = {}  # {date: [songs]}

if reset:
    st.session_state.clear()
    st.experimental_rerun()

# -----------------------------
# 취향 요약
# -----------------------------
def summarize(lst):
    if not lst:
        return "없음"
    c = Counter(lst)
    return ", ".join([f"{k}({v})" for k, v in c.most_common(5)])

# -----------------------------
# 시스템 프롬프트
# -----------------------------
system_message = {
    "role": "system",
    "content": (
        f"{DJ_CHARACTERS[dj]}\n\n"
        "당신은 사용자의 음악 취향을 학습하는 DJ입니다.\n\n"
        f"- 장르: {genre} (무관이면 자유)\n"
        f"- 추천 곡 수: {song_count}곡\n"
        f"- 날씨: {weather}\n"
        f"- 좋아요 취향: {summarize(st.session_state.taste_good)}\n"
        f"- 싫어요 취향: {summarize(st.session_state.taste_bad)}\n\n"
        "조건:\n"
        "- 좋아요 취향은 더 반영하고 싫어요 취향은 피하세요\n"
        "- 유튜브 검색 링크만 제공하세요\n"
        "- 아래 형식으로만 출력하세요:\n\n"
        "1️⃣ 곡 제목 - 아티스트\n"
    )
}

# -----------------------------
# 사용자 입력
# -----------------------------
user_input = st.chat_input("지금 기분이나 상황을 말해줘 🎶")

if user_input:
    with st.spinner("🎧 DJ가 플레이리스트를 믹싱 중..."):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message, {"role": "user", "content": user_input}]
        )

    raw = response.choices[0].message.content

    # -----------------------------
    # 곡 파싱
    # -----------------------------
    songs = []
    for line in raw.split("\n"):
        match = re.match(r"\d️⃣\s(.+?)\s-\s(.+)", line)
        if match:
            title, artist = match.groups()
            songs.append((title.strip(), artist.strip()))

    # -----------------------------
    # 하루 플레이리스트 저장
    # -----------------------------
    today = str(date.today())
    st.session_state.daily_playlists[today] = songs

    st.subheader(f"🎧 오늘의 플레이리스트 ({today})")

    # -----------------------------
    # 곡별 출력 + 👍👎 + 링크 버튼
    # -----------------------------
    for i, (title, artist) in enumerate(songs, 1):
        query = urllib.parse.quote_plus(f"{title} {artist}")
        youtube_url = f"https://www.youtube.com/results?search_query={query}"

        st.markdown(f"### {i}. {title} - {artist}")

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            if st.button("👍", key=f"like_{today}_{i}"):
                st.session_state.taste_good.append(artist)
                st.success("좋아요 반영!")

        with col2:
            if st.button("👎", key=f"dislike_{today}_{i}"):
                st.session_state.taste_bad.append(artist)
                st.warning("싫어요 반영!")

        with col3:
            st.link_button("🎬 YouTube에서 듣기", youtube_url)

# -----------------------------
# 저장된 하루 플레이리스트 보기
# -----------------------------
if st.session_state.daily_playlists:
    st.divider()
    st.subheader("📅 저장된 플레이리스트")

    for d, plist in st.session_state.daily_playlists.items():
        st.markdown(f"**{d}** — {len(plist)}곡")
