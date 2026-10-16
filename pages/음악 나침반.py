import hashlib
import json
import os
import re
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

MODEL_NAME = "gemini-2.5-flash-lite"

st.set_page_config(page_title="음악 나침반", page_icon="🧭", layout="centered")

# ---------- 접근성 중심 스타일 (큰 글씨, 높은 대비) ----------
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 20px; }
    .stApp { background-color: #0b1020; color: #f5f5f5; }
    h1, h2, h3, h4, p, label, span, div { color: #f5f5f5; }
    .stButton > button, .stLinkButton > a {
        font-size: 1.2rem; font-weight: 700; padding: 0.9rem 1rem;
        border-radius: 14px; border: 3px solid #ffd54a;
    }
    .stButton > button[kind="primary"] { background: #ffd54a; color: #111; }
    textarea { font-size: 1.15rem !important; }
    *:focus { outline: 4px solid #ffd54a !important; outline-offset: 2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 세션 상태 초기화 ----------
defaults = {
    "user_text": "",
    "last_audio": "",
    "result": None,
    "history": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------- 유틸 함수 ----------
def get_api_key() -> str:
    try:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "").strip()


def get_client():
    key = get_api_key()
    if not key:
        raise RuntimeError("NO_KEY")
    from google import genai  # 지연 import

    return genai.Client(api_key=key)


def friendly_error(e: Exception) -> str:
    msg = str(e)
    if "NO_KEY" in msg:
        return ("GEMINI_API_KEY가 설정되지 않았습니다. "
                "Streamlit Cloud의 Secrets에 GEMINI_API_KEY를 등록해 주세요.")
    low = msg.lower()
    if "429" in msg or "quota" in low or "resource_exhausted" in low:
        return "요청이 너무 많거나 무료 사용량을 넘었습니다. 잠시 후 다시 시도해 주세요."
    if "api key" in low or "401" in msg or "403" in msg or "permission" in low:
        return "API 키가 올바르지 않거나 권한이 없습니다. Secrets의 키를 확인해 주세요."
    if "timeout" in low or "timed out" in low or "connect" in low:
        return "인터넷 연결이 불안정합니다. 잠시 후 다시 시도해 주세요."
    return f"오류가 발생했습니다. 잠시 후 다시 시도해 주세요. ({msg[:120]})"


def transcribe(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Gemini로 음성을 한국어 글자로 변환"""
    from google.genai import types

    client = get_client()
    prompt = (
        "다음 음성을 들리는 그대로 글자로 받아 적어 주세요. "
        "주로 한국어입니다. 설명이나 따옴표 없이 받아쓴 내용만 출력하세요. "
        "말소리가 없으면 빈 문자열만 출력하세요."
    )
    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
    )
    return (resp.text or "").strip()


def parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise ValueError("AI 응답을 해석하지 못했습니다.")


def recommend(user_text: str, count: int, region: str, exclude: list) -> dict:
    from google.genai import types

    client = get_client()
    exclude_text = ", ".join(exclude[-40:]) if exclude else "없음"
    prompt = f"""
당신은 시각 장애인을 위한 친절한 음악 안내자 '음악 나침반'입니다.
사용자가 말하거나 쓴 내용을 분석해 취향에 맞는 노래를 추천하세요.

[사용자 입력]
{user_text}

[조건]
- 추천 곡 수: {count}곡
- 지역: {region}
- 이미 추천한 곡(중복 금지): {exclude_text}
- 실제로 존재하는 노래만 추천하고, 확실하지 않은 곡은 넣지 마세요.
- 곡 제목과 가수 이름은 정확하게 쓰세요.
- 설명은 귀로 듣기 편하도록 짧고 쉬운 한국어 문장으로 쓰세요.
- 이모지, 특수기호, 마크다운은 쓰지 마세요.
- 입력에 노래 취향 단서가 거의 없으면 대중적이고 무난한 곡을 추천하세요.

[출력 형식: 아래 JSON만 출력]
{{
  "analysis": {{
    "summary": "취향을 한두 문장으로 요약",
    "mood": ["분위기 키워드"],
    "genre": ["장르 키워드"],
    "artists": ["언급되었거나 비슷한 가수"],
    "situation": "어울리는 상황이나 감정"
  }},
  "songs": [
    {{"title": "곡 제목", "artist": "가수", "reason": "추천 이유 한 문장"}}
  ]
}}
"""
    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )
    data = parse_json(resp.text)
    songs = data.get("songs")
    if not isinstance(songs, list) or not songs:
        raise ValueError("추천 결과가 비어 있습니다.")
    clean = []
    for s in songs:
        if isinstance(s, dict) and s.get("title") and s.get("artist"):
            clean.append({
                "title": str(s["title"]).strip(),
                "artist": str(s["artist"]).strip(),
                "reason": str(s.get("reason", "")).strip(),
            })
    if not clean:
        raise ValueError("추천 결과를 해석하지 못했습니다.")
    data["songs"] = clean
    if not isinstance(data.get("analysis"), dict):
        data["analysis"] = {}
    return data


def join_list(v) -> str:
    if isinstance(v, list):
        return ", ".join(str(x) for x in v if x)
    return str(v) if v else ""


def build_speech_lines(result: dict) -> list:
    a = result.get("analysis", {})
    lines = ["음악 나침반의 추천 결과입니다."]
    if a.get("summary"):
        lines.append("취향 분석. " + str(a["summary"]))
    if join_list(a.get("mood")):
        lines.append("분위기는 " + join_list(a["mood"]) + " 입니다.")
    if join_list(a.get("genre")):
        lines.append("장르는 " + join_list(a["genre"]) + " 입니다.")
    for i, s in enumerate(result["songs"], 1):
        lines.append(f"{i}번. {s['artist']}의 {s['title']}. {s['reason']}")
    lines.append("추천 안내를 마칩니다.")
    return lines


def speak_component(lines: list, rate: float):
    """브라우저 음성 합성으로 결과 읽어주기 (추가 라이브러리 불필요)"""
    safe = json.dumps(lines, ensure_ascii=False).replace("</", "<\\/")
    html = f"""
    <div style="display:flex; gap:12px; flex-wrap:wrap; font-family:sans-serif;">
      <button id="play" aria-label="추천 결과 소리로 듣기"
        style="font-size:22px; font-weight:700; padding:16px 22px; border-radius:14px;
               border:3px solid #ffd54a; background:#ffd54a; color:#111; cursor:pointer;">
        🔊 결과 소리로 듣기</button>
      <button id="stop" aria-label="읽기 멈추기"
        style="font-size:22px; font-weight:700; padding:16px 22px; border-radius:14px;
               border:3px solid #ffd54a; background:#0b1020; color:#ffd54a; cursor:pointer;">
        ⏹ 멈추기</button>
    </div>
    <script>
      const lines = {safe};
      const rate = {rate};
      const synth = window.speechSynthesis;
      document.getElementById('play').onclick = function() {{
        if (!synth) {{ alert('이 브라우저는 음성 읽기를 지원하지 않습니다.'); return; }}
        synth.cancel();
        lines.forEach(function(t) {{
          const u = new SpeechSynthesisUtterance(t);
          u.lang = 'ko-KR';
          u.rate = rate;
          synth.speak(u);
        }});
      }};
      document.getElementById('stop').onclick = function() {{
        if (synth) synth.cancel();
      }};
    </script>
    """
    components.html(html, height=110)


def clear_text():
    st.session_state.user_text = ""
    st.session_state.result = None
    st.session_state.history = []


def do_recommend(count: int, region: str, more: bool):
    text = st.session_state.user_text.strip()
    if not text:
        st.warning("먼저 말씀하시거나 글로 취향을 입력해 주세요.")
        return
    try:
        with st.spinner("취향을 분석하고 노래를 찾는 중입니다. 잠시만 기다려 주세요."):
            exclude = st.session_state.history if more else []
            result = recommend(text, count, region, exclude)
        st.session_state.result = result
        if not more:
            st.session_state.history = []
        st.session_state.history += [s["title"] for s in result["songs"]]
    except Exception as e:
        st.error(friendly_error(e))


# ---------- 화면 ----------
st.title("🧭 음악 나침반")
st.write("듣고 싶은 노래의 분위기, 장르, 가수를 말하거나 글로 알려 주세요. "
         "취향을 분석해서 어울리는 노래를 여러 곡 추천해 드립니다.")

if not get_api_key():
    st.warning("GEMINI_API_KEY가 설정되지 않았습니다. 배포 설정의 Secrets에 키를 등록해 주세요.")

# 1단계: 말하기
st.header("1단계. 말로 알려주기")
st.write("마이크 버튼을 눌러 말씀하시고, 끝나면 정지 버튼을 눌러 주세요. "
         "예: 비 오는 날 혼자 듣기 좋은 잔잔한 발라드, 아이유 같은 목소리.")

audio = None
if hasattr(st, "audio_input"):
    try:
        audio = st.audio_input("마이크로 말하기")
    except Exception:
        audio = None
else:
    st.info("이 환경에서는 음성 입력을 쓸 수 없습니다. 아래 입력창에 글로 적어 주세요.")

if audio is not None:
    try:
        data = audio.getvalue()
        h = hashlib.md5(data).hexdigest() if data else ""
        if data and h != st.session_state.last_audio:
            st.session_state.last_audio = h
            with st.spinner("말씀하신 내용을 글로 바꾸는 중입니다."):
                text = transcribe(data, "audio/wav")
            if text:
                old = st.session_state.user_text.strip()
                st.session_state.user_text = (old + " " + text).strip() if old else text
                st.success("음성을 글로 바꿨습니다. 아래 입력창에서 확인해 주세요.")
            else:
                st.warning("말소리를 알아듣지 못했습니다. 다시 말씀해 주세요.")
    except Exception as e:
        st.error(friendly_error(e))

# 2단계: 글로 확인/입력
st.header("2단계. 글로 확인하거나 직접 쓰기")
st.text_area(
    "원하는 분위기, 장르, 가수, 지금의 기분을 자유롭게 적어 주세요.",
    key="user_text",
    height=150,
    placeholder="예: 운전하면서 신나게 들을 수 있는 90년대 한국 댄스곡",
)

col1, col2 = st.columns(2)
with col1:
    count = st.slider("추천받을 곡 수", 3, 10, 5)
with col2:
    region = st.selectbox("노래 범위", ["국내외 섞어서", "한국 노래 위주", "해외 노래 위주"])

# 3단계: 추천
st.header("3단계. 추천받기")
if st.button("🧭 음악 추천받기", type="primary", use_container_width=True):
    do_recommend(count, region, more=False)

st.button("🗑 입력 지우기", on_click=clear_text, use_container_width=True)

# 결과
result = st.session_state.result
if result:
    st.header("추천 결과")
    a = result.get("analysis", {})

    st.subheader("내 취향 분석")
    if a.get("summary"):
        st.write(str(a["summary"]))
    if join_list(a.get("mood")):
        st.write("분위기: " + join_list(a["mood"]))
    if join_list(a.get("genre")):
        st.write("장르: " + join_list(a["genre"]))
    if join_list(a.get("artists")):
        st.write("관련 가수: " + join_list(a["artists"]))
    if a.get("situation"):
        st.write("어울리는 상황: " + str(a["situation"]))

    st.subheader("추천 노래")
    for i, s in enumerate(result["songs"], 1):
        st.markdown(f"#### {i}번. {s['title']} - {s['artist']}")
        if s["reason"]:
            st.write(s["reason"])
        q = quote(f"{s['artist']} {s['title']}")
        st.link_button(
            f"{i}번 곡 유튜브에서 찾아 듣기",
            f"https://www.youtube.com/results?search_query={q}",
        )

    st.header("4단계. 소리로 듣기")
    speed = st.select_slider("읽는 속도", options=["느리게", "보통", "빠르게"], value="보통")
    rate = {"느리게": 0.8, "보통": 1.0, "빠르게": 1.3}[speed]
    try:
        speak_component(build_speech_lines(result), rate)
    except Exception:
        st.info("소리 읽기 기능을 불러오지 못했습니다. 스크린 리더로 위 내용을 읽어 주세요.")

    if st.button("🔄 다른 곡 더 추천받기", use_container_width=True):
        do_recommend(count, region, more=True)
        st.rerun()

    st.caption("AI가 추천한 곡 정보는 가끔 틀릴 수 있습니다. 유튜브 링크로 확인해 주세요.")
