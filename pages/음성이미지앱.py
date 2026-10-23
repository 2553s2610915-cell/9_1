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

# 2. Custom CSS
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

# 4. 브라우저 내장 Web Speech API 기반 음성 출력 함수 (SyntaxError 방지 처리 완료)
def speak_text(text):
    if text:
        js_code = f"""
        <script>
            var msg = new SpeechSynthesisUtterance("{text}");
            msg.lang = 'ko-KR';
            msg.rate = 1.1;
            window.speechSynthesis.speak(msg);
        </script>
        """
        st.components.v1.html(js_code, height=0)

# 5. 영상 처리 클래스
class ObstacleDetector(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        height, width, _ = img.shape

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_obstacles = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (width * height * (min_confidence * 0.015)):
                x, y, w, h = cv2.boundingRect(cnt)
                
                bbox_area_ratio = (w * h) / (width * height) * 100
                
                center_x = x + w / 2
                if center_x < width / 3:
                    position = "좌측"
                elif center_x > (width * 2) / 3:
                    position = "우측"
                else:
                    position = "전방 중앙"

                is_danger = bbox_area_ratio >= danger_threshold

                color = (0, 0, 255) if is_danger else (0, 255, 0)
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                label = f"{position} ({int(bbox_area_ratio)}%)"
                cv2.putText(img, label, (x, max(y - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if is_danger:
                    detected_obstacles.append((position, bbox_area_ratio))

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
    st.subheader("📹 실시간 웹캠 화면 분석")
    rtc_config = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )
    
    webrtc_ctx = webrtc_streamer(
        key="obstacle-detection",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_config,
        video_processor_factory=ObstacleDetector,
        media_stream_constraints={"video": True, "audio": False},
    )

with col2:
    st.subheader("📢 알림 및 상태 안내")
    
    status_container = st.empty()
    
    if 'warning_msg' in st.session_state:
        msg = st.session_state['warning_msg']
        if "⚠️" in msg:
            html_content = f'<div class="warning-box">{msg}</div>'
            status_container.markdown(html_content, unsafe_allow_html=True)
            
            speech = st.session_state.get('speech_text', '')
            if speech:
                speak_text(speech)
        else:
            html_content = f'<div class="safe-box">{msg}</div>'
            status_container.markdown(html_content, unsafe_allow_html=True)
    else:
        status_container.info("카메라 [START] 버튼을 누르면 장애물 감지가 시작됩니다.")

    st.markdown("---")
    st.markdown("### 💡 사용 가이드")
    st.markdown("""
    1. **웹캠 실행**: 비디오 화면의 **[START]** 버튼을 클릭하고 브라우저의 카메라 권한을 허용해 주세요.
    2. **음성 출력**: 스마트폰이나 PC의 스피커 볼륨이 켜져 있는지 확인해 주세요.
    3. **민감도 조절**: 사물 인식 반응 속도나 감도를 조절하고 싶을 경우, 좌측 사이드바의 슬라이더를 조정하세요.
    """)
