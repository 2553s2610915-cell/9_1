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
    .permission-card {
        background-color: #f0f2f5;
        border-left: 5px solid #1890ff;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 음성 재생 JS 함수
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

# 3. 카메라 권한 확인 및 요청 컴포넌트 함수
def render_camera_permission_check():
    """브라우저의 카메라 접근 권한 상태를 확인하고 허용을 유도하는 HTML/JS 컴포넌트"""
    permission_html = """
    <div style="background-color: #e6f7ff; border: 2px solid #91d5ff; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
        <h4 style="margin:0 0 8px 0; color: #0050b3;">📷 카메라 접근 권한 확인</h4>
        <p id="perm-status" style="margin: 0 0 10px 0; font-size: 14px; color: #262626;">권한 상태를 확인하고 있습니다...</p>
        <button id="perm-btn" onclick="requestCameraPermission()" style="padding: 8px 16px; font-size: 14px; font-weight: bold; background-color: #1890ff; color: white; border: none; border-radius: 6px; cursor: pointer;">
            카메라 권한 요청 / 확인
        </button>
    </div>

    <script>
    function updateStatus(message, isSuccess) {
        var statusEl = document.getElementById('perm-status');
        if (statusEl) {
            statusEl.innerText = message;
            statusEl.style.color = isSuccess ? '#389e0d' : '#cf1322';
            statusEl.style.fontWeight = 'bold';
        }
    }

    async function checkPermission() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            updateStatus('이 브라우저는 카메라 접근을 지원하지 않거나 HTTPS 보안 연결이 아닙니다.', false);
            return;
        }

        try {
            if (navigator.permissions && navigator.permissions.query) {
                const result = await navigator.permissions.query({ name: 'camera' });
                if (result.state === 'granted') {
                    updateStatus('✅ 카메라 권한이 허용되었습니다. 아래 카메라 창을 이용하세요.', true);
                } else if (result.state === 'prompt') {
                    updateStatus('⚠️ 카메라 권한 승인이 필요합니다. 아래 버튼을 눌러 허용해 주세요.', false);
                } else if (result.state === 'denied') {
                    updateStatus('❌ 카메라 권한이 차단되어 있습니다. 브라우저 주소창 왼쪽의 자물쇠/설정 아이콘을 눌러 권한을 허용으로 변경해 주세요.', false);
                }
            }
        } catch (e) {
            console.log("Permission Query API 미지원:", e);
        }
    }

    async function requestCameraPermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            updateStatus('✅ 카메라 접근이 승인되었습니다!', true);
            // 권한 획득 후 스트림 즉시 해제 (Streamlit camera_input이 사용할 수 있도록)
            stream.getTracks().forEach(track => track.stop());
        } catch (err) {
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                updateStatus('❌ 카메라 접근이 거부되었습니다. 주소창 자물쇠 아이콘에서 카메라 권한을 [허용]으로 바꿔주세요.', false);
            } else {
                updateStatus('카메라 접근 오류: ' + err.message, false);
            }
        }
    }

    // 페이지 로드시 자동 권한 상태 체크
    checkPermission();
    </script>
    """
    st.components.v1.html(permission_html, height=135)

# 4. Gemini Client 초기화 함수
@st.cache_resource
def get_gemini_client(api_key_value):
    return genai.Client(api_key=api_key_value)

# 5. 헤더 영역
st.markdown("<h1 class='main-title'>👁️ 음성 이미지</h1>", unsafe_allow_html=True)
st.caption("시각장애인을 위한 전방 실시간 장애물 감지 및 음성 안내 앱")

# Secrets 파싱 예외 처리
try:
    api_key = st.secrets.get("GEMINI_API_KEY", None)
except Exception:
    api_key = Noneㅂㅁ

if not api_key:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")ㅂ

    반드시 다음 구조의 JSON 형식으로만 응답하세요:
    {
      "risk_level": "DANGER",
