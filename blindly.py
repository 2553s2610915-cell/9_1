import streamlit as st
import google.generativeai as genai
import json

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 고대비 접근성 스타일링
# ---------------------------------------------------------
st.set_page_config(
    page_title="VoiceMelody - 시각 장애인을 위한 노래 추천",
    page_icon="🎵",
    layout="wide"
)

# 시각 장애인 및 저시력자를 위한 가독성 향상 CSS
st.markdown("""
    <style>
    /* 전체 글자 크기 확대 및 명암 대비 강화 */
    html, body, [class*="css"] {
        font-size: 1.15rem !important;
        font-family: 'Malgun Gothic', sans-serif;
    }
    .stButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border: 2px solid #1E88E5 !important;
        border-radius: 8px !important;
        margin-bottom: 0.5rem;
    }
    .stTextInput > div > div > input {
        font-size: 1.2rem !important;
        height: 3.2rem;
    }
    .song-card {
        background-color: #f0f4f8;
        border-left: 6px solid #1E88E5;
        padding: 18px;
        margin-bottom: 15px;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Gemini API 키 확인 및 초기화
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("⚠️ Secrets 설정에서 GEMINI_API_KEY를 찾을 수 없습니다. [Secrets 설정 방법]을 참고해 주세요.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    st.error(f"⚠️ Gemini API 초기화 중 오류가 발생했습니다: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 메인 레이아웃 및 설명
# ---------------------------------------------------------
st.title("🎵 VoiceMelody: 시각 장애인을 위한 노래 추천")
st.write("원하는 기분, 장르, 상황을 입력하거나 아래 키워드를 선택하시면 AI가 딱 맞는 노래를 추천해 드립니다.")

st.markdown("---")

# ---------------------------------------------------------
# 4. 입력 섹션 (키워드 버튼 선택 OR 직접 입력)
# ---------------------------------------------------------
st.subheader("1. 추천 방식 선택하기")

col1, col2 = st.columns([1, 1])

# 빠른 태그 선택용 키워드 목록
preset_keywords = [
    "🌧️ 비 오는 날 듣기 좋은 아늑한 노래",
    "☕ 카페에서 공부할 때 듣는 편안한 음악",
    "🏃‍♂️ 운동할 때 들으면 신나는 K-POP",
    "🌙 밤에 잠들기 전에 듣는 조용한 클래식/뉴에이지",
    "🚗 드라이브할 때 듣기 좋은 시원한 팝송",
    "🍂 감성적이고 아련한 짝사랑 발라드"
]

selected_preset = ""
with col1:
    st.markdown("**[방법 A] 자주 찾는 키워드 선택**")
    for kw in preset_keywords:
        if st.button(kw, key=kw):
            selected_preset = kw

with col2:
    st.markdown("**[방법 B] 자유롭게 직접 입력**")
    user_input = st.text_input(
        label="원하는 분위기,
