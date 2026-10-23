import streamlit as st
import cv2
import numpy as np
import time
import base64
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode, ClientSettings

# 페이지 기본 설정
st.set_page_config(
    page_title="시각장애인을 위한 장애물 감지 경고 시스템",
    page_icon="🦯",
    layout="wide"
)

# Custom CSS for accessibility and modern UI
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 20px;
    }
    .warning-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #FEE2E2;
        border: 2px solid #EF4444;
        color: #991B1B;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 15px;
    }
    .safe-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #D1FAE5;
        border: 2px solid #10B981;
        color: #065F46;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🦯 실시간 장애물 감지 및 음성 안내 시스템</div>', unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.title("⚙️ 감지 및 알림 설정")
min_confidence = st.sidebar.slider("객체 감지 민감도", 0.1, 0.9, 0.4, 0.05)
danger_threshold = st.sidebar.slider("위험 거리 영역 비율 (%)", 10, 60, 30, 5)
alert_interval = st.sidebar.slider("음성 알림 간격 (초)", 1.0, 5.0, 2.0, 0.5)

# 브라우저 기반 Web Speech API JavaScript 재생 함수
def speak_text(text):
    if text:
        js_code = f"""
        <script>
            var msg = new SpeechSynthesisUtterance('{text}');
            msg.lang = 'ko-KR';
            msg.rate = 1.1;
            window.speechSynthesis.speak(msg);
        </script>
        """
        st.components.v1.html(js_code, height=0)

# 영상 처리를 위한 Transformer 클래스
class ObstacleDetector(VideoTransformerBase):
    def __init__(self):
        self.last_alert_time = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        height, width, _ = img.shape

        # 간단하고 빠른 명암/윤곽선 기반 장애물 감지 (추가 모델 로드 없이 안정적 실행)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        # 윤곽선(Contour) 기반 장애물 영역 식별
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_obstacles = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 화면 크기 대비 일정 비율 이상인 큰 장애물만 필터링
            if area > (width * height * (min_confidence * 0.02)):
                x, y, w, h = cv2.boundingRect(cnt)
                
                # 장애물 면적 비율
                bbox_area_ratio = (w * h) / (width * height) * 100
                
                # 장애물 위치 (좌 / 중앙 / 우)
                center_x = x + w / 2
                if center_x < width / 3:
                    position = "좌측"
                elif center_x > (width * 2) / 3:
                    position = "우측"
                else:
                    position = "전방 중앙"

                # 위험도 판단 (바운딩 박스 크기 기준)
                is_danger = bbox_area_ratio >= danger_threshold

                color = (0, 0, 255) if is_danger else (0, 255, 0)
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                cv2.putText(img, f"{position} ({int(bbox_area_ratio)}%)", (x, max(y - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if is_danger:
                    detected_obstacles.append((position, bbox_area_ratio))

        # 위험 장애물이 존재할 때 상태 저장
        if detected_obstacles:
            # 가장 큰 장애물 순으로 정렬
            detected_obstacles.sort(key=lambda x: x[1], reverse=True)
            top_obstacle = detected_obstacles[0]
            st.session_state['warning_msg'] = f"⚠️ {top_obstacle[0]}에 근접한 장애물 주의!"
            st.session_state['speech_text'] = f"주의! {top_obstacle[0]}에 장애물이 있습니다."
        else:
            st.session_state['warning_msg'] = "✅ 이동 경로에 위험 장애물이 없습니다."
            st.session_state['speech_text'] = ""

        return img

# 레이아웃 구성
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📹 실시간 웹캠 화면 분석")
    webrtc_ctx = webrtc_streamer(
        key="obstacle-detection",
        mode=WebRtcMode.SENDRECV,
        client_settings=ClientSettings(
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        ),
        video_transformer_factory=ObstacleDetector,
        async_transform=True,
    )

with col2:
    st.subheader("📢 실시간 상태 및 음성 안내")
    
    status_container = st.empty()
    
    if 'warning_msg' in st.session_state:
        if "⚠️" in st.session_state['warning_msg']:
            status_container.markdown(f'<div class="warning-box">{st.session_state["warning_msg"]}</div>', unsafe_allow_html=True)
            # 음성 재생 처리
            if 'speech_text' in st.session_state and st.session_state['speech_text']:
                speak_text(st.session_state['speech_text'])
        else:
            status_container.markdown(f'<div class="safe-box">{st.session_state["warning_msg"]}</div>', unsafe_allow_html=True)
    else:
        status_container.info("카메라를 시작하면 감지가 시작됩니다.")

    st.markdown("---")
    st.markdown("### ℹ️ 이용 안내")
    st.markdown("""
    1. **카메라 시작**: 왼쪽 화면의 `START` 버튼을 눌러 카메라 권한을 허용하세요.
    2. **음성 알림**: 브라우저 소리가 켜져 있는지 확인하세요.
    3. **감도 조절**: 장애물 인식이 너무 예민하거나 둔감한 경우 사이드바에서 감도를 조절할 수 있습니다.
    """)
