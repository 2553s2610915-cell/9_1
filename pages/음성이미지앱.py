import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 1. 페이지 설정 (고대비 및 접근성 고려)
st.set_page_config(
    page_title="시각장애인을 위한 음성 장애물 감지기",
    page_icon="🦯",
    layout="centered"
)

# 커스텀 CSS (고대비 / 대형 텍스트)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem !important;
        font-weight: 800;
        color: #FFFF00;
        background-color: #000000;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .danger-box {
        background-color: #FF0000;
        color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        margin-top: 15px;
    }
    .safe-box {
        background-color: #008000;
        color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# 브라우저 TTS(Text-To-Speech) 음성 출력 함수
def play_tts_javascript(text):
    clean_text = text.replace("'", "").replace('"', '').replace('\n', ' ')
    js_code = f"""
        <script>
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel(); // 이전 음성 취소
                var msg = new SpeechSynthesisUtterance('{clean_text}');
                msg.lang = 'ko-KR';
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
            }}
        </script>
    """
    st.components.v1.html(js_code, height=0)

# Gemini API 초기화
def get_gemini_model():
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        st.error("⚠️ GEMINI_API_KEY가 Secrets에 설정되지 않았습니다.")
        return None
    
    try:
        genai.configure(api_key=api_key)
        # 요구사항에 명시된 gemini-2.5-flash-lite 사용
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        return model
    except Exception as e:
        st.error(f"API 연결 오류: {e}")
        return None

# UI 헤더
st.markdown("<div class='main-title'>🦯 음성 장애물 감지 및 안내 시스템</div>", unsafe_allow_html=True)

model = get_gemini_model()

if model:
    # 모드 선택
    input_type = st.radio(
        "입력 방식을 선택하세요:",
        ("📷 카메라로 실시간 촬영", "📁 이미지 파일 업로드"),
        horizontal=True
    )

    image_data = None

    if input_type == "📷 카메라로 실시간 촬영":
        camera_image = st.camera_input("전방을 촬영하세요 (보행 경로)")
        if camera_image:
            image_data = Image.open(camera_image)
    else:
        uploaded_file = st.file_uploader("전방 이미지를 업로드하세요", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_data = Image.open(uploaded_file)

    if image_data:
        st.image(image_data, caption="분석 대상 이미지", use_container_width=True)
        
        analyze_btn = st.button("🚨 장애물 감지 및 음성 안내 시작", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner("전방 장애물 및 충돌 위험 분석 중..."):
                try:
                    prompt = """
                    너는 시각장애인을 위한 전방 보행 안내 AI 도우미이다.
                    제시된 이미지를 보고 보행에 방해가 되는 장애물, 차량, 사람, 턱, 계단 등을 분석하라.

                    [응답 규칙]
                    1. 첫 번째 줄에는 오직 [위험] 또는 [안전] 중 하나만 출력하라. (충돌 위험이나 보행 장애물이 있으면 [위험], 전방이 깨끗하면 [안전])
                    2. 두 번째 줄부터는 시각장애인에게 말로 들려줄 핵심 안내 문장을 작성하라. 
                    - 위치(좌, 우, 중앙)와 장애물 종류, 대략적인 거리감을 간결하고 명확하게 한국어로 적어라.
                    - 경고문은 최대 2~3문장 이내로 작성하라.
                    
                    예시:
                    [위험]
                    전방 중앙 약 2미터 앞에 자전거와 볼라드가 있습니다. 오른쪽으로 우회하세요.
                    """

                    response = model.generate_content([prompt, image_data])
                    result_text = response.text.strip()

                    # 결과 처리
                    lines = result_text.split('\n')
                    status = lines[0].strip() if lines else "[안전]"
                    speech_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else result_text

                    if "[위험]" in status:
                        st.markdown(f"<div class='danger-box'>🚨 경고: 전방 위험 요소 감지</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='safe-box'>✅ 전방 안전함</div>", unsafe_allow_html=True)

                    st.markdown("### 🔊 음성 안내 내용")
                    st.info(speech_text)

                    # 브라우저 음성(TTS) 출력
                    play_tts_javascript(speech_text)

                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다: {e}")
                    play_tts_javascript("이미지 분석 중 오류가 발생했습니다. 다시 시도해 주세요.")
else:
    st.info("💡 배포 후 Secrets에 GEMINI_API_KEY를 등록해야 정상 작동합니다.")
