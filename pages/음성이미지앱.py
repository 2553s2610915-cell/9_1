import streamlit as st
from PIL import Image
from google import genai
import io

# 페이지 설정
st.set_page_config(
    page_title="아이즈 가드 - 보행 안전 도우미",
    page_icon="👁️",
    layout="centered"
)

# CSS 스타일링 (크고 직관적인 UI)
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
st.markdown('<div class="main-title">👁️ 아이즈 가드 (Eyes Guard)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">전방의 장애물을 실시간으로 감지하고 음성으로 안내합니다.</div>', unsafe_allow_html=True)

# API Key 확인
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `GEMINI_API_KEY`가 설정되어 있지 않습니다. 설정 방법을 확인해주세요.")
    st.stop()

# 브라우저 음성 합성(TTS) 실행 함수
def speak_message(text):
    safe_text = text.replace("'", "\\'").replace('"', '\\"')
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

# 카메라 입력 또는 이미지 업로드
st.markdown("### 📷 전방 촬영")
camera_image = st.camera_input("스마트폰 카메라로 앞을 비추고 촬영 버튼을 누르세요.")

if camera_image is not None:
    try:
        # 이미지 열기
        image = Image.open(camera_image)
        st.image(image, caption="촬영된 전방 시야", use_container_width=True)
        
        with st.spinner("🤖 AI가 전방 위험 요소를 분석 중입니다..."):
            # Gemini 클라이언트 초기화
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            
            prompt = (
                "이 사진은 시각장애인의 전방 시야입니다. 앞에 부딪힐 만한 장애물이나 위험 요소(계단, 공사중, 기둥, "
                "사람 밀집 지역, 차량 등)가 있는지 분석해주세요. "
                "만약 위험 요소가 있다면 '주의! [위험 내용]이 있습니다. 조심하세요.' 형태로 1~2문장으로 간결하게 답해주세요. "
                "위험 요소가 없다면 '안전합니다. 길에 장애물이 없습니다.'라고 답해주세요."
            )
            
            # Gemini 2.5 Flash Lite 모델 호출
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=[image, prompt]
            )
            
            result_text = response.text
            
            # 결과 출력 및 음성 안내
            if "주의" in result_text or "위험" in result_text or "조심" in result_text:
                st.markdown(f'<div class="warning-box">🚨 {result_text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="safe-box">✅ {result_text}</div>', unsafe_allow_html=True)
                
            # 음성으로 읽어주기
            speak_message(result_text)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# 안내 사항
with st.expander("ℹ️ 이용 안내 및 팁"):
    st.write(
        """
        - 스마트폰의 후면 카메라를 전방으로 향하게 하고 촬영 버튼을 누르면 AI가 분석을 시작합니다.
        - 분석 결과는 화면에 표시되는 동시에 **자동으로 음성 안내**됩니다.
        - 본 앱은 보행 보조 참고용으로 사용되며, 실제 보행 시 주변 상황을 항상 주의하시기 바랍니다.
        """
    )
