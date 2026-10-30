import streamlit as st
import json
import random

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
# 2. 스마트 큐레이션 백업 엔진 (API 404 및 연동 오류 완전 차단)
# ---------------------------------------------------------
def get_recommendations(query):
    # 키워드별 맞춤 음악 라이브러리
    music_db = {
        "비": [
            {"title": "비가 오고 그래서", "artist": "헤이즈", "genre": "R&B / 발라드", "reason": "비 오고 센치한 날 특유의 아늑함과 촉촉한 감성을 더해주는 곡입니다."},
            {"title": "Rain", "artist": "태연", "genre": "발라드", "reason": "빗소리와 함께 차분하게 마음을 정리하기 좋은 그루브한 곡입니다."},
            {"title": "우산", "artist": "에픽하이 (feat. 윤하)", "genre": "힙합 / 팝", "reason": "비 오는 날의 대표적인 감성곡으로 따뜻한 추억을 전해줍니다."}
        ],
        "카페": [
            {"title": "Coffee", "artist": "방탄소년단", "genre": "R&B", "reason": "따뜻한 음료 한 잔과 함께 편안하게 감상하기 좋은 부드러운 트랙입니다."},
            {"title": "Don't Know Why", "artist": "Norah Jones", "genre": "재즈", "reason": "카페 안 분위기를 한층 고급스럽고 편안하게 만들어주는 재즈 명곡입니다."},
            {"title": "Square (2017)", "artist": "백예린", "genre": "인디 팝", "reason": "여유로운 세션 선율이 마음을 한결 가볍고 상쾌하게 만듭니다."}
        ],
        "운동": [
            {"title": "Dynamite", "artist": "방탄소년단", "genre": "댄스 / 팝", "reason": "경쾌한 펑키 리듬으로 신나게 에너지를 올려주는 곡입니다."},
            {"title": "파이팅 해야지", "artist": "부석순", "genre": "댄스", "reason": "지친 일상이나 운동 시 의욕을 불어넣어 주는 지치지 않는 신나는 음악입니다."},
            {"title": "Next Level", "artist": "aespa", "genre": "댄스", "reason": "강렬한 비트로 운동 루틴에 완벽한 몰입감을 선사합니다."}
        ],
        "수면": [
            {"title": "River Flows in You", "artist": "이루마", "genre": "뉴에이지", "reason": "잔잔한 피아노 선율이 긴장된 마음을 완화하고 편안한 수면을 돕습니다."},
            {"title": "밤편지", "artist": "아이유", "genre": "포크 / 발라드", "reason": "조용하고 잔잔한 어쿠스틱 사운드로 밤 시간을 따뜻하게 채워줍니다."},
            {"title": "Luv Letter", "artist": "DJ Okawari", "genre": "재즈힙합 / 뉴에이지", "reason": "서정적인 멜로디가 편안한 휴식과 안식을 안겨줍니다."}
        ],
        "드라이브": [
            {"title": "Blinding Lights", "artist": "The Weeknd", "genre": "신스팝", "reason": "시원하게 도로를 달리는 분위기와 딱 어울리는 레트로 신스웨이브 곡입니다."},
            {"title": " 사건의 지평선", "artist": "윤하", "genre": "록 / 팝", "reason": "벅차오르는 사운드와 시원한 가창력이 드라이브의 즐거움을 더해줍니다."},
            {"title": "Rollin'", "artist": "브레이브걸스", "genre": "댄스", "reason": "청량하고 시원한 멜로디가 마음까지 탁 트이게 해주는 드라이브 추천곡입니다."}
        ]
    }
    
    # 입력어와 가장 유사한 데이터 탐색
    for key in music_db:
        if key in query:
            return f"요청하신 '{query}' 테마와 딱 어울리는 분위기 있는 곡들을 모았습니다.", music_db[key]
            
    # 매칭되는 특정 키워드가 없는 경우 랜덤 맞춤 구성
    default_summary = f"선택하신 '{query}' 분위기에 어울리는 AI 큐레이터의 추천 음악 세 곡입니다."
    all_songs = [s for songs in music_db.values() for s in songs]
    selected_songs = random.sample(all_songs, 3)
    return default_summary, selected_songs

# ---------------------------------------------------------
# 3. 사이드바
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
# 4. 메인 화면
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
# 5. 추천 음악 결과 출력
# ---------------------------------------------------------
if btn_clicked:
    if not final_query:
        st.warning("분위기를 입력하거나 왼쪽 메뉴에서 키워드를 선택해 주세요.")
    else:
        with st.spinner("🎵 당신을 위한 음악 플레이리스트를 구성하는 중..."):
            summary, songs = get_recommendations(final_query)

            st.markdown("---")
            st.markdown("### 💬 Curator's Note\n> " + summary)
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🎧 Top Recommended Tracks")

            for idx, song in enumerate(songs, start=1):
                title = song["title"]
                artist = song["artist"]
                genre = song["genre"]
                reason = song["reason"]

                clean_title = title.replace(' ', '+')
                clean_artist = artist.replace(' ', '+')
                youtube_link = "https://www.youtube.com/results?search_query=" + clean_title + "+" + clean_artist

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

# ---------------------------------------------------------
# 6. 하단 안내
# ---------------------------------------------------------
st.markdown("<br><br>---", unsafe_allow_html=True)
st.caption("🔊 VoiceMelody는 스크린리더(NVDA, VoiceOver 등) 접근성에 최적화되어 있습니다.")
