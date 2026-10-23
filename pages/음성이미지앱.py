import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import cv2
import numpy as np
import google.generativeai as genai
from PIL import Image
import io
import time

# 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(
    page_title="시각장애인 보행 보조 - 장애물 알림",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

# 고대비 및 대형 폰트 스타일 적용 (저시력자 접근성)
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A8A; text-align: center; margin-bottom: 20px; }
    .alert-box-danger { background-color: #FEE2E2; border: 4px solid #DC2626; padding: 20px; border-radius: 12px; text-align: center; }
    .alert-box-safe { background-color: #D1FAE5; border: 4px solid #059669; padding: 20px; border-radius: 12px; text-align: center; }
    .status-text { font-size: 2rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">👁️ 시각장애인 실시간 장애물 감지 및 음성 알림</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. Gemini API 설정
# ---------------------------------------------------------
gemini_available = False
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # gemini-2.5-flash-lite 모델 설정
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        gemini_available = True
    except Exception as e:
        st.sidebar.error(f"Gemini API 연동 실패: {e}")
else:
    st.sidebar.warning("Secrets에 GEMINI_API_KEY가 설정되지 않았습니다. 기본 컴퓨터 비전 감지만 동작합니다.")

# ---------------------------------------------------------
# 2. 비디오 프레임 처리 클래스 (Computer Vision 기반)
# ---------------------------------------------------------
class ObstacleDetector(VideoTransformerBase):
    def __init__(self):
        self.last_capture_time = 0
        self.latest_frame = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        height, width, _ = img.shape
        
        # 전방 관심 영역 (ROI) 설정: 화면 중앙 하단 영역 (보행 시 전방 바닥 및 장애물 위치)
        roi_y1, roi_y2 = int(height * 0.4), int(height * 0.9)
        roi_x1, roi_x2 = int(width * 0.25), int(width * 0.75)
        
        # ROI 영역 표시 (시각적 가이드)
        cv2.rectangle(img, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 255, 255), 2)
        
        # 간단하고 유효한 장애물 감지 logic: ROI 내의 엣지(Edge) 밀도 측정
        gray_roi = cv2.cvtColor(img[roi_y1:roi_y2, roi_x1:roi_x2], cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

        # 엣지 밀도가 기준치 이상이면 장애물이 근접한 것으로 간주
        is_obstacle = edge_density > 0.08  # 임계값 설정
        
        if is_obstacle:
            # 경고 박스 및 텍스트 표시
            cv2.putText(img, "WARNING: OBSTACLE DETECTED", (30, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.rectangle(img, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 0, 255), 4)
        else:
            cv2.putText(img, "SAFE: CLEAR PATH", (30, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

        self.latest_frame = img
        return img

# ---------------------------------------------------------
# 3. 레이아웃 구성
# ---------------------------------------------------------
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("📹 실시간 전방 카메라")
    ctx = webrtc_streamer(
        key="obstacle-detection",
        mode=WebRtcMode.SENDRECV,
        video_transformer_factory=ObstacleDetector,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True
    )

with col2:
    st.subheader("📢 음성 안내 및 AI 분석")
    
    # 웹 브라우저 음성 출력(TTS) 자바스크립트 컨트롤러
    st.markdown("""
        <script>
        function speakText(text) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); // 이전 음성 취소
                var msg = new SpeechSynthesisUtterance(text);
                msg.lang = 'ko-KR';
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
            }
        }
        </script>
    """, unsafe_allow_html=True)

    # 음성 알림 테스트 버튼
    if st.button("🔊 음성 알림 테스트 실행", use_container_width=True):
        st.components.v1.html("""
            <script>
            var msg = new SpeechSynthesisUtterance('음성 안내 기능이 정상적으로 작동 중입니다.');
            msg.lang = 'ko-KR';
            window.speechSynthesis.speak(msg);
            </script>
        """, height=0)
        st.success("음성 안내를 출력했습니다.")

    st.markdown("---")
    st.markdown("### 🤖 Gemini AI 정밀 정황 분석")
    st.info("카메라에 잡힌 전방 화면의 세부 위험 요소를 분석하여 음성으로 상세 설명합니다.")

    if st.button("🔍 전방 정황 AI 분석하기", use_container_width=True):
        if not gemini_available:
            st.error("GEMINI_API_KEY가 설정되어 있지 않습니다.")
        elif ctx and ctx.video_transformer and ctx.video_transformer.latest_frame is not None:
            frame = ctx.video_transformer.latest_frame
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)

            with st.spinner("Gemini AI가 전방 위험 요소를 분석 중입니다..."):
                try:
                    prompt = """
                    당신은 시각장애인을 돕는 음성 보행 보조 AI입니다.
                    사진 속 전방 시야에 있는 주요 장애물(의자, 계단, 벽, 사람, 차 등)을 파악하고,
                    시각장애인이 안전하게 이동할 수 있도록 2~3문장의 명확하고 다정한 한국어 음성 메시지 스타일로 설명해 주세요.
                    예시: "전방 1미
