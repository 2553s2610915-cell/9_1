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

# 2. 음성 재생 JS 함수 생성
def speak_text(text):
    """브라우저의 Web Speech API(TTS)를 사용하여 한국어 음성을 출력하는 HTML/JS 레더링"""
    # 따옴표 및 줄바꿈 예외 처리
    safe_text = text.replace("'", "").replace('"', '').replace('\n', ' ')
    js_code = f"""
        <script>
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel(); // 이전 음성 취소
                var msg = new SpeechSynthesisUtterance('{safe_text}');
                msg.lang = 'ko-KR';
                msg.rate = 1.1; // 읽기 속도
                msg.pitch = 1.0;
                window.speechSynthesis.speak(msg);
            }}
        </script>
    """
    st.components.v1.html(js_code, height=0, width=0)

# 3. Gemini Client 초기화 함수
@st.cache_resource
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

# 4. 헤더 영역
st.markdown("<h1 class='main-title'>👁️ SafeVision 보조공학 서비스</h1>", unsafe_allow_html=True)
st.caption("시각장애인을 위한 전방 실시간 장애물 감지 및 음성 안내 앱")

# API 키 확인 및 예외 처리
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. Secrets 설정을 확인해주세요.")
    st.info("Streamlit Community Cloud의 [App settings] -> [Secrets]에 GEMINI_API_KEY를 등록하세요.")
    st.stop()

try:
    client = get_gemini_client(api_key)
except Exception as e:
    st.error(f"API 클라이언트 초기화 중 오류가 발생했습니다: {e}")
    st.stop()

# 5. 설정 및 안내 모드
with st.expander("ℹ️ 사용 방법 및 음성 설정", expanded=False):
    st.write("""
    1. 아래 **'카메라로 전방 촬영하기'** 버튼을 누르거나 촬영을 수행합니다.
    2. AI가 이미지를 즉시 분석하여 장애물, 위험도, 위치를 파악합니다.
    3. 충돌 위험 요소가 감지되면 **음성(TTS)**으로 즉각 알려줍니다.
    4. 음성이 들리지 않을 경우 스마트폰/PC의 미디어 음량이 켜져 있는지 확인하세요.
    """)

st.subheader("📷 전방 화면 촬영")
camera_image = st.camera_input("전방을 향해 카메라를 찍어주세요", label_visibility="visible")

# 분석 수행 함수
def analyze_image(image_bytes):
    prompt = """
    당신은 시각장애인을 돕는 AI 보조 안내 시스템입니다.
    제공된 전방 사진을 분석하여 시각장애인이 보행 중 충돌하거나 넘어질 수 있는 위험 요소(장애물, 계단, 턱, 차량, 기둥, 사람, 입간판 등)를 감지하세요.

    반드시 다음 구조의 JSON 형식으로만 응답하세요:
    {
      "risk_level": "DANGER" | "WARNING" | "SAFE",
      "voice_message": "시각장애인에게 한국어로 짧고 명확하게 음성으로 읽어줄 경고 문장 (예: '전방 중앙 1미터 앞에 계단이 있습니다. 주의하세요.')",
      "summary": "화면 요약 한 줄 설명",
      "detected_objects": ["감지된 장애물1", "감지된 장애물2"]
    }

    위험도 기준:
    - DANGER: 바로 앞(1~2m 이내)에 충돌/낙상 위험이 높은 장애물(계단, 벽, 차, 사람, 낮은 턱 등)이 있음.
    - WARNING: 진행 방향 주변에 장애물이 있으나 약간의 주의가 필요함.
    - SAFE: 전방 보행에 특별한 장애물이 없고 안전함.
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
        
        # JSON 결과 파싱
        result = json.loads(response.text)
        return result
    except json.JSONDecodeError:
        return {
            "risk_level": "WARNING",
            "voice_message": "전방 분석 결과를 처리하는 중 형식이 맞지 않습니다. 다시 시도해 주세요.",
            "summary": "파싱 오류 발생",
            "detected_objects": []
        }
    except Exception as e:
        return {
            "risk_level": "WARNING",
            "voice_message": f"오류가 발생했습니다: {str(e)}",
            "summary": "API 오류",
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

    # 위험도별 UI CSS 클래스 및 아이콘 설정
    box_class = "safe-box"
    status_title = "✅ 안전"
    if risk_level == "DANGER":
        box_class = "danger-box"
        status_title = "🚨 위험 경고"
    elif risk_level == "WARNING":
        box_class = "warning-box"
        status_title = "⚠️ 주의 필요"

    # UI 결과 출력 (대형 고대비 카드)
    st.markdown(f"""
        <div class="status-card {box_class}">
            <h2>{status_title}</h2>
            <p class="alert-text">"{voice_msg}"</p>
        </div>
    """, unsafe_allow_html=True)

    # 한국어 음성 출력 실행
    speak_text(voice_msg)

    # 음성 다시 듣기 버튼
    if st.button("🔊 안내 음성 다시 듣기"):
        speak_text(voice_msg)

    # 세부 정보
    st.markdown("### 📋 감지 상세 정보")
    col1, col2 = st.columns(2)
    with col1:
        st.write(**"상황 요약:"**, summary)
    with col2:
        st.write(**"감지된 항목:"**, ", ".join(detected_objects) if detected_objects else "없음")

else:
    st.info("👆 위 카메라 창에서 사진 촬영/캡처를 진행하면 전방 장애물 감지 및 음성 안내가 시작됩니다.")
