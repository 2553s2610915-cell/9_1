import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import base64

# 1. 페이지 기본 설정 및 스타일 (시각장애인을 위한 큰 글씨 및 대비)
st.set_page_config(page_title="보이스 아이 (Voice Eye)", layout="centered")
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .warning-font { font-size:20px !important; color: red; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="big-font">👁️ 보이스 아이 (Voice Eye)</p>', unsafe_allow_html=True)
st.write("앞에 있는 상황을 촬영하거나 사진을 업로드하시면 위험 요소를 분석하여 음성으로 알려드립니다.")

# 2. API 키 설정 및 예외 처리
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
else:
    st.error("Secrets 설정에서 GEMINI_API_KEY를 입력해주세요.")
    st.stop()

# 3. 이미지 입력 (카메라 촬영 및 파일 업로드 통합)
img_file = st.camera_input("정면을 향해 사진을 촬영하세요")

# 카메라를 지원하지 않는 환경을 위한 파일 업로드 백업
if not img_file:
    img_file = st.file_uploader("또는 사진 파일을 선택하세요", type=["jpg", "jpeg", "png"])

# 4. 이미지 분석 및 TTS 변환 프로세스
if img_file is not None:
    try:
        # 이미지 데이터 읽기
        image_bytes = img_file.read()
        
        st.info("🔄 전방 상황을 분석하고 있습니다. 잠시만 기다려주세요...")
        
        # Gemini 2.5 Flash-lite 모델 설정
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # 시각장애인 맞춤형 충돌 경고 프롬프트
        prompt = (
            "당신은 앞을 볼 수 없는 시각장애인의 보행을 돕는 AI 조수입니다. "
            "보내진 사진을 보고, 사용자의 바로 앞에 충돌 위험이 있는 장애물(예: 턱, 계단, 사람, 전동킥보드, 차량 등)이 있는지 확인하세요. "
            "지나치게 상세한 설명은 배제하고, '조심하세요, 전방에 XX가 있습니다' 또는 '안전합니다'와 같이 "
            "시각장애인이 즉각 상황을 인지할 수 있도록 짧고 단호한 경고 문장(한국어 2~3문장 이내)으로만 답변하세요."
        )
        
        # 이미지 분석 요청
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        
        analysis_text = response.text
        
        # 결과 화면 표시
        st.markdown('<p class="warning-font">🚨 안내 메시지</p>', unsafe_allow_html=True)
        st.success(analysis_text)
        
        # 5. gTTS를 활용한 음성 변환 (한국어)
        tts = gTTS(text=analysis_text, lang='ko')
        sound_file = io.BytesIO()
        tts.write_to_fp(sound_file)
        sound_file.seek(0)
        
        # 6. 자동 재생을 위한 HTML 오디오 코드 삽입 (UX 차별화)
        b64 = base64.b64encode(sound_file.read()).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
        st.audio(sound_file, format="audio/mp3")
        st.caption("🔊 음성이 자동으로 재생되지 않으면 위 플레이어의 재생 버튼을 누르세요.")
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}\n잠시 후 다시 시도해주세요.")


