import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import streamlit as st
import streamlit.components.v1 as components

MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"]

st.set_page_config(page_title="음악 나침반", page_icon="🧭", layout="centered")

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

defaults = {
    "user_text": "",
    "last_audio": "",
    "result": None,
    "history": [],
    "pending": "",
    "error": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------- Gemini ----------
def get_api_key() -> str:
    try:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "").strip()


def get_client():
    key = get_api_key()
    if not key:
        raise RuntimeError("NO_KEY")
    from google import genai

    return genai.Client(api_key=key)


def generate(contents, config=None):
    client = get_client()
    last = None
    for model in MODELS:
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            s = str(e)
            if "404" in s or "NOT_FOUND" in s or "no longer available" in s:
                last = e
                continue
            raise
    raise last if last else RuntimeError("모델을 찾지 못했습니다.")


def friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "NO_KEY" in msg:
        return ("GEMINI_API_KEY가 설정되지 않았습니다. "
                "Streamlit Cloud의 Secrets에 GEMINI_API_KEY를 등록해 주세요.")
    if "404" in msg or "NOT_FOUND" in msg:
        return "사용할 수 있는 AI 모델을 찾지 못했습니다. app.py 위쪽 MODELS 목록의 모델 이름을 확인해 주세요."
    if "429" in msg or "quota" in low or "resource_exhausted" in low:
        return "요청이 너무 많거나 무료 사용량을 넘었습니다. 잠시 후 다시 시도해 주세요."
    if "api key" in low or "401" in msg or "403" in msg or "permission" in low:
        return "API 키가 올바르지 않거나 권한이 없습니다. Secrets의 키를 확인해 주세요."
    if "timeout" in low or "timed out" in low or "connect" in low:
        return "인터넷 연결이 불안정합니다. 잠시 후 다시 시도해 주세요."
    return f"오류가 발생했습니다. 잠시 후 다시 시도해 주세요. ({msg[:120]})"


def transcribe(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    from google.genai import types

    prompt = (
        "다음 음성을 들리는 그대로 글자로 받아 적어 주세요. "
        "주로 한국어입니다. 설명이나 따옴표 없이 받아쓴 내용만 출력하세요. "
        "말소리가 없으면 빈 문자열만 출력하세요."
    )
    resp = generate([prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)])
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


def ask_model(user_text: str, ask_count: int, region: str, exclude: list) -> dict:
    """AI에게 '후보' 곡을 받는다. (이후 음원 스토어에서 실제 존재 여부를 확인함)"""
    from google.genai import types

    exclude_text = ", ".join(exclude[-50:]) if exclude else "없음"
    prompt = f"""
당신은 시각 장애인을 위한 친절한 음악 안내자 '음악 나침반'입니다.
사용자가 말하거나 쓴 내용을 분석해 취향에 맞는 노래 후보를 추천하세요.

[사용자 입력]
{user_text}

[조건]
- 후보 곡 수: {ask_count}곡
- 지역: {region}
- 이미 나온 곡(중복 금지): {exclude_text}
- 멜론, 지니, 애플뮤직 같은 음원 사이트에 실제로 발매되어 등록된 곡만 고르세요.
- 반드시 잘 알려진 곡만 고르세요. 제목이나 가수가 조금이라도 불확실하면 넣지 마세요.
- 곡을 지어내지 마세요. 가수와 곡 제목의 조합이 실제와 정확히 일치해야 합니다.
- title과 artist는 음원 사이트에 표기된 공식 이름 그대로 쓰세요.
- artist_alt에는 같은 가수의 다른 언어 표기(한글이면 영문, 영문이면 한글)를, title_alt에는 곡 제목의 다른 언어 표기를 쓰세요. 없으면 빈 문자열.
- 설명은 귀로 듣기 편하도록 짧고 쉬운 한국어 문장으로 쓰세요. 이모지, 특수기호, 마크다운은 쓰지 마세요.

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
    {{"title": "곡 제목", "title_alt": "", "artist": "가수", "artist_alt": "", "reason": "추천 이유 한 문장"}}
  ]
}}
"""
    resp = generate(
        prompt,
        types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6),
    )
    data = parse_json(resp.text)
    songs = data.get("songs")
    if not isinstance(songs, list):
        songs = []
    clean = []
    for s in songs:
        if isinstance(s, dict) and s.get("title") and s.get("artist"):
            clean.append({
                "title": str(s["title"]).strip(),
                "title_alt": str(s.get("title_alt", "") or "").strip(),
                "artist": str(s["artist"]).strip(),
                "artist_alt": str(s.get("artist_alt", "") or "").strip(),
                "reason": str(s.get("reason", "")).strip(),
            })
    analysis = data.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}
    return {"analysis": analysis, "songs": clean}


# ---------- 음원 스토어(Apple Music / iTunes) 실존 확인 ----------
def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    return re.sub(r"[^0-9a-z가-힣]", "", s)


def similar(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 2 and short in long_ and len(short) / len(long_) >= 0.6:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def artist_ok(cand_names: list, store_artist: str) -> bool:
    store_n = norm(store_artist)
    for n in cand_names:
        if not n:
            continue
        if similar(n, store_artist):
            return True
        nn = norm(n)
        # 'A feat. B' 처럼 여러 가수가 적힌 경우
        if len(nn) >= 2 and nn in store_n:
            return True
    return False


@st.cache_data(ttl=3600, show_spinner=False)
def itunes_search(term: str, country: str) -> list:
    params = urlencode({
        "term": term, "media": "music", "entity": "song",
        "country": country, "limit": 10,
    })
    req = Request("https://itunes.apple.com/search?" + params,
                  headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    res = data.get("results", [])
    return res if isinstance(res, list) else []


def verify_song(c: dict):
    """반환: ("ok", song) / ("nomatch", None) / ("error", None)"""
    term = f"{c['artist']} {c['title']}"
    titles = [c["title"], c.get("title_alt", "")]
    artists = [c["artist"], c.get("artist_alt", "")]
    had_error = False
    had_success = False
    for country in ("KR", "US"):
        try:
            results = itunes_search(term, country)
            had_success = True
        except Exception:
            had_error = True
            continue
        for r in results:
            if r.get("kind") not in (None, "song"):
                continue
            name = r.get("trackName", "")
            art = r.get("artistName", "")
            if any(t and similar(t, name) for t in titles) and artist_ok(artists, art):
                return "ok", {
                    "id": r.get("trackId"),
                    "title": name,
                    "artist": art,
                    "album": r.get("collectionName", ""),
                    "preview": r.get("previewUrl", ""),
                    "link": r.get("trackViewUrl", ""),
                    "reason": c.get("reason", ""),
                }
    if had_error and not had_success:
        return "error", None
    return "nomatch", None


def safe_verify(c: dict):
    try:
        return verify_song(c)
    except Exception:
        return "error", None


def recommend(user_text: str, count: int, region: str, exclude: list) -> dict:
    analysis = None
    verified = []
    seen_ids = set()
    seen_titles = set(norm(x) for x in exclude)
    tried = list(exclude)
    checked = 0
    errors = 0

    for _ in range(2):  # 모자라면 한 번 더 요청
        need = count - len(verified)
        if need <= 0:
            break
        data = ask_model(user_text, min(need + 4, 14), region, tried)
        if analysis is None:
            analysis = data["analysis"]
        cands = data["songs"]
        if not cands:
            continue
        for c in cands:
            tried.append(c["title"])
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(safe_verify, cands))
        for status, song in results:
            checked += 1
            if status == "error":
                errors += 1
            if status != "ok":
                continue
            key = song["id"] or norm(song["title"] + song["artist"])
            tnorm = norm(song["title"])
            if key in seen_ids or tnorm in seen_titles:
                continue
            seen_ids.add(key)
            seen_titles.add(tnorm)
            verified.append(song)

    if not verified:
        if checked and errors == checked:
            raise RuntimeError("음원 사이트 확인에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        raise ValueError("음원 사이트에서 확인된 곡을 찾지 못했습니다. 조금 다르게 설명해서 다시 시도해 주세요.")

    return {"analysis": analysis or {}, "songs": verified[:count]}


# ---------- 표시용 ----------
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


def set_pending(kind: str):
    st.session_state.pending = kind


def clear_all():
    st.session_state.user_text = ""
    st.session_state.result = None
    st.session_state.history = []
    st.session_state.error = ""


# ---------- 화면 ----------
st.title("🧭 음악 나침반")
st.write("듣고 싶은 노래의 분위기, 장르, 가수를 말하거나 글로 알려 주세요. "
         "취향을 분석해서, 음원 사이트에 실제로 있는 노래만 추천해 드립니다.")

if not get_api_key():
    st.warning("GEMINI_API_KEY가 설정되지 않았습니다. 배포 설정의 Secrets에 키를 등록해 주세요.")

mode = st.radio(
    "어떻게 알려 주시겠어요?",
    ["🎤 말로 하기", "⌨️ 글로 쓰기"],
    horizontal=True,
)

if mode == "🎤 말로 하기":
    st.write("마이크 버튼을 눌러 말씀하시고, 끝나면 정지 버튼을 눌러 주세요. "
             "예: 비 오는 날 혼자 듣기 좋은 잔잔한 발라드, 아이유 같은 목소리.")
    audio = None
    if hasattr(st, "audio_input"):
        try:
            audio = st.audio_input("마이크로 말하기")
        except Exception:
            audio = None
    else:
        st.info("이 환경에서는 음성 입력을 쓸 수 없습니다. '글로 쓰기'를 선택해 주세요.")

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
                    st.success("말씀하신 내용을 글로 바꿨습니다. 아래에서 확인해 주세요.")
                else:
                    st.warning("말소리를 알아듣지 못했습니다. 다시 말씀해 주세요.")
        except Exception as e:
            st.error(friendly_error(e))
    label = "말씀하신 내용 (틀린 부분은 고칠 수 있습니다)"
else:
    label = "원하는 분위기, 장르, 가수, 지금의 기분을 자유롭게 적어 주세요."

st.text_area(
    label,
    key="user_text",
    height=150,
    placeholder="예: 운전하면서 신나게 들을 수 있는 90년대 한국 댄스곡",
)

col1, col2 = st.columns(2)
with col1:
    count = st.slider("추천받을 곡 수", 3, 10, 5)
with col2:
    region = st.selectbox("노래 범위", ["국내외 섞어서", "한국 노래 위주", "해외 노래 위주"])

st.button("🧭 추천받기", type="primary", use_container_width=True,
          on_click=set_pending, args=("new",))
st.button("🗑 모두 지우기", on_click=clear_all, use_container_width=True)

# ---------- 추천 실행 ----------
pending = st.session_state.pending
if pending:
    st.session_state.pending = ""
    text = st.session_state.user_text.strip()
    if not text:
        st.session_state.error = "먼저 말씀하시거나 글로 취향을 입력해 주세요."
    else:
        try:
            more = pending == "more"
            with st.spinner("취향을 분석하고, 음원 사이트에서 실제 있는 곡인지 확인하는 중입니다. "
                            "잠시만 기다려 주세요."):
                exclude = st.session_state.history if more else []
                res = recommend(text, count, region, exclude)
            st.session_state.result = res
            if not more:
                st.session_state.history = []
            st.session_state.history += [s["title"] for s in res["songs"]]
            st.session_state.error = ""
        except Exception as e:
            st.session_state.error = friendly_error(e)

if st.session_state.error:
    st.error(st.session_state.error)

# ---------- 결과 ----------
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
    if len(result["songs"]) < count:
        st.info(f"음원 사이트에서 확인된 {len(result['songs'])}곡만 보여 드립니다. "
                "'다른 곡 더 추천받기'를 누르면 더 찾아 드립니다.")
    for i, s in enumerate(result["songs"], 1):
        st.markdown(f"#### {i}번. {s['title']} - {s['artist']}")
        if s.get("album"):
            st.write("앨범: " + s["album"])
        if s["reason"]:
            st.write(s["reason"])
        if s.get("preview"):
            try:
                st.audio(s["preview"])
            except Exception:
                pass
        q = quote(f"{s['artist']} {s['title']}")
        st.link_button(
            f"{i}번 곡 유튜브에서 전곡 듣기",
            f"https://www.youtube.com/results?search_query={q}",
        )
        if s.get("link"):
            st.link_button(f"{i}번 곡 Apple Music에서 보기", s["link"])

    st.subheader("소리로 듣기")
    speed = st.select_slider("읽는 속도", options=["느리게", "보통", "빠르게"], value="보통")
    rate = {"느리게": 0.8, "보통": 1.0, "빠르게": 1.3}[speed]
    try:
        speak_component(build_speech_lines(result), rate)
    except Exception:
        st.info("소리 읽기 기능을 불러오지 못했습니다. 스크린 리더로 위 내용을 읽어 주세요.")

    st.button("🔄 다른 곡 더 추천받기", use_container_width=True,
              on_click=set_pending, args=("more",))

    st.caption("곡 제목과 가수는 Apple Music 음원 목록에서 확인된 정보입니다.")
