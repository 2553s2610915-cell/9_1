import os
import streamlit as st
import google.generativeai as genai

# 페이지 기본 설정 (와이드 레이아웃 및 접근성 고려 타이틀)
st.set_page_config(
    page_title="마음으로 듣는 음악 - 시각 장애인을 위한 노래 추천",
    page_icon="🎵",
    layout="centered"
)

# [디자인 및 접근성 설정] 고대비 스타일 및 큰 글씨 적용
st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
        color: #f0f6fc;
        font-size: 18px;
    }
    .stTextInput > div > div > input {
        background-color: #161b22;
        color: #f0f6fc;
        font-size: 18px;
        border: 2px solid #58a6ff;
    }
    .stButton > button {
        background-color: #238636;
        color: white;
        font-size: 20px;
        font-weight: bold;
        width: 100%;
        padding: 12px;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background-color: #2ea043;
    }
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    .song-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# 헤더 영역
st.title("🎵 마음으로 듣는 음악")
st.markdown("### 시각 장애인을 위한 맞춤형 노래 추천 서비스입니다.")
st.write("듣고 싶으신 노래의 분위기, 상황, 혹은 마음 상태를 자유롭게 적어주세요. AI가 마음을 어루만져 줄 노래를 추천해 드립니다.")

# API 키 설정 확인 (Streamlit Secrets 활용)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

# 사용자 입력 영역
user_input = st.text_input(
    "어떤 느낌의 노래를 원하시나요?",
    placeholder="예: 마음이 지칠 때 위로가 되는 따뜻한 발라드",
    help="키워드나 문장 형태로 편하게 입력해 주세요."
)

# 추천받기 버튼
if st.button("노래 추천받기"):
    if not user_input.strip():
        st.warning("⚠️ 추천받고 싶은 느낌이나 상황을 입력해 주세요.")
    elif not api_key:
        st.error("❌ API Key가 설정되지 않았습니다. Streamlit Secrets 설정을 확인해 주세요.")
    else:
        try:
            # Gemini API 설정 (gemini-2.5-flash-lite 모델 사용)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash-lite")

            # 프롬프트 구성
            prompt = f"""
            당신은 감성적이고 따뜻한 음악 큐레이터입니다.
            사용자가 입력한 느낌이나 상황: "{user_input}"
            
            시각 장애인 사용자에게 마음의 위로와 감동을 줄 수 있는 어울리는 노래 3곡을 추천해 주세요.
            각 노래마다 다음 정보를 포함하여 JSON 형식이 아닌, 읽기 편한 마크다운 형식으로 작성해 주세요.
            
            1. 곡 제목 및 아티스트
            2. 추천하는 이유 (이 노래가 사용자에게 전하는 감성과 위로)
            
            화면 낭독기(스크린 리더)로 읽기에도 자연스럽도록 명확하고 정중한 어조로 작성해 주세요.
            """

            with st.spinner("🎧 마음을 담아 어울리는 노래를 고르고 있습니다... 잠시만 기다려 주세요."):
                response = model.generate_content(prompt)
                
            # 결과 출력
            st.markdown("---")
            st.subheader("🎶 추천된 음악 목록")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {e}")
            st.info("💡 잠시 후 다시 시도해 주시거나, API Key 설정을 다시 확인해 주세요.")

# 접근성 안내 푸터
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #8b949e; font-size: 14px;'>"
    "본 앱은 화면 낭독기 및 고대비 환경을 고려하여 제작되었습니다."
    "</p>", 
    unsafe_allow_html=True
)

