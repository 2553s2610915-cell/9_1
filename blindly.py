import streamlit as st
from duckduckgo_search import DDGS
import json

# ---------------------------------------------------------
# 1. 페이지 설정 및 스포티파이 스타일 UI Custom CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="VoiceMelody - AI Music Curator",
    page_icon="🎵",
    layout="wide"
)

if "selected_theme" not in st.session_state:
    st.session_state["selected_theme"] = ""

st.markdown("""
    <style>
    .stApp {
        background-color: #121212 !important;
        color: #FFFFFF !important;
        font-family: 'Malgun Gothic', sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background-color: #000000 !important;
        padding-top: 1rem;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #FFFFFF !important;
    }
    
    .sidebar-title {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        margin-bottom: 4px;
    }
    
    .sidebar-subtitle {
        color: #E0E0E0 !important;
        font-size: 0.95rem !important;
        margin-bottom: 15px;
    }

    .spotify-card {
        background-color: #181818;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 14px;
        border: 1px solid #282828;
    }
    
    .song-title {
        color: #1DB954;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 4px;
    }
    .artist-name {
        color: #B3B3B3;
        font-size: 1.0rem;
        margin-bottom: 8px;
    }
    .reason-text {
        color: #E5E5E5;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    .stButton > button {
        background-color: #1DB954 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-size: 1.05rem !important;
        width: 100%;
        margin-bottom: 6px;
    }
    
    .stTextInput > div > div > input {
        background-color: #242424 !important;
        color: #FFFFFF !important;
        border: 1px solid #3E3E3E !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 사이드바 (빠른 키워드 버튼)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎵 VoiceMelody</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">시각 장애인 및 음성 사용자 전용 추천</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📚 빠른 키워드 선택")
    
    presets = [
        "🌧️ 비 오는 날 감성 발라드",
        "☕ 카페 느낌의 편안한 재즈",
        "🏃‍♂️ 드라이브용 신나는 K-POP",
        "🌙 수면 유도 조용한 뉴에이지",
        "🎸 90년대 따뜻한 록 밴드"
    ]
    
    for p in presets:
        if st.button(p, key="btn_" + p):
            st.session_state["selected_theme"] = p

# ---------------------------------------------------------
# 3. 메인 화면
# ---------------------------------------------------------
st.markdown("## 🎧 AI 음악 큐레이터")
st.write("원하는 느낌이나 가사를 자유롭게 적거나, 왼쪽 라이브러리에서 빠른 키워드를 선택해 보세요.")

st.markdown("<br>", unsafe_allow_html=True)

user_input = st.text_input(
    label="어떤 분위기의 노래를 찾으시나요?",
    value=st.session_state.get("selected_theme", ""),
    placeholder="예: 마음이 차분해지는 새벽 들을만한 노래 알려줘",
    key="custom_query"
)

final_query = user_input.strip()

st.markdown("<br>", unsafe_allow_html=True)

if final_query:
    st.info("선택된 테마: " + final_query)

btn_clicked = st.button("▶ 추천 음악 불러오기", type="primary")

# ---------------------------------------------------------
# 4. DuckDuckGo AI 봇 추천 로직 (API 키 없음)
# ---------------------------------------------------------
if btn_clicked:
    if not final_query:
        st.warning("분위기를 입력하거나 왼쪽 메뉴에서 키워드를 선택해 주세요.")
    else:
        with st.spinner("🎵 당신을 위한 음악 플레이리스트를 구성하는 중..."):
            prompt = """당신은 음악 큐레이터입니다.
요청 테마: """ + final_query + """

위 테마에 어울리는 대표 노래 3곡을 추천해 주세요.
반드시 아래와 같은 JSON 형식을 엄격히 준수하여 응답하세요. 다른 부연 설명이나 인사말, 마크다운 백틱은 출력하지 마세요.

{
    "summary": "추천 테마에 대한 친절한 한 줄 큐레이션 서두",
    "songs": [
        {
            "title": "곡 제목",
            "artist": "가수 이름",
            "genre": "장르",
            "reason": "추천하는 이유 및 음악적 감상 설명"
        }
    ]
}"""

            try:
                # API 키 없이 무료 지원되는 DDG AI 호출
                ddgs = DDGS()
                results = ddgs.chat(prompt, model='gpt-4o-mini')
                
                res_text = results.strip() if results else ""
                
                # 마크다운 구분자 제거
                if res_text.startswith("```"):
                    lines = res_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    res_text = "\n".join(lines).strip()

                data = json.loads(res_text)

                st.markdown("---")
                st.markdown("### 💬 Curator's Note\n> " + str(data.get("summary", "")))
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("🎧 Top Recommended Tracks")

                for idx, song in enumerate(data.get("songs", []), start=1):
                    title = str(song.get("title", "제목 없음"))
                    artist = str(song.get("artist", "가수 미상"))
                    genre = str(song.get("genre", "장르 미상"))
                    reason = str(song.get("reason", "추천 내용"))

                    clean_title = title.replace(' ', '+')
                    clean_artist = artist.replace(' ', '+')
                    youtube_link = "[https://www.youtube.com/results?search_query=](https://www.youtube.com/results?search_query=)" + clean_title + "+" + clean_artist

                    card_html = (
                        '<div class="spotify-card">'
                        '<div class="song-title">#' + str(idx) + '. ' + title + '</div>'
                        '<div class="artist-name">🎤 ' + artist + ' &nbsp;|&nbsp; 🏷️ ' + genre + '</div>'
                        '<div class="reason-text">💡 ' + reason + '</div>'
                        '<br>'
                        '<a href="' + youtube_link + '" target="_blank" style="color: #1DB954; font-weight: bold; text-decoration: none;">▶ YouTube에서 바로 재생하기</a>'
                        '</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

            except json.JSONDecodeError:
                st.warning("추천 음악 결과입니다:")
                st.write(results if 'results' in locals() else "결과를 불러올 수 없습니다.")
            except Exception as e:
                st.error("오류가 발생했습니다: " + str(e))

# ---------------------------------------------------------
# 5. 하단 안내
# ---------------------------------------------------------
st.markdown("<br><br>---", unsafe_allow_html=True)
st.caption("🔊 VoiceMelody는 스크린리더(NVDA, VoiceOver 등) 접근성에 최적화되어 있습니다.")
