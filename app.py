import streamlit as st
from openai import OpenAI
import requests
from datetime import date
import re
import urllib.parse

# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("DJ 캐릭터와 함께 음악 플레이리스트를 추천해드려요 🎶")

# ==================================================
# DJ 캐릭터
# ==================================================
DJ_CHARACTERS = {
    "힙합 DJ": "당신은 힙합과 스트릿 감성에 강한 DJ입니다. 말투는 힙하고 자신감 넘칩니다.",
    "감성 DJ": "당신은 새벽 감성과 감정선을 중시하는 DJ입니다. 말투는 부드럽고 공감적입니다.",
    "클럽 DJ": "당신은 클럽에서 분위기를 터뜨리는 DJ입니다. 말투는 에너지 넘치고 과감합니다.",
    "카페 DJ": "당신은 카페 플레이리스트 전문가 DJ입니다. 말투는 차분하고 따뜻합니다."
}

GENRES = ["KPOP", "POP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM", "무관"]

# ==================================================
# 사이드바
# ==================================================
with st.sidebar:
    st.header("⚙️ 설정")

    dj = st.selectbox("🎧 DJ 캐릭터", list(DJ_CHARACTERS.keys()))
    genre = st.selectbox("🎵 장르", GENRES)
    song_count = st.slider("🎶 추천 곡 수", 3, 30, 10)

    use_weather = st.checkbox("🌦️ 날씨 반영", value=True)
    city = st.text_input("도시", "Seoul") if use_weather else None

    st.divider()
    st.subheader("📚 이전 플레이리스트")

    if "playlists" in st.session_state and st.session_state.playlists:
        selected_pid = st.selectbox(
            "다시 보기",
            list(st.session_state.playlists.keys())
        )
    else:
        selected_pid = None

    if st.button("🗑️ 전체 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

# ==================================================
# Secrets
# ==================================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("🚨 OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==================================================
# 날씨 API (선택적)
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
        return None

weather = get_weather(city) if use_weather and city else None

# ==================================================
# session_state 초기화
# ==================================================
if "playlists" not in st.session_state:
    st.session_state.playlists = {}  # {playlist_id: [(title, artist, desc), ...]}

if "playlist_counter" not in st.session_state:
    st.session_state.playlist_counter = 0

if "current_playlist" not in st.session_state:
    st.session_state.current_playlist = None

# ==================================================
# 시스템 프롬프트 생성
# ==================================================
def build_system_prompt():
    prompt = (
        f"{DJ_CHARACTERS[dj]}\n\n"
        f"- 장르: {genre} (무관이면 자유)\n"
    )

    if weather:
        prompt += f"- 현재 날씨: {weather}\n"

    prompt += (
        f"\n❗ 반드시 정확히 {song_count}곡을 출력하세요.\n"
        f"❗ 아래 형식을 정확히 지키세요.\n\n"
        "형식:\n"
        "1. 곡 제목 - 아티스트\n"
        "💬 한 줄 설명\n"
    )
    return prompt

# ==================================================
# 사용자 입력
# ==================================================
user_input = st.chat_input("지금 기분이나 상황을 말해줘 🎶")

if user_input:
    st.session_state.playlist_counter += 1
    playlist_id = f"{date.today()}_{st.session_state.playlist_counter}"

    # 최대 3회 재시도
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
            match = re.match(r"^\d+\.\s(.+?)\s-\s(.+)", lines[i])
            if match and i + 1 < len(lines) and lines[i + 1].startswith("💬"):
                title, artist = match.groups()
                desc = lines[i + 1].replace("💬", "").strip()
                songs.append((title.strip(), artist.strip(), desc))
                i += 2
            else:
                i += 1

        if len(songs) == song_count:
            break

    st.session_state.playlists[playlist_id] = songs
    st.session_state.current_playlist = playlist_id

# ==================================================
# 표시할 플레이리스트 결정
# ==================================================
playlist_to_show = st.session_state.current_playlist or selected_pid

# ==================================================
# 플레이리스트 출력
# ==================================================
if playlist_to_show:
    songs = st.session_state.playlists.get(playlist_to_show, [])

    st.subheader(f"🎧 플레이리스트 ({playlist_to_show})")

    for idx, (title, artist, desc) in enumerate(songs, 1):
        query = urllib.parse.quote_plus(f"{title} {artist}")
        youtube_url = f"https://www.youtube.com/results?search_query={query}"

        st.markdown(f"### {idx}. {title} - {artist}")
        st.caption(f"💬 {desc}")
        st.link_button("▶ YouTube에서 듣기", youtube_url)
