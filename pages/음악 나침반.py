import io
import json
import urllib.parse

import anthropic
import speech_recognition as sr
import streamlit as st
from gtts import gTTS

# ---------------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------------
st.set_page_config(page_title="음악나침반", page_icon="🧭", layout="centered")

# 시각장애인(저시력 포함)을 위한 큰 글씨 + 고대비 스타일
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 22px !important; }
    h1 { font-size: 2.6rem !important; }
    .stButton > button {
        font-size: 1.4rem; padding: 0.8rem 1.2rem; width: 100%;
        border: 3px solid #FFD400; background: #000; color: #FFD400;
    }
    .stButton > button:hover { background: #FFD400; color: #000; }
    </style>
    """,
    unsafe_allow_html=True,
)

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

if "taste_text" not in st.session_state:
    st.session_state.taste_text = ""


# ---------------------------------------------------------------
# 기능 함수
# ---------------------------------------------------------------
def speech_to_text(audio_bytes: bytes) -> str:
    """녹음된 음성(WAV)을 한국어 글자로 변환"""
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio, language="ko-KR")


def text_to_speech(text: str) -> bytes:
    """글자를 한국어 음성(mp3)으로 변환"""
    buf = io.BytesIO()
    gTTS(text=text, lang="ko").write_to_fp(buf)
    return buf.getvalue()


def recommend_songs(user_text: str) -> dict:
    """취향 문장을 분석해서 노래 여러 곡을 추천 (JSON 반환)"""
    system = (
        "너는 시각장애인 사용자를 돕는 친절한 음악 추천 도우미 '음악나침반'이야. "
        "사용자의 글에서 분위기, 장르, 좋아하는 가수, 상황을 분석하고 "
        "취향에 맞는 실제로 존재하는 노래 6곡을 추천해. "
        "반드시 아래 JSON 형식으로만 답하고, 다른 말이나 마크다운은 붙이지 마.\n"
        '{"analysis": "취향 분석 요약 (2문장 이내)", '
        '"songs": [{"title": "곡명", "artist": "가수", "reason": "추천 이유 (1문장)"}]}'
    )
    resp = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_text}],
    )
    raw = resp.content[0].text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ---------------------------------------------------------------
# 화면
# ---------------------------------------------------------------
st.title("🧭 음악나침반")
st.write("듣고 싶은 노래의 분위기, 장르, 가수를 말하거나 적어 주세요. 취향에 맞는 노래를 찾아 읽어 드립니다.")

st.header("1단계. 말로 입력하기")
audio = st.audio_input("마이크 버튼을 눌러 말씀해 주세요. 다시 누르면 녹음이 끝납니다.")

if audio is not None:
    with st.spinner("음성을 글자로 바꾸는 중입니다..."):
        try:
            st.session_state.taste_text = speech_to_text(audio.getvalue())
        except sr.UnknownValueError:
            st.error("음성을 알아듣지 못했어요. 다시 말씀해 주세요.")
        except Exception as e:
            st.error(f"음성 변환 중 문제가 생겼어요: {e}")

st.header("2단계. 글로 입력하거나 확인하기")
user_text = st.text_area(
    "취향 입력창 (말씀하신 내용이 여기에 자동으로 입력됩니다)",
    value=st.session_state.taste_text,
    height=150,
    placeholder="예: 비 오는 날 혼자 듣기 좋은 잔잔한 발라드, 아이유 같은 목소리면 좋겠어요",
)

st.header("3단계. 추천받기")
if st.button("🎵 노래 추천받기"):
    if not user_text.strip():
        st.warning("먼저 취향을 말하거나 적어 주세요.")
    else:
        with st.spinner("취향을 분석하고 노래를 고르는 중입니다..."):
            try:
                result = recommend_songs(user_text)
            except Exception as e:
                st.error(f"추천 중 문제가 생겼어요: {e}")
                st.stop()

        st.subheader("취향 분석")
        st.write(result["analysis"])

        st.subheader("추천 노래")
        speak = f"취향 분석입니다. {result['analysis']} 추천 노래를 알려 드릴게요. "
        for i, s in enumerate(result["songs"], start=1):
            st.markdown(f"**{i}. {s['title']} - {s['artist']}**")
            st.write(s["reason"])
            q = urllib.parse.quote(f"{s['artist']} {s['title']}")
            st.markdown(f"[▶ 유튜브에서 듣기](https://www.youtube.com/results?search_query={q})")
            speak += f"{i}번, {s['artist']}의 {s['title']}. {s['reason']} "

        # 결과를 음성으로 자동 읽어주기
        st.subheader("🔊 추천 결과 음성 안내")
        st.audio(text_to_speech(speak), format="audio/mp3", autoplay=True)
