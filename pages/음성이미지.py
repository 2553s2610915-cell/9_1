import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import json

# 1. 페이지 기본 설정 (모바일 및 대형 UI 최적화)
st.set_page_config(
    page_title="SafeVision - 시각장애인 보조 AI",
    page_icon="👁️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS (고대비 및 시각장애인/저시력자용 대형 글씨 스타일)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .status-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
    }
    .danger-box {
        background-color: #ffebe9;
        border: 3px solid #ff4d4f;
        color: #cf1322;
    }
    .warning-box {
        background-color: #fffbe6;
        border: 3px solid #ffe58f;
        color: #d46b08;
    }
    .safe-box {
        background-color: #f6ffed;
        border: 3px solid #b7eb8f;
        color: #389e0d;
    }
    .alert-text {
        font-size: 1.8rem;
        font-weight: bold;
        line-height: 1.4;
    }
    .stButton button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 음성 재생 JS 함수 (문자열 이스케이프 이중 처리로 SyntaxError 예방)
def speak_text(text):
    """브라우저의 Web Speech API(TTS)를 사용하여 한국어 음성을 출력하는 HTML/JS 렌더링"""
    clean_text = text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance('{clean_text}');
            msg.lang = 'ko-KR';
            msg.rate = 1.1;
            msg.pitch = 1.0;
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)

# 3. Gemini Client 초기화 함수
@st.cache_resource
def get_gemini_client(api_key_value):
    return genai.Client(api_key=api_key_value)

# 4. 헤더 영역
st.markdown("<h1 class='main-title'>👁️ SafeVision 보조공학 서비스</h1>", unsafe_allow_html=True)
st.caption("시각장애인을 위한 전방 실시간 장애물 감지 및 음성 안내 앱")

# Secrets 파싱 예외 처리
try:
    api_key = st.secrets.get("GEMINI_API_KEY", None)
except Exception:
    api_key = None

if not api_key:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    st.info("Streamlit Cloud의 [App settings] -> [Secrets] 메뉴에서 GEMINI_API_KEY = \"your_api_key\" 를 입력해주세요.")
    st.stop()

try:
    client = get_gemini_client(api_key)
except Exception as e:
    st.error(f"API 클라이언트 초기화 오류: {e}")
    st.stop()

# 5. 안내 문구
with st.expander("ℹ️ 사용 방법 및 음성 설정", expanded=False):
    st.write("""
    1. 아래 **'전방 향해 카메라 찍기'** 버튼으로 사진을 촬영합니다.
    2. AI가 이미지를 분석하여 위험도와 위치를 파악합니다.
    3. 장애물이 감지되면 **음성(TTS)**으로 즉각 알려줍니다.
    """)

st.subheader("📷 전방 화면 촬영")
camera_image = st.camera_input("전방을 촬영하세요", label_visibility="visible")

# 분석 수행 함수
def analyze_image(image_bytes):
    prompt = """
    당신은 시각장애인을 돕는 AI 보조 안내 시스템입니다.
    제공된 전방 사진을 분석하여 시각장애인이 보행 중 충돌하거나 넘어질 수 있는 위험 요소(장애물, 계단, 턱, 차량, 기둥, 사람, 입간판 등)를 감지하세요.

    반드시 다음 구조의 JSON 형식으로만 응답하세요:
    {
      "risk_level": "DANGER",
      "voice_message": "전방 중앙 1미터 앞에 계단이 있습니다. 주의하세요.",
      "summary": "전방 계단 감지됨",
      "detected_objects": ["계단", "기둥"]
    }

    위험도 기준(risk_level):
    - DANGER: 바로 앞(1~2m 이내)에 충돌/낙상 위험 요소가 있음.
    - WARNING: 진행 방향 주변에 장애물이 있어 주의가 필요함.
    - SAFE: 전방 보행에 장애물이 없고 안전함.
    """

    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {
            "risk_level": "WARNING",
            "voice_message": "분석 결과를 처리하는 중 형식이 맞지 않습니다. 다시 시도해 주세요.",
            "summary": "응답 형식 오류",
            "detected_objects": []
        }
    except Exception as e:
        return {
            "risk_level": "WARNING",
            "voice_message": f"분석 중 오류가 발생했습니다: {str(e)}",
            "summary": "API 처리 오류",
            "detected_objects": []
        }

# 6. 카메라 이미지 감지 처리
if camera_image:
    bytes_data = camera_image.getvalue()
    
    with st.spinner("🔍 전방 장애물 분석 및 위험 감지 중..."):
        analysis = analyze_image(bytes_data)

    risk_level = analysis.get("risk_level", "SAFE")
    voice_msg = analysis.get("voice_message", "분석 결과가 없습니다.")
    summary = analysis.get("summary", "")
    detected_objects = analysis.get("detected_objects", [])

    box_class = "safe-box"
    status_title = "✅ 안전"
    if risk_level == "DANGER":
        box_class = "danger-box"
        status_title = "🚨 위험 경고"
    elif risk_level == "WARNING":
        box_class = "warning-box"
        status_title = "⚠️ 주의 필요"

    st.markdown(f"""
        <div class="status-card {box_class}">
            <h2>{status_title}</h2>
            <p class="alert-text">"{voice_msg}"</p>
        </div>
    """, unsafe_allow_html=True)

    # 음성 출력
    speak_text(voice_msg)

    if st.button("🔊 안내 음성 다시 듣기"):
        speak_text(voice_msg)

    st.markdown("### 📋 감지 상세 정보")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**상황 요약:**", summary)
    with col2:
        st.write("**감지된 항목:**", ", ".join(detected_objects) if detected_objects else "없음")
else:
    st.info("👆 위 카메라 창에서 사진을 찍으면 전방 장애물 감지 및 음성 안내가 시작됩니다.")
