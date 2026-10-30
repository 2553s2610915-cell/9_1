import streamlit as st
from google import genai
import json

# ---------------------------------------------------------
# 1. 페이지 설정 및 스포티파이 스타일 UI Custom CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="VoiceMelody - AI Music Curator",
    page_icon="🎵",
    layout="wide"
)

# 스포티파이 느낌의 다크 패널 UI 스타일링
st.markdown("""
    <style>
    /* 전체 배경색 - 딥 다크 메인 테마 */
    .stApp {
        background-color: #121212 !important;
        color: #FFFFFF !important;
        font-family: 'Malgun Gothic', sans-serif;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #000000 !important;
        padding-top: 1rem;
    }
    
    /* 메인 영역 카드리스트 패널 */
    .spotify-card {
        background-color: #181818;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 14px;
        border: 1px solid #282828;
    }
    
    /* 타이틀 및 네온 강조 텍스트 */
    .song-title {
        color: #1DB954;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 4px;
    }
    .artist-name {
        color: #B3B3B3;
        font-size: 1.0rem;
        margin-bottom: 8px;
    }
    .reason-text {
        color: #E5E5E5;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* 스포티파이 시그니처 그리너리 버튼 스타일 */
    .stButton > button {
        background-color: #1DB954 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-size: 1.05rem !important;
        width: 100%;
        margin-bottom: 6px;
    }
    
    /* 텍스트 입력창 스타일 */
    .stTextInput > div > div > input {
        background-color: #242424 !important;
        color: #FFFFFF !important;
        border: 1px solid #3E3E3E !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Gemini Client 초기화 (최신 SDK)
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("⚠️ Secrets 설정에서 GEMINI_API_KEY를 찾을 수 없습니다.")
    st.stop()

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API 초기화 실패: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 사이드바 (내 라이브러리 & 키워드 퀵 선택)
# ---------------------------------------------------------
with st.sidebar:
    st.title("🎵 VoiceMelody")
    st.caption("시각 장애인 및 음성 사용자 전용 추천")
    
    st.markdown("---")
    st.markdown("### 📚 빠른 키워드 선택")
    
    presets = [
        "🌧️ 비 오는 날 감성 발라드",
        "☕ 카페 느낌의 편안한 재즈",
        "🏃‍♂️ 드라이브용 신나는 K-POP",
        "🌙 수면 유도 조용한 뉴에이지",
        "🎸 90년대 따뜻한 록 밴드"
    ]
    
    selected_preset = ""
    for p in presets:
        if st.button(p, key=f"sidebar_{p}"):
            selected_preset = p

# ---------------------------------------------------------
# 4. 메인 화면 (프로필/검색 및 카드뷰)
# ---------------------------------------------------------
st.markdown("## 🎧 AI 음악 큐레이터")
st.write("원하는 느낌이나 가사를 자유롭게 적거나, 왼쪽 라이브러리에서 빠른 키워드를 선택해 보세요.")

st.markdown("<br>", unsafe_allow_html=True)

user_input = st.text_input(
    label="어떤 분위기의 노래를 찾으시나요?",
    placeholder="예: 마음이 차분해지는 새벽 들을만한 노래 알려줘",
    key="custom_query"
)

# 입력 우선순위 처리
final_query = user_input.strip() if user_input.strip() else selected_preset

st.markdown("<br>", unsafe_allow_html=True)

if final_query:
    st.info(f"선택된 테마: **{final_query}**")

# 추천 실행 버튼
if st.button("▶ 추천 음악 불러오기", type="primary"):
    if not final_query:
        st.warning("분위기를 입력하거나 왼쪽 메뉴에서 키워드를 선택해 주세요.")
    else:
        with st.spinner("🎵 당신을 위한 음악 플레이리스트를 구성하는 중..."):
            prompt = f"""당신은 시각장애인을 포함한 음악 사랑꾼을 위한 친절한 음악 큐레이터입니다.
요청 테마: "{final_query}"

위 테마에 딱 맞는 노래 3곡을 추천해 주세요.
반드시 마크다운 코드 블록(```json) 없이 오직 JSON 텍스트 형식으로만 답변해야 합니다.

{{
    "summary": "추천 배경 및 큐레이터의 메시지",
    "songs": [
        {{
            "title": "곡 제목",
            "artist": "가수명",
            "genre": "장르",
            "reason": "추천 이유 및 음악적 감상 포인트"
        }}
    ]
}}"""

            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=prompt
                )
                
                res_text = response.
