import os
import streamlit as st
import google.generativeai as genai

# 페이지 기본 설정
st.set_page_config(
    page_title="마음으로 듣는 음악 - 시각 장애인을 위한 노래 추천",
    page_icon="🎵",
    layout="centered"
)

# 고대비 및 접근성 디자인 스타일 적용
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
    </style>
""", unsafe_allow_html=True)

# 헤더 영역
st.title("🎵 마음으로 듣는 음악")
st.markdown("### 시각 장애인을 위한 맞춤형 노래 추천 서비스입니다.")
st.write("듣고 싶으신 노래의 분위기, 상황, 혹은 마음 상태를 자유롭게 적어주세요.")

# API 키 안전하게 불러오기 (Streamlit Secrets 우선, 없으면 환경변수)
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

# 사용자 입력 영역
user_input = st.text_input(
    "어떤 느낌의 노래를 원하시나요?",
    placeholder="예: 마음이 지칠 때 위로가 되는 따뜻한 발라드"
)

# 추천받기 버튼
if st.button("노래 추천받기"):
    if not user_input.strip():
        st.warning("⚠️ 추천받고 싶은 느낌이나 상황을 입력해 주세요.")
    elif not api_key:
        st.error("❌ API Key가 설정되지 않았습니다. Streamlit Secrets에 `GEMINI_API_KEY`를 등록해 주세요.")
    else:
        try:
            # Gemini API 설정 (안정적인 gemini-2.5-flash 모델 사용)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
            당신은 감성적이고 따뜻한 음악 큐레이터입니다.
            사용자가 입력한 느낌이나 상황: "{user_input}"
            
            시각 장애인 사용자에게 마음의 위로와 감동을 줄 수 있는 어울리는 노래 3곡을 추천해 주세요.
            각 노래마다 곡 제목, 아티스트, 추천 이유를 읽기 편한 마크다운 형식으로 작성해 주세요.
            화면 낭독기(스크린 리더)로 읽기 자연스럽도록 정중한 어조로 작성해 주세요.
            """

            with st.spinner("🎧 마음을 담아 어울리는 노래를 고르고 있습니다... 잠시만 기다려 주세요."):
                response = model.generate_content(prompt)
                
            # 결과 출력
            st.markdown("---")
            st.subheader("🎶 추천된 음악 목록")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"❌ AI 응답 중 오류가 발생했습니다: {e}")
            st.info("💡 API Key가 올바른지, 혹은 할당량(Quota)을 초과하지 않았는지 확인해 주세요.")

# 푸터
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #8b949e; font-size: 14px;'>"
    "본 앱은 화면 낭독기 및 고대비 환경을 고려하여 제작되었습니다."
    "</p>", 
    unsafe_allow_html=True
)
