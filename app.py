import streamlit as st
from openai import OpenAI
import requests
import urllib.parse

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("기분, 상황, 날씨까지 고려해서 DJ가 플레이리스트를 만들어줄게 🔥")

# -----------------------------
# 장르 (확장)
# -----------------------------
GENRES = ["KPOP", "POP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM", "무관"]

# -----------------------------
# 사이드바 설정
# -----------------------------
with st.sidebar:
    st.header("⚙️ 음악 설정")

    genre = st.selectbox("🎵 음악 장르 선택", GENRES)

    song_count = st.slider(
        "🎶 추천 곡 개수",
        min_value=3,
        max_value=10,
        value=5
    )

    city = st.text_input(
        "🌦️ 현재 위치 (날씨 반영)",
        placeholder="예: Seoul"
    )

    reset = st.button("🗑️ 대화 초기화")

    st.caption("🎧 DJ MIX AUTO MODE")

# -----------------------------
# Secrets 체크
# -----------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("🚨 OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

if "OPENWEATHER_API_KEY" not in st.secrets:
    st.error("🚨 OPENWEATHER_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -----------------------------
# 날씨 API 함수
# -----------------------------
def get_weather(city_name):
    if not city_name:
        return "알 수 없음"

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": st.secrets["OPENWEATHER_API_KEY"],
        "units": "metric",
        "lang": "kr"
    }

    try:
        res = requests.get(url, params=params, timeout=5).json()
        return res["weather"][0]["description"]
    except:
        return "알 수 없음"

weather_info = get_weather(city)

# -----------------------------
# session_state 초기화
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if reset:
    st.session_state.messages = []

# -----------------------------
# 시스템 프롬프트 (DJ + 플레이리스트)
# -----------------------------
system_message = {
    "role": "system",
    "content": (
        "당신은 트렌디하고 힙한 DJ입니다 🎧🔥\n"
        "사용자의 기분, 상황, 날씨를 종합해 플레이리스트를 만들어주세요.\n\n"
        "조건:\n"
        f"- 음악 장르는 '{genre}' 기준 (무관이면 장르 자유)\n"
        f"- 추천 곡 개수는 정확히 {song_count}곡\n"
        f"- 현재 날씨: '{weather_info}'\n"
        "- ❗유튜브 '검색 링크'만 제공하세요 (직접 영상 링크 금지)\n"
        "- 링크 형식:\n"
        "  https://www.youtube.com/results?search_query=곡명+아티스트\n"
        "- 말투는 힙한 DJ 멘트처럼\n\n"
        "출력 형식:\n"
        "🎧 오늘의 플레이리스트\n"
        "1️⃣ 곡 제목 - 아티스트\n"
        "👉 추천 이유\n"
        "🔗 유튜브 검색 링크\n"
    )
}

# -----------------------------
# 기존 대화 표시
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# 사용자 입력
# -----------------------------
user_input = st.chat_input(
    "지금 기분/상황을 말해줘 🎶 (예: 비 오는 밤, 혼자 작업 중)"
)

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # -----------------------------
    # AI 응답 (스트리밍)
    # -----------------------------
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response += delta
                placeholder.markdown(full_response + "▌")

        placeholder.markdown(full_response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })
