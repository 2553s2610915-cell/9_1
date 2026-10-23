import streamlit as st
from google import genai
from google.genai import types

# 페이지 설정
st.set_page_config(
    page_title="아이즈 가드 (음성 보행 도우미)",
    page_icon="🎙️",
    layout="centered"
)

# CSS 스타일링
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 2rem;
    }
    .warning-box {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #FEF3C7;
        border: 2px solid #F59E0B;
        font-size: 1.3rem;
        font-weight: bold;
        color: #92400E;
        text-align: center;
        margin-top: 1rem;
    }
    .safe-box {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #D1FAE5;
        border: 2px solid #10B981;
        font-size: 1.3rem;
        font-weight: bold;
        color: #065F46;
        text-align: center;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# 헤더 영역
st.markdown('<div class="main-title">🎙️ 아이즈 가드 (음성 도우미)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">주변 상황을 말로 설명하거나 소리를 녹음하면 AI가 안전을 안내합니다.</div>', unsafe_allow_html=True)

# API Key 확인
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `GEMINI_API_KEY`가 설정되어 있지 않습니다.")
    st.stop()

# 브라우저 음성 합성(TTS) 실행 함수
def speak_message(text):
    safe_text = text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance("{safe_text}");
            utterance.lang = 'ko-KR';
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    st.components.v1.html(js_code, height=0)

# 오디오 입력 영역
st.markdown("### 🗣️ 음성으로 상황 전달하기")
audio_file = st.audio_input("마이크 버튼을 누르고 주변 상황을 말씀해주세요 (예: '앞에 계단이 있는 것 같아', '여기가 건널목이야?')")

if audio_file is not None:
    try:
        st.audio(audio_file)
        
        with st.spinner("🤖 AI가 음성을 분석하고 안전 지침을 생성 중입니다..."):
            # 업로드된 오디오 바이너리 읽기 및 MIME type 확인
            audio_bytes = audio_file.read()
            mime_type = getattr(audio_file, "type", "audio/wav") or "audio/wav"
            
            # Gemini 클라이언트 초기화
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            
            prompt = (
                "이것은 시각장애인이 주변 상황을 음성으로 설명하거나 녹음한 파일입니다. "
                "사용자의 상황과 고민을 바탕으로 현재 예상되는 위험 요소를 분석하고, "
                "1~2문장으로 간결하고 명확하게 주의 사항이나 대처 방법을 안내해주세요. "
                "예: '주의! 앞에 계단이 있을 수 있으니 지팡이로 확인하며 천천히 이동하세요.'"
            )
            
            # Gemini 모델 호출 - 최신 모델 gemini-3.5-flash-lite 적용
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=mime_type,
                    ),
