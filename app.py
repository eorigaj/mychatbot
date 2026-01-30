import streamlit as st
from openai import OpenAI

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="🎧 음악 추천 DJ", page_icon="🎧")
st.title("🎧 음악 추천 DJ")
st.write("기분, 상황에 맞는 음악을 DJ가 바로 추천해줄게 🔥")

# -----------------------------
# 음악 장르
# -----------------------------
GENRES = ["KPOP", "발라드", "재즈", "클래식", "R&B", "힙합", "EDM"]

# -----------------------------
# 사이드바 설정
# -----------------------------
with st.sidebar:
    st.header("⚙️ 음악 설정")

    genre = st.selectbox("🎵 음악 장르 선택", GENRES)

    reset = st.button("🗑️ 대화 초기화")

    st.caption("🎧 Powered by Streamlit Cloud")

# -----------------------------
# OpenAI API Key (Streamlit Secrets)
# -----------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error(
        "🚨 OpenAI API Key가 설정되어 있지 않습니다.\n\n"
        "Streamlit Cloud의 **Settings → Secrets**에\n"
        "`OPENAI_API_KEY`를 추가해주세요."
    )
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -----------------------------
# session_state 초기화
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if reset:
    st.session_state.messages = []

# -----------------------------
# 시스템 프롬프트 (DJ 캐릭터 + 검색 링크 강제)
# -----------------------------
system_message = {
    "role": "system",
    "content": (
        "당신은 트렌디하고 힙한 DJ입니다 🎧🔥\n"
        "사용자의 기분, 상황, 날씨에 어울리는 음악을 추천해주세요.\n\n"
        "조건:\n"
        f"- 음악 장르는 '{genre}' 기준\n"
        "- 최소 3곡 이상 추천\n"
        "- 각 곡마다 간단한 추천 이유 포함\n"
        "- ❗유튜브 '검색 링크'만 제공하세요 (직접 영상 링크 금지)\n"
        "- 링크 형식:\n"
        "  https://www.youtube.com/results?search_query=곡명+아티스트\n"
        "- 말투는 힙하고 친근한 DJ 멘트처럼\n\n"
        "출력 형식:\n"
        "🎶 곡 제목 - 아티스트\n"
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
    "지금 상황/기분/날씨를 말해줘 🎶 (예: 비 오는 밤, 혼자 감성 타임)"
)

if user_input:
    # 사용자 메시지 저장
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

    # AI 메시지 저장
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })
