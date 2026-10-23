import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="시각장애인 음성 보행 도우미", page_icon="🦯")

# 커스텀 고대비 UI 스타일ing
st.markdown("""
<style>
    .title { font-size: 2.2rem; font-weight: bold; color: #FFFF00; background: #000; padding: 15px; text-align: center; border-radius: 8px; }
    .btn-big button { font-size: 1.5rem !important; height: 3em !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

def play_speech(text):
    clean = text.replace("'", "").replace('"', '').replace('\n', ' ')
    js = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance('{clean}');
            msg.lang = 'ko-KR';
            msg.rate = 1.0;
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    st.components.v1.html(js, height=0)

st.markdown("<div class='title'>🦯 시각장애인 보행 위험 음성 안내 시스템</div>", unsafe_allow_html=True)

# API 키 확인
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
else:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

# 입력 방식 선택 (카메라 외의 다양한 대안 제공)
mode = st.radio(
    "👉 분석 방식을 선택하세요:",
    ["1. 상황 음성/텍스트 질문", "2. 파일 업로드 분석", "3. 보행 위험 샘플 테스트"],
    horizontal=False
)

st.divider()

selected_image = None
text_prompt_input = ""

if mode == "1. 상황 음성/텍스트 질문":
    st.info("💡 마이크 음성 입력 기능 또는 현재 상황/위치를 입력하면 보행 안전 수칙을 음성으로 알려줍니다.")
    text_prompt_input = st.text_input("질문 또는 현재 상황을 입력하세요 (예: 전방에 점자블록이 끊기고 공사 소리가 납니다)", "전방에 공사 표지판과 볼라드가 보입니다. 어떻게 이동해야 하나요?")

elif mode == "2. 파일 업로드 분석":
    uploaded = st.file_uploader("전방 촬영 이미지를 업로드하세요", type=["jpg", "png", "jpeg"])
    if uploaded:
        selected_image = Image.open(uploaded)
        st.image(selected_image, caption="업로드된 이미지", use_container_width=True)

elif mode == "3. 보행 위험 샘플 테스트":
    st.info("💡 보행 중 자주 만나는 위험 요소 샘플을 선택하세요.")
    sample = st.selectbox("보행 위험 상황 선택:", [
        "전방 2미터 앞 자전거 방치",
        "보도블록 파손 및 계단 단차",
        "인도 위 전동 킥보드 장애물",
        "신호등 없는 횡단보도 전방"
    ])
    text_prompt_input = f"시각장애인 보행
