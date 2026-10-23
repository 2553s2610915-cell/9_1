import os
import io
import time
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. 페이지 기본 설정 (고대비 및 테마)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Guide AI - 시각 장애인 안전 보행 보조",
    page_icon="🦯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 시각 장애인/저시력자를 위한 커스텀 고대비 CSS 스타일ing
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    .stButton>button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.3rem !important;
        font-weight: bold;
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
        border: 2px solid white;
    }
    .danger-box {
        padding: 20px;
        background-color: #8B0000;
        color: #FFFFFF;
        border-radius: 12px;
        border: 3px solid #FF0000;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .safe-box {
        padding: 20px;
        background-color: #006400;
        color: #FFFFFF;
        border-radius: 12px;
        border: 3px solid #00FF00;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .warning-box {
        padding: 20px;
        background-color: #B8860B;
        color: #FFFFFF;
        border-radius: 12px;
        border: 3px solid #FFD700;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. Gemini API 클라이언트 초기화 및 함수 정의
# ---------------------------------------------------------------------------
@st.cache_resource
def get_gemini_client():
    """Secrets 또는 환경변수에서 API 키를 가져옵니다."""
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def analyze_image_for_hazards(image: Image.Image, mode="hazard"):
    """
    Gemini 2.5 Flash Lite 모델을 활용해 장애물 감지 및 상황을 분석합니다.
    """
    client = get_gemini_client()
    if not client:
        return {
            "risk_level": "ERROR",
            "voice_message": "API 키가 설정되지 않았습니다. 관리자 설정을 확인해주세요.",
            "description": "GEMINI_API_KEY가 등록되지 않았습니다."
        }

    try:
        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        if mode == "hazard":
            prompt = """
            당신은 시각 장애인을 위한 실시간 안전 보행 가이드 AI입니다.
            제공된 카메라 이미지에서 앞에 있는 장애물, 위험 요소, 보행 경로 상황을 분석하세요.

            반드시 아래의 양식 규칙으로만 답변해 주세요:
            [위험도]: 고 / 중 / 저 / 안전 중 하나 선택
            [음성안내]: 시각 장애인에게 즉시 들려줄 한 문장의 짧고 명확한 경고/안내 메시지 (예: "전방 1m 앞에 계단이 있습니다. 정지하세요.", "오른쪽에 기둥이 있습니다. 왼쪽으로 진행하세요.")
            [상세상황]: 장애물 종류, 대략적 위치 및 주의사항 간략 설명

            위험도 판단 기준:
            - 고: 차량, 웅덩이, 낭떠러지, 빠른 속도의 이동체, 바로 앞 장애물
            - 중: 보행자, 간판, 자전거, 약간의 턱, 기둥
            - 저: 멀리 있는 장애물, 평탄한 인도
            - 안전: 장애물이 없고 보행이 자유로운 경우
            """
        else:  # OCR / 글자 읽기 모드
            prompt = """
            시각 장애인을 위해 이미지 내에 존재하는 모든 중요한 텍스트(표지판, 버스 번호, 간판, 메뉴판 등)를 읽어주세요.
            
            양식:
            [위험도]: 안전
            [음성안내]: 이미지에서 읽은 핵심 텍스트 내용 요약
            [상세상황]: 감지된 전체 텍스트
            """

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'),
                prompt
            ]
        )

        text = response.text
        
        # 간단 파싱
        risk_level = "저"
        voice_msg = "전방을 확인 중입니다."
        desc = text

        for line in text.split('\n'):
            if line.startswith('[위험도]:'):
                risk_level = line.replace('[위험도]:', '').strip()
            elif line.startswith('[음성안내]:'):
                voice_msg = line.replace('[음성안내]:', '').strip()
            elif line.startswith('[상세상황]:'):
                desc = line.replace('[상세상황]:', '').strip()

        return {
            "risk_level": risk_level,
            "voice_message": voice_msg,
            "description": text
        }

    except Exception as e:
        return {
            "risk_level": "ERROR",
            "voice_message": "화면 분석 중 오류가 발생했습니다.",
            "description": f"오류 원인: {str(e)}"
        }

def speak_text(text: str):
    """HTML5 SpeechSynthesis API를 이용하여 웹 브라우저에서 직접 음성(TTS)을 재생합니다."""
    # 큰따옴표/작은따옴표 탈
