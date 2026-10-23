import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode, RTCConfiguration

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="시각장애인을 위한 장애물 감지 경고 시스템",
    page_icon="🦯",
    layout="wide"
)

# 2. Custom CSS (고대비 및 가독성 최적화)
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

# 3. 사이드바 설정
st.sidebar.title("⚙️ 감지 및 알림 설정")
min_confidence = st.sidebar.slider("장애물 감지 민감도", 0.1, 0.9, 0.4, 0.05)
danger_threshold = st.sidebar.slider("위험 판단 영역 비율 (%)", 10, 60, 25, 5)

# 4. 브라우저 내장 Web Speech API 기반 음성 출력 함수
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

# 5. 영상 처리 클래스 (VideoProcessorBase 사용으로 최신 streamlit-webrtc 규격 반영)
class ObstacleDetector(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        height, width, _ = img.shape

        # 명암 처리 및 에지(윤곽) 추출
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        # 윤곽선(Contour) 기반 장애물 영역 식별
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_obstacles = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 설정한 민감도 대비 일정 크기 이상의 장애물만 탐지
            if area > (width * height * (min_confidence * 0.015)):
                x, y, w, h = cv2.boundingRect(cnt)
                
                # 화면 대비 장애물 점유 비율 (%)
                bbox_area_ratio = (w * h) / (width * height) * 100
                
                # 위치 구획 (좌 / 전방 중앙 / 우)
                center_x = x + w / 2
                if center_x < width / 3:
                    position = "좌측"
                elif center_x > (width * 2) / 3:
                    position = "우측"
                else:
                    position = "전방 중앙"

                # 위험도 판단 (화면 점유율 기준)
                is_danger = bbox_area_ratio >= danger_threshold

                color = (0, 0, 255) if is_danger else (0, 255, 0)
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                label = f"{position} ({int(bbox_area_ratio)}%)"
                cv2.putText(img, label, (x, max(y - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if is_danger:
                    detected_obstacles.append((position, bbox_area_ratio))

        # 가장 크고 가까운 위험 장애물 상태 기록
        if detected_obstacles:
            detected_obstacles.sort(key=lambda item: item[1], reverse=True)
            top_obstacle = detected_obstacles[0]
            st.session_state['warning_msg'] = f"⚠️ {top_obstacle[0]}에 위험 장애물 접근!"
            st.session_state['speech_text'] = f"주의! {top_obstacle[0]}에 장애물이 있습니다."
        else:
            st.session_state['warning_msg'] = "✅ 이동 경로에 위험 장애물이 없습니다."
            st.session_state['speech_text'] = ""

        return frame.from_ndarray(img, format="bgr24")

# 6. 메인 화면 레이아웃
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📹 실시간 웹
