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
st.write("DJ 캐릭터와 함께 나만의 플레이리스트를 만들어보세요 🎶")

# ==================================================
# DJ 캐릭터 / 장르
# ==================================================
DJ_CHARACTERS = {
    "힙합 DJ": "당신은 힙합과 스트릿 감성에 강한 DJ입니다. 말투는 힙하고 자신감 넘칩니다.",
    "감성 DJ": "당신은 새벽 감성과 감정선을 중시하는 DJ입니다. 말투는 부드럽고 공감적입니다.",
    "클럽 DJ": "당신은 클럽에서 분위기를 터뜨리는 DJ입니다. 말투는 에너지 넘치고 과감합니다.",
    "카페 DJ": "당신은 카페 플레이리스트 전문가 DJ입니다. 말투는 차분하고 따뜻합니다."
}
GENRES = ["KPOP", "POP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM", "무관"]

# ==================================================
# session_state 초기화
# ==================================================
if "playlists" not in st.session_state:
    st.session_state.playlists = {}  # {name: [(title, artist, desc)]}

if "playlist_counter" not in st.session_state:
    st.session_state.playlist_counter = 0

if "current_playlist" not in st.session_state:
    st.session_state.current_playlist = None

# selectbox 상태 저장용
if "playlist_selector" not in st.session_state:
    st.session_state.playlist_selector = None

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
    st.subheader("📚 플레이리스트")

    names = list(st.session_state.playlists.keys())
    if names:
        # 현재 선택이 유효하지 않으면 첫 번째로 보정
        if st.session_state.playlist_selector not in names:
            st.session_state.playlist_selector = names[0]

        selected = st.selectbox(
            "플레이리스트 선택",
            names,
            key="playlist_selector",
        )
        # 선택이 바뀌면 current_playlist 동기화
        st.session_state.current_playlist = selected
    else:
        st.session_state.playlist_selector = None
        st.session_state.current_playlist = None
        st.info("아직 저장된 플레이리스트가 없어요.")

    if st.button("🗑️ 전체 초기화"):
        st.session_state.clear()
        st.rerun()

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
def get_weather(city_name: str):
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city_name,
                "appid": st.secrets["OPENWEATHER_API_KEY"],
                "units": "metric",
                "lang": "kr",
            },
            timeout=5
        ).json()
        return res["weather"][0]["description"]
    except Exception:
        return None

weather = get_weather(city) if use_weather and city else None

# ==================================================
# 새 플레이리스트 이름 입력
# ==================================================
playlist_name_input = st.text_input(
    "✏️ 새 플레이리스트 이름",
    placeholder="예: 비 오는 밤 감성 플레이리스트"
)

# ==================================================
# 시스템 프롬프트
# ==================================================
def build_system_prompt():
    p = (
        f"{DJ_CHARACTERS[dj]}\n\n"
        f"- 장르: {genre} (무관이면 자유)\n"
    )
    if weather:
        p += f"- 현재 날씨: {weather}\n"

    p += (
        f"\n❗ 반드시 정확히 {song_count}곡을 출력하세요.\n"
        f"❗ 아래 형식을 정확히 지키세요.\n\n"
        "형식:\n"
        "1. 곡 제목 - 아티스트\n"
        "💬 한 줄 설명\n"
    )
    return p

# ==================================================
# 사용자 입력 → 플레이리스트 생성
# ==================================================
user_input = st.chat_input("지금 기분이나 상황을 말해줘 🎶")

if user_input:
    st.session_state.playlist_counter += 1

    # 이름 결정
    if playlist_name_input.strip():
        name = playlist_name_input.strip()
    else:
        name = f"{date.today()} 플레이리스트 {st.session_state.playlist_counter}"

    # 중복 방지
    base = name
    k = 1
    while name in st.session_state.playlists:
        name = f"{base} ({k})"
        k += 1

    # 최대 3회 재시도
    songs = []
    for _ in range(3):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": user_input}
            ]
        )
        raw = resp.choices[0].message.content

        parsed = []
        lines = raw.split("\n")
        i = 0
        while i < len(lines):
            m = re.match(r"^\d+\.\s(.+?)\s-\s(.+)", lines[i])
            if m and i + 1 < len(lines) and lines[i + 1].startswith("💬"):
                title, artist = m.groups()
                desc = lines[i + 1].replace("💬", "").strip()
                parsed.append((title.strip(), artist.strip(), desc))
                i += 2
            else:
                i += 1

        if len(parsed) == song_count:
            songs = parsed
            break

    st.session_state.playlists[name] = songs
    # 새로 만든 플레이리스트로 즉시 전환
    st.session_state.current_playlist = name
    st.session_state.playlist_selector = name
    st.rerun()

# ==================================================
# 플레이리스트 이름 수정 / 삭제 (st.form 사용)
# ==================================================
current = st.session_state.current_playlist
if current:
    st.divider()
    st.subheader("🛠️ 플레이리스트 편집")

    with st.form("edit_playlist_form", clear_on_submit=False):
        new_name = st.text_input("이름 수정", value=current)
        col1, col2 = st.columns(2)
        rename_submit = col1.form_submit_button("✏️ 이름 변경")
        delete_submit = col2.form_submit_button("🗑️ 삭제")

        if rename_submit:
            new_name = (new_name or "").strip()
            if not new_name:
                st.warning("이름을 입력해주세요.")
            elif new_name == current:
                st.info("이름이 동일해서 변경할 내용이 없어요.")
            else:
                # 중복 방지
                base = new_name
                k = 1
                while new_name in st.session_state.playlists:
                    new_name = f"{base} ({k})"
                    k += 1

                st.session_state.playlists[new_name] = st.session_state.playlists.pop(current)
                st.session_state.current_playlist = new_name
                st.session_state.playlist_selector = new_name
                st.success("이름을 변경했어요!")
                st.rerun()

        if delete_submit:
            st.session_state.playlists.pop(current, None)

            # 남아있는 것 중 하나로 선택 전환
            remain = list(st.session_state.playlists.keys())
            if remain:
                st.session_state.current_playlist = remain[0]
                st.session_state.playlist_selector = remain[0]
            else:
                st.session_state.current_playlist = None
                st.session_state.playlist_selector = None

            st.success("플레이리스트를 삭제했어요!")
            st.rerun()

# ==================================================
# 플레이리스트 출력
# ==================================================
current = st.session_state.current_playlist
if current:
    songs = st.session_state.playlists.get(current, [])
    st.subheader(f"🎧 {current}")

    if not songs:
        st.info("곡을 파싱하지 못했어요. (모델 출력 형식이 어긋났을 수 있어요) 다시 생성해보세요!")
    else:
        for i, (title, artist, desc) in enumerate(songs, 1):
            query = urllib.parse.quote_plus(f"{title} {artist}")
            youtube_url = f"https://www.youtube.com/results?search_query={query}"

            st.markdown(f"### {i}. {title} - {artist}")
            st.caption(f"💬 {desc}")
            st.link_button("▶ YouTube에서 듣기", youtube_url)
