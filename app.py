import streamlit as st
from openai import OpenAI
import requests
from collections import Counter

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("DJ 캐릭터와 함께, 취향을 학습하는 음악 추천 🎶")

# -----------------------------
# DJ 캐릭터 설정
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

    song_count = st.slider("🎶 곡 수", 3, 30, 10)
    city = st.text_input("🌦️ 도시 (날씨)", "Seoul")

    reset = st.button("🗑️ 초기화")

# -----------------------------
# Secrets
# -----------------------------
if "OPENAI_API_KEY" not in st.secrets or "OPENWEATHER_API_KEY" not in st.secrets:
    st.error("Secrets에 API 키를 설정해주세요.")
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
if "messages" not in st.session_state:
    st.session_state.messages = []

if "taste_good" not in st.session_state:
    st.session_state.taste_good = []

if "taste_bad" not in st.session_state:
    st.session_state.taste_bad = []

if reset:
    st.session_state.messages = []
    st.session_state.taste_good = []
    st.session_state.taste_bad = []

# -----------------------------
# 취향 요약
# -----------------------------
def summarize(lst):
    if not lst:
        return "아직 데이터 없음"
    c = Counter(lst)
    return ", ".join([f"{k}({v})" for k, v in c.most_common(5)])

taste_good = summarize(st.session_state.taste_good)
taste_bad = summarize(st.session_state.taste_bad)

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
        f"- 좋아요 받은 취향: {taste_good}\n"
        f"- 싫어요 받은 취향: {taste_bad}\n\n"
        "조건:\n"
        "- 최소한 싫어요 취향은 피하고, 좋아요 취향을 더 반영\n"
        "- YouTube / Spotify / Apple Music는 검색 링크만 제공\n"
        "- DJ 멘트 스타일 유지\n\n"
        "출력 형식:\n"
        "🎧 오늘의 플레이리스트\n"
        "1️⃣ 곡 제목 - 아티스트\n"
        "👉 추천 이유\n"
        "▶ YouTube: https://www.youtube.com/results?search_query=곡명+아티스트\n"
        "▶ Spotify: https://open.spotify.com/search/곡명%20아티스트\n"
        "▶ Apple Music: https://music.apple.com/kr/search?term=곡명+아티스트\n"
    )
}

# -----------------------------
# 대화 표시
# -----------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# -----------------------------
# 입력
# -----------------------------
user_input = st.chat_input("지금 기분이나 상황을 말해줘 🎶")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""

        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full += delta
                placeholder.markdown(full + "▌")

        placeholder.markdown(full)

    st.session_state.messages.append({"role": "assistant", "content": full})
    st.session_state.last_playlist = full

# -----------------------------
# 👍👎 피드백 버튼
# -----------------------------
if "last_playlist" in st.session_state:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("👍 좋아요"):
            st.session_state.taste_good.append(st.session_state.last_playlist)
            st.success("취향에 반영했어요!")

    with col2:
        if st.button("👎 싫어요"):
            st.session_state.taste_bad.append(st.session_state.last_playlist)
            st.warning("다음엔 다른 스타일로 추천할게요!")
