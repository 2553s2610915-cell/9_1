import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="오징어 게임 PK 오디오 축구",
    page_icon="⚽",
    layout="wide"
)

# HTML 파일 경로 설정
html_path = os.path.join(os.path.dirname(__file__), "game.html")

# game.html 파일 존재 여부 확인 후 출력
if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()
    components.html(html_code, height=620)
else:
    st.error("game.html 파일을 찾을 수 없습니다. app.py와 같은 폴더에 업로드해 주세요.")
