
import streamlit as st
from urllib.parse import quote_plus
import random
import re

st.set_page_config(
    page_title="마음의 플레이리스트",
    page_icon="🎧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

SONGS = [
    {
        "title": "밤편지",
        "artist": "아이유",
        "genre": "발라드",
        "moods": ["위로", "잔잔함", "그리움"],
        "tags": ["밤", "편안한", "조용한", "외로움", "감성", "비", "위로", "혼자"],
        "reason": "조용한 밤과 그리운 마음에 어울리는 섬세한 발라드예요.",
    },
    {
        "title": "Love wins all",
        "artist": "아이유",
        "genre": "발라드",
        "moods": ["위로", "감동", "그리움"],
        "tags": ["사랑", "감동", "위로", "희망", "그리움", "감성"],
        "reason": "소중한 사람과 희망을 떠올리고 싶을 때 추천해요.",
    },
    {
        "title": "벚꽃 엔딩",
        "artist": "버스커 버스커",
        "genre": "인디",
        "moods": ["설렘", "행복", "산뜻함"],
        "tags": ["봄", "산책", "벚꽃", "설렘", "데이트", "밝은", "여행"],
        "reason": "봄날 산책이나 설레는 기분에 잘 어울려요.",
    },
    {
        "title": "여행",
        "artist": "볼빨간사춘기",
        "genre": "인디",
        "moods": ["행복", "설렘", "활기"],
        "tags": ["여행", "드라이브", "휴가", "신나는", "밝은", "자유"],
        "reason": "일상에서 벗어나 기분 전환하고 싶을 때 좋아요.",
    },
    {
        "title": "Dynamite",
        "artist": "방탄소년단",
        "genre": "팝",
        "moods": ["행복", "활기", "신남"],
        "tags": ["춤", "파티", "운동", "신나는", "밝은", "에너지", "팝"],
        "reason": "몸을 움직이고 싶거나 에너지가 필요할 때 추천해요.",
    },
    {
        "title": "봄날",
        "artist": "방탄소년단",
        "genre": "발라드",
        "moods": ["그리움", "위로", "희망"],
        "tags": ["친구", "이별", "그리움", "위로", "추억", "겨울", "감성"],
        "reason": "보고 싶은 사람을 생각하거나 마음을 다독이고 싶을 때 어울려요.",
    },
    {
        "title": "사건의 지평선",
        "artist": "윤하",
        "genre": "록",
        "moods": ["희망", "감동", "활기"],
        "tags": ["새출발", "도전", "미래", "희망", "여행", "힘내", "록"],
        "reason": "새로운 시작이나 앞으로 나아갈 용기가 필요할 때 추천해요.",
    },
    {
        "title": "걱정말아요 그대",
        "artist": "이적",
        "genre": "발라드",
        "moods": ["위로", "희망", "잔잔함"],
        "tags": ["위로", "힘들어", "지침", "응원", "휴식", "마음", "희망"],
        "reason": "지친 하루를 마무리하며 마음을 쉬게 하고 싶을 때 좋아요.",
    },
    {
        "title": "너의 의미",
        "artist": "아이유, 김창완",
        "genre": "인디",
        "moods": ["설렘", "행복", "잔잔함"],
        "tags": ["사랑", "산책", "따뜻한", "카페", "햇살", "설렘"],
        "reason": "따뜻하고 포근한 분위기를 느끼고 싶을 때 추천해요.",
    },
    {
        "title": "좋은 날",
        "artist": "아이유",
        "genre": "팝",
        "moods": ["설렘", "행복", "신남"],
        "tags": ["사랑", "고백", "설렘", "밝은", "신나는", "데이트"],
        "reason": "두근거리는 마음이나 기분 좋은 에너지를 원할 때 어울려요.",
    },
    {
        "title": "Hype Boy",
        "artist": "NewJeans",
        "genre": "팝",
        "moods": ["설렘", "신남", "활기"],
        "tags": ["댄스", "춤", "친구", "설렘", "드라이브", "신나는"],
        "reason": "리듬감 있는 음악으로 분위기를 바꾸고 싶을 때 추천해요.",
    },
    {
        "title": "Ditto",
        "artist": "NewJeans",
        "genre": "팝",
        "moods": ["그리움", "잔잔함", "설렘"],
        "tags": ["추억", "겨울", "그리움", "감성", "밤", "혼자"],
        "reason": "추억을 떠올리거나 차분한 감성에 잠기고 싶을 때 좋아요.",
    },
    {
        "title": "한 페이지가 될 수 있게",
        "artist": "DAY6",
        "genre": "록",
        "moods": ["희망", "행복", "활기"],
        "tags": ["청춘", "친구", "학교", "여행", "응원", "새출발", "밴드"],
        "reason": "소중한 순간을 즐기거나 힘차게 시작하고 싶을 때 추천해요.",
    },
    {
        "title": "예뻤어",
        "artist": "DAY6",
        "genre": "록",
        "moods": ["그리움", "슬픔", "감동"],
        "tags": ["이별", "추억", "사랑", "그리움", "감성", "혼자"],
        "reason": "지난 사랑이나 아름다웠던 추억을 떠올릴 때 어울려요.",
    },
    {
        "title": "밤양갱",
        "artist": "비비",
        "genre": "인디",
        "moods": ["잔잔함", "그리움", "편안함"],
        "tags": ["밤", "달콤한", "카페", "독특한", "감성", "편안한"],
        "reason": "개성 있고 부드러운 분위기의 곡을 듣고 싶을 때 추천해요.",
    },
    {
        "title": "비밀번호 486",
        "artist": "윤하",
        "genre": "록",
        "moods": ["설렘", "신남", "행복"],
        "tags": ["사랑", "고백", "밝은", "추억", "신나는", "청춘"],
        "reason": "경쾌한 밴드 사운드와 풋풋한 설렘을 느끼고 싶을 때 좋아요.",
    },
    {
        "title": "사랑은 늘 도망가",
        "artist": "임영웅",
        "genre": "트로트",
        "moods": ["그리움", "슬픔", "위로"],
        "tags": ["사랑", "이별", "그리움", "감성", "위로", "추억"],
        "reason": "애절한 감성과 깊은 여운을 느끼고 싶을 때 추천해요.",
    },
    {
        "title": "보라빛 엽서",
        "artist": "임영웅",
        "genre": "트로트",
        "moods": ["그리움", "잔잔함", "감동"],
        "tags": ["추억", "그리움", "옛날", "감성", "편안한"],
        "reason": "차분한 분위기에서 추억과 감성을 느끼고 싶을 때 어울려요.",
    },
    {
        "title": "아로하",
        "artist": "조정석",
        "genre": "발라드",
        "moods": ["행복", "설렘", "편안함"],
        "tags": ["사랑", "결혼", "데이트", "따뜻한", "행복", "고백"],
        "reason": "사랑하는 사람을 떠올리며 따뜻한 기분을 느끼고 싶을 때 좋아요.",
    },
    {
        "title": "Blueming",
        "artist": "아이유",
        "genre": "팝",
        "moods": ["설렘", "행복", "활기"],
        "tags": ["사랑", "문자", "고백", "밝은", "설렘", "데이트"],
        "reason": "통통 튀는 리듬과 설레는 기분을 원할 때 추천해요.",
    },
    {
        "title": "Fix You",
        "artist": "Coldplay",
        "genre": "록",
        "moods": ["위로", "슬픔", "희망"],
        "tags": ["위로", "힘들어", "지침", "치유", "희망", "감동"],
        "reason": "힘든 순간을 지나 다시 일어설 힘을 얻고 싶을 때 어울려요.",
    },
    {
        "title": "Perfect",
        "artist": "Ed Sheeran",
        "genre": "팝",
        "moods": ["사랑", "설렘", "잔잔함"],
        "tags": ["사랑", "결혼", "데이트", "로맨틱", "따뜻한"],
        "reason": "로맨틱하고 부드러운 분위기를 만들고 싶을 때 추천해요.",
    },
    {
        "title": "River Flows in You",
        "artist": "Yiruma",
        "genre": "연주곡",
        "moods": ["잔잔함", "편안함", "위로"],
        "tags": ["피아노", "연주", "집중", "공부", "휴식", "수면", "비", "조용한"],
        "reason": "가사가 없는 피아노 선율로 조용히 쉬고 싶을 때 좋아요.",
    },
    {
        "title": "캐논 변주곡",
        "artist": "George Winston",
        "genre": "연주곡",
        "moods": ["잔잔함", "집중", "편안함"],
        "tags": ["피아노", "연주", "집중", "공부", "독서", "휴식", "조용한"],
        "reason": "차분하게 집중하거나 편안한 배경 음악이 필요할 때 추천해요.",
    },
    {
        "title": "벚꽃이 피면",
        "artist": "봄 분위기 음악",
        "genre": "연주곡",
        "moods": ["행복", "잔잔함", "편안함"],
        "tags": ["봄", "산책", "자연", "꽃", "피아노", "휴식"],
        "reason": "봄과 자연을 떠올리는 차분한 연주곡 분위기를 원할 때 어울려요.",
    },
]


def normalize(text):
    """한글 및 일반 검색어를 비교하기 쉽게 정리합니다."""
    text = text.lower().strip()
    return re.sub(r"\s+", " ", text)


def recommend_songs(query, mood, genre, count=5):
    query = normalize(query)
    scored = []

    # 검색어를 단어 단위로 나눕니다.
    words = [
        word for word in re.split(r"[\s,，.!?、]+", query)
        if len(word) >= 2
    ]

    for song in SONGS:
        if genre != "전체" and song["genre"] != genre:
            continue

        score = 0
        reasons = []

        if mood != "상관없음" and mood in song["moods"]:
            score += 3
            reasons.append(f"{mood} 분위기")

        searchable = normalize(
            " ".join([
                song["title"],
                song["artist"],
                song["genre"],
                " ".join(song["moods"]),
                " ".join(song["tags"]),
                song["reason"],
            ])
        )

        matched_words = []
        for word in words:
            if word in searchable:
                score += 2
                matched_words.append(word)

        if matched_words:
            reasons.append(
                "입력한 키워드와 일치: " + ", ".join(matched_words[:3])
            )

        # 검색어가 없으면 기분과 장르만으로 추천합니다.
        if not query and score == 0:
            score = 1

        if score > 0:
            scored.append((score, song, reasons))

    # 점수가 같으면 매번 같은 순서로 표시해 사용하기 쉽게 합니다.
    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    return scored[:count]


def spotify_search_url(title, artist):
    query = quote_plus(f"{title} {artist}")
    return f"https://open.spotify.com/search/{query}"


st.title("마음의 플레이리스트")
st.caption("듣고 싶은 마음을 말해 주세요. 어울리는 노래를 찾아드릴게요.")

st.markdown(
    "이 앱은 시각 정보 없이도 사용할 수 있도록 "
    "텍스트 중심으로 구성했습니다. 아래에 원하는 노래의 "
    "느낌이나 상황을 자유롭게 적어 주세요."
)

with st.form("recommendation_form"):
    st.subheader("어떤 노래를 듣고 싶나요?")

    query = st.text_area(
        "노래 키워드 또는 원하는 느낌",
        placeholder=(
            "예: 비 오는 날 혼자 걸을 때 듣기 좋은 잔잔한 노래\n"
            "예: 기분이 우울할 때 위로가 되는 음악\n"
            "예: 운동할 때 신나는 노래"
        ),
        height=120,
        help="장르, 날씨, 기분, 상황, 악기 등 무엇이든 입력할 수 있어요.",
    )

    mood = st.selectbox(
        "지금 원하는 분위기",
        [
            "상관없음",
            "위로",
            "잔잔함",
            "편안함",
            "행복",
            "설렘",
            "신남",
            "활기",
            "그리움",
            "슬픔",
            "희망",
            "감동",
            "집중",
        ],
    )

    genre = st.selectbox(
        "선호하는 음악 장르",
        ["전체", "발라드", "팝", "인디", "록", "트로트", "연주곡"],
    )

    count = st.radio(
        "추천받을 곡 수",
        [3, 5, 10],
        index=1,
        horizontal=True,
    )

    submitted = st.form_submit_button(
        "노래 추천받기",
        type="primary",
        use_container_width=True,
    )

if submitted:
    try:
        results = recommend_songs(query, mood, genre, count)

        st.session_state["recommendations"] = results
        st.session_state["last_query"] = query
        st.session_state["last_mood"] = mood
        st.session_state["last_genre"] = genre

    except Exception:
        st.error(
            "노래를 추천하는 중 문제가 발생했습니다. "
            "입력 내용을 바꾸어 다시 시도해 주세요."
        )
        st.session_state.pop("recommendations", None)

if "recommendations" in st.session_state:
    results = st.session_state["recommendations"]

    st.divider()
    st.header("추천 결과")

    if not results:
        st.info(
            "조건에 맞는 노래를 찾지 못했어요. "
            "장르를 '전체'로 바꾸거나 다른 키워드를 입력해 보세요."
        )
    else:
        st.write(f"총 {len(results)}곡을 추천합니다.")

        for index, (score, song, reasons) in enumerate(results, start=1):
            with st.container(border=True):
                st.subheader(f"{index}위. {song['title']}")
                st.write(f"가수: {song['artist']}")
                st.write(f"장르: {song['genre']}")
                st.write(f"분위기: {', '.join(song['moods'])}")
                st.write(f"추천 이유: {song['reason']}")

                if reasons:
                    st.write("검색 일치 정보: " + "; ".join(reasons))

                st.link_button(
                    "Spotify에서 이 노래 검색하기",
                    spotify_search_url(song["title"], song["artist"]),
                    use_container_width=True,
                )

        st.caption(
            "안내: 추천은 앱에 내장된 곡 정보와 키워드를 바탕으로 합니다. "
            "실시간 음원 재생이나 외부 서비스의 검색 결과를 보장하지 않습니다."
        )

st.divider()
st.caption(
    "마음의 플레이리스트 | 시각 장애인을 위한 접근성 중심 노래 추천"
)
