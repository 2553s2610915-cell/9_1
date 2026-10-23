import hashlib
import html as htmllib
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
COUNT = 6  # 한 번에 추천하는 곡 수
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

st.set_page_config(page_title="음악 나침반", layout="centered")

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 19px; }
    .stApp { background: linear-gradient(120deg, #0a84ff 0%, #3aa0ff 55%, #7cc0ff 100%); }
    .block-container, [data-testid="stMainBlockContainer"] { max-width: 920px; padding-top: 2rem; }
    .stApp p, .stApp label, .stApp h2, .stApp h3, .stApp span { color: #ffffff; }
    [data-testid="stAlert"] { background: #ffffff !important; border-radius: 14px; }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span { color: #111111 !important; }

    .hero { text-align: center; margin: 4px 0 14px 0; }
    .hero .brand { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 12px 0 0 0; padding: 0; }
    .hero .sub { color: #eaf4ff; font-size: 1.05rem; margin-top: 4px; }
    .disc {
        width: 96px; height: 96px; border-radius: 50%; margin: 0 auto; position: relative;
        background: conic-gradient(from 0deg, #1b1464, #ff2d55, #6a11cb, #00c6ff, #ff2d55, #1b1464);
        box-shadow: 0 10px 26px rgba(255, 45, 85, 0.35);
        animation: spin 9s linear infinite;
    }
    .disc::after {
        content: ""; position: absolute; top: 38%; left: 38%; width: 24%; height: 24%;
        border-radius: 50%; background: #ffffff; box-shadow: inset 0 0 0 3px #dbe8ff;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) { .disc { animation: none; } }

    .rtitle { font-size: 1.9rem; font-weight: 800; color: #ffffff; }
    .rsum { color: #ffffff; font-size: 1rem; margin: 4px 0 6px 0; line-height: 1.45; }
    .chip {
        display: inline-block; background: rgba(255,255,255,0.25); color: #ffffff;
        border: 1px solid rgba(255,255,255,0.6); border-radius: 999px;
        padding: 2px 12px; margin: 0 6px 6px 0; font-size: 0.9rem; font-weight: 700;
    }

    /* 작은 보조 버튼 */
    .stButton > button {
        font-size: 1rem; font-weight: 700; padding: 0.45rem 0.9rem; min-height: 0;
        border-radius: 999px; border: 2px solid #ffffff !important;
        background: #ffffff !important; color: #0a6cff !important;
    }
    .stButton > button p { color: inherit !important; font-size: 1rem; }
    /* 큰 주 버튼 (추천받기) */
    button[data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
        background: #0b2a6f !important; color: #ffffff !important; border: 2px solid #0b2a6f !important;
        font-size: 1.25rem; padding: 0.9rem 1rem;
    }
    button[data-testid="stBaseButton-primary"] p { font-size: 1.25rem; }
    .stTextArea textarea { font-size: 1.15rem !important; background: #ffffff !important; color: #111111 !important; }
    *:focus { outline: 4px solid #ffd54a !important; outline-offset: 2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

defaults = {
    "user_text": "",
    "query": "",
    "last_audio": "",
    "result": None,
    "history": [],
    "pending": "",
    "error": "",
    "page": "home",
    "start": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
st.session_state.user_text = st.session_state.user_text


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


def ask_model(user_text: str, ask_count: int, exclude: list) -> dict:
    from google.genai import types

    exclude_text = ", ".join(exclude[-50:]) if exclude else "없음"
    prompt = f"""
당신은 시각 장애인을 위한 친절한 음악 안내자 '음악 나침반'입니다.
사용자가 말하거나 쓴 내용을 분석해 취향에 맞는 노래 후보를 추천하세요.

[사용자 입력]
{user_text}

[가수 규칙: 매우 중요]
- 사용자가 특정 가수(또는 그룹) 이름을 말했다면, 오직 그 가수의 곡만 추천하세요.
- 비슷한 가수, 연관된 가수, 같은 소속사나 같은 장르의 다른 가수는 절대 넣지 마세요.
- "~같은", "~스타일", "~목소리"라고 말했어도 그 가수 본인의 곡만 추천하세요.
- 가수를 여러 명 말했다면 말한 가수들의 곡만 추천하세요.
- requested_artists에는 사용자가 직접 말한 가수 이름을 한글 표기와 영문 표기 모두 적으세요.
- 가수를 말하지 않았다면 requested_artists는 빈 목록으로 두고, 분위기와 장르에 맞는 여러 가수의 곡을 추천하세요.

[조건]
- 후보 곡 수: {ask_count}곡
- 이미 나온 곡(중복 금지): {exclude_text}
- 멜론, 지니, 유튜브 같은 음원 사이트에 실제로 발매된 곡만 고르세요.
- 반드시 잘 알려진 곡만 고르세요. 제목이나 가수가 조금이라도 불확실하면 넣지 마세요.
- 곡을 지어내지 마세요. 가수와 곡 제목의 조합이 실제와 정확히 일치해야 합니다.
- title과 artist는 음원 사이트에 표기된 공식 이름 그대로 쓰세요.
- artist_alt에는 같은 가수의 다른 언어 표기, title_alt에는 곡 제목의 다른 언어 표기를 쓰세요. 없으면 빈 문자열.
- 설명은 귀로 듣기 편하도록 짧고 쉬운 한국어 문장으로 쓰세요. 이모지, 특수기호, 마크다운은 쓰지 마세요.

[출력 형식: 아래 JSON만 출력]
{{
  "requested_artists": [],
  "analysis": {{
    "summary": "취향을 한두 문장으로 요약",
    "mood": ["분위기 키워드"],
    "genre": ["장르 키워드"],
    "situation": "어울리는 상황이나 감정"
  }},
  "songs": [
    {{"title": "곡 제목", "title_alt": "", "artist": "가수", "artist_alt": "", "reason": "추천 이유 한 문장"}}
  ]
}}
"""
    resp = generate(
        prompt,
        types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4),
    )
    data = parse_json(resp.text)

    requested = data.get("requested_artists")
    requested = [str(x).strip() for x in requested if x] if isinstance(requested, list) else []

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
    return {"analysis": analysis, "requested": requested, "songs": clean}


# ---------- 곡 실존 확인 (화면에는 표시하지 않음) ----------
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


def artist_ok(names: list, store_artist: str) -> bool:
    store_n = norm(store_artist)
    for n in names:
        if not n:
            continue
        if similar(n, store_artist):
            return True
        nn = norm(n)
        if len(nn) >= 2 and nn in store_n:
            return True
    return False


@st.cache_data(ttl=3600, show_spinner=False)
def itunes_search(term: str, country: str) -> list:
    params = urlencode({
        "term": term, "media": "music", "entity": "song",
        "country": country, "limit": 10,
    })
    req = Request("https://itunes.apple.com/search?" + params, headers={"User-Agent": UA})
    with urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    res = data.get("results", [])
    return res if isinstance(res, list) else []


def verify_song(c: dict):
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
                    "reason": c.get("reason", ""),
                    "names": [x for x in [c["artist"], c.get("artist_alt", ""), art] if x],
                    "titles": [x for x in [c["title"], c.get("title_alt", ""), name] if x],
                    "yt": "",
                }
    if had_error and not had_success:
        return "error", None
    return "nomatch", None


def safe_verify(c: dict):
    try:
        return verify_song(c)
    except Exception:
        return "error", None


# ---------- 유튜브: 가수 본인이 올린 공식 음원만 찾기 ----------
BAD_WORDS = [
    "mr", "m/r", "엠알", "inst", "instrumental", "karaoke", "노래방", "반주", "제거",
    "cover", "커버", "remix", "리믹스", "nightcore", "sped up", "slowed", "8d",
    "reaction", "리액션", "tutorial", "연주", "piano ver", "acoustic ver",
]


def has_bad_word(video_title: str, own_text: str) -> bool:
    vt = video_title.lower()
    own = own_text.lower()
    for w in BAD_WORDS:
        if re.search(r"(?<![a-z0-9가-힣])" + re.escape(w) + r"(?![a-z0-9가-힣])", vt):
            # 곡 제목이나 가수 이름에 원래 들어 있는 말이면 예외 (예: Mr. Brightside)
            if re.search(r"(?<![a-z0-9가-힣])" + re.escape(w) + r"(?![a-z0-9가-힣])", own):
                continue
            return True
    return False


def parse_length(txt: str) -> int:
    try:
        parts = [int(p) for p in txt.split(":")]
    except Exception:
        return 0
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


@st.cache_data(ttl=3600, show_spinner=False)
def yt_search(query: str) -> list:
    url = "https://www.youtube.com/results?" + urlencode(
        {"search_query": query, "hl": "ko", "gl": "KR"})
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Cookie": "CONSENT=YES+cb; SOCS=CAI",
    })
    with urlopen(req, timeout=8) as r:
        page = r.read().decode("utf-8", "ignore")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.DOTALL)
    if not m:
        m = re.search(r'ytInitialData"\]\s*=\s*(\{.*?\});', page, re.DOTALL)
    if not m:
        return []
    data = json.loads(m.group(1))

    found = []

    def walk(o, depth=0):
        if depth > 40:
            return
        if isinstance(o, dict):
            vr = o.get("videoRenderer")
            if isinstance(vr, dict) and vr.get("videoId"):
                found.append(vr)
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(data)
    items = []
    for vr in found:
        try:
            title = "".join(x.get("text", "") for x in vr["title"]["runs"])
            owner = vr.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
            badge = False
            for b in vr.get("ownerBadges", []) or []:
                br = b.get("metadataBadgeRenderer", {})
                if "ARTIST" in str(br.get("style", "")).upper() or \
                        "artist" in str(br.get("tooltip", "")).lower():
                    badge = True
            length = parse_length(vr.get("lengthText", {}).get("simpleText", ""))
            items.append({"id": vr["videoId"], "title": title, "channel": owner,
                          "badge": badge, "len": length})
        except Exception:
            continue
        if len(items) >= 15:
            break
    return items


def pick_official(items: list, titles: list, names: list) -> str:
    own = " ".join(titles + names)
    best_id, best_score = "", 0
    for it in items:
        vt = it["title"]
        if has_bad_word(vt, own):
            continue
        if not it["len"] or it["len"] < 60 or it["len"] > 720:
            continue
        nvt = norm(vt)
        if not any(norm(t) and norm(t) in nvt for t in titles):
            continue
        ch = it["channel"]
        score = 0
        if it["badge"]:
            score += 3
        base = ch[:-7].strip() if ch.endswith("- Topic") else ch
        if artist_ok(names, base):
            score += 3
        elif any(len(norm(n)) >= 2 and norm(n) in norm(base) for n in names):
            score += 3
        if score == 0:
            continue  # 가수 본인 채널로 확인되지 않으면 사용하지 않음
        low = vt.lower()
        if "official audio" in low or "audio" in low or "공식" in vt:
            score += 1
        if score > best_score:
            best_id, best_score = it["id"], score
    return best_id


def attach_youtube(song: dict) -> dict:
    try:
        name = song["names"][0]
        title = song["titles"][0]
        for q in (f"{name} {title} official audio", f"{name} {title}"):
            items = yt_search(q)
            vid = pick_official(items, song["titles"], song["names"])
            if vid:
                song["yt"] = vid
                break
    except Exception:
        pass
    return song


def recommend(user_text: str, count: int, exclude: list) -> dict:
    analysis = None
    requested = []
    verified = []
    seen_ids = set()
    seen_titles = set(norm(x) for x in exclude)
    tried = list(exclude)
    checked = 0
    errors = 0

    for _ in range(2):
        need = count - len(verified)
        if need <= 0:
            break
        data = ask_model(user_text, min(need + 5, 15), tried)
        if analysis is None:
            analysis = data["analysis"]
        if data["requested"]:
            requested = data["requested"]
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
            if requested and not artist_ok(requested, song["artist"]):
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
            raise RuntimeError("곡 확인에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        raise ValueError("확인된 곡을 더 찾지 못했습니다. 조금 다르게 설명해서 다시 시도해 주세요.")

    final = verified[:count]
    with ThreadPoolExecutor(max_workers=5) as ex:
        final = list(ex.map(attach_youtube, final))
    return {"analysis": analysis or {}, "songs": final}


# ---------- 표시용 ----------
def esc(x) -> str:
    return htmllib.escape(str(x or ""), quote=True)


def youtube_url(song: dict) -> str:
    if song.get("yt"):
        return "https://www.youtube.com/watch?v=" + song["yt"]
    q = (f"{song['artist']} {song['title']} official audio "
         "-MR -mr -instrumental -inst -karaoke -노래방 -반주 -cover -커버")
    return "https://www.youtube.com/results?search_query=" + quote(q)


def build_speech_lines(result: dict) -> list:
    a = result.get("analysis", {})
    lines = ["음악 나침반의 추천 결과입니다."]
    if a.get("summary"):
        lines.append("취향 분석. " + str(a["summary"]))
    for i, s in enumerate(result["songs"], 1):
        line = f"{i}번. {s['artist']}의 {s['title']}."
        if s["reason"]:
            line += " " + s["reason"]
        lines.append(line)
    lines.append("추천 안내를 마칩니다.")
    return lines


CAROUSEL_TEMPLATE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.wrap{display:flex;gap:12px;height:446px;padding:2px}
.left{flex:1;min-width:0;display:flex;flex-direction:column}
.bar{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
.hint{font-size:14px;font-weight:700;line-height:1.35}
.nav{display:flex;gap:6px;flex-shrink:0}
.pill{border:2px solid #fff;background:#fff;color:#0a6cff;font-weight:800;font-size:14px;
  padding:7px 12px;border-radius:999px;cursor:pointer;font-family:inherit}
.pill:hover{background:#eaf3ff}
.rail{flex:1;min-height:0;display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;
  position:relative;padding:4px;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.rail::-webkit-scrollbar{display:none}
.card{flex:0 0 78%;max-width:214px;scroll-snap-align:start;background:#fff;border-radius:22px;
  padding:12px;display:flex;flex-direction:column;text-decoration:none;color:#111;
  box-shadow:0 14px 30px rgba(0,40,120,.28);transition:transform .15s}
.card:hover{transform:translateY(-4px)}
.card:focus{outline:4px solid #ffd54a;outline-offset:2px}
.art{position:relative;height:130px;border-radius:16px;overflow:hidden;flex-shrink:0;
  background:linear-gradient(135deg,var(--c1),var(--c2))}
.num{position:absolute;left:12px;top:6px;font-size:42px;font-weight:900;line-height:1;
  color:rgba(255,255,255,.95);text-shadow:0 2px 8px rgba(0,0,0,.25)}
.vinyl{position:absolute;right:-34px;bottom:-34px;width:128px;height:128px;border-radius:50%;
  background:
   conic-gradient(rgba(255,255,255,0) 0 20%,rgba(255,255,255,.2) 25%,rgba(255,255,255,0) 30% 70%,rgba(255,255,255,.2) 75%,rgba(255,255,255,0) 80%),
   repeating-radial-gradient(circle at center,#15151f 0 3px,#262634 3px 5px);
  box-shadow:0 0 0 3px rgba(255,255,255,.14);animation:spin 7s linear infinite}
.vinyl::after{content:"";position:absolute;left:50%;top:50%;width:40px;height:40px;margin:-20px 0 0 -20px;
  border-radius:50%;background:var(--c3);box-shadow:0 0 0 5px rgba(255,255,255,.35)}
@keyframes spin{to{transform:rotate(360deg)}}
.title{margin-top:10px;font-size:18px;font-weight:800;line-height:1.3;word-break:keep-all;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.artist{margin-top:2px;font-size:15px;font-weight:700;color:#0a6cff}
.reason{margin-top:6px;font-size:13.5px;line-height:1.45;color:#555;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.go{margin-top:auto;background:#ff2d2d;color:#fff;font-weight:800;font-size:15px;
  text-align:center;padding:8px 6px;border-radius:16px;line-height:1.3}
.go small{display:block;font-size:12px;font-weight:700;opacity:.95}
.card:hover .go{background:#d60000}
.panel{width:128px;flex-shrink:0;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.55);
  border-radius:22px;padding:14px 10px;display:flex;flex-direction:column;gap:9px}
.ptitle{font-size:16px;font-weight:800;text-align:center;line-height:1.3}
.pbtn{width:100%;border:2px solid #fff;background:#fff;color:#0a6cff;font-weight:800;font-size:15px;
  line-height:1.3;padding:12px 6px;border-radius:14px;cursor:pointer;font-family:inherit}
.pbtn.stop{background:transparent;color:#fff}
.pbtn:hover{filter:brightness(.95)}
.plabel{font-size:13px;font-weight:700;text-align:center;margin-top:4px}
.speed{display:flex;flex-direction:column;gap:6px}
.sp{width:100%;border:2px solid #fff;background:transparent;color:#fff;font-weight:700;font-size:14px;
  padding:7px 4px;border-radius:999px;cursor:pointer;font-family:inherit}
.sp.on{background:#0b2a6f;border-color:#0b2a6f}
button:focus{outline:4px solid #ffd54a;outline-offset:2px}
@media (max-width:480px){.nav{display:none}.panel{width:112px;padding:12px 8px}}
@media (prefers-reduced-motion:reduce){.vinyl{animation:none}.card{transition:none}}
</style></head>
<body>
<div class="wrap">
  <div class="left">
    <div class="bar">
      <div class="hint">옆으로 넘겨서 고르고, 곡 카드를 누르면 유튜브가 열려요</div>
      <div class="nav">
        <button class="pill" id="prev" type="button">이전 곡</button>
        <button class="pill" id="next" type="button">다음 곡</button>
      </div>
    </div>
    <div class="rail" id="rail" role="region" aria-label="추천 노래 목록">__CARDS__</div>
  </div>
  <div class="panel" role="group" aria-label="소리로 듣기">
    <div class="ptitle">소리로 듣기</div>
    <button class="pbtn" id="play" type="button">추천 곡 읽어 주기</button>
    <button class="pbtn stop" id="stop" type="button">멈추기</button>
    <div class="plabel">읽는 속도</div>
    <div class="speed">
      <button class="sp" data-rate="0.8" type="button" aria-pressed="false">느리게</button>
      <button class="sp on" data-rate="1.0" type="button" aria-pressed="true">보통</button>
      <button class="sp" data-rate="1.3" type="button" aria-pressed="false">빠르게</button>
    </div>
  </div>
</div>
<script>
  var LINES = __LINES__;
  var START = __START__;
  var rate = 1.0;
  var synth = window.speechSynthesis;
  var rail = document.getElementById('rail');

  function step(dir) {
    var c = rail.querySelector('.card');
    var w = c ? c.offsetWidth + 12 : 220;
    rail.scrollBy({left: dir * w, behavior: 'smooth'});
  }
  document.getElementById('prev').onclick = function() { step(-1); };
  document.getElementById('next').onclick = function() { step(1); };
  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') { step(-1); }
    if (e.key === 'ArrowRight') { step(1); }
  });

  var cards = rail.querySelectorAll('.card');
  if (START > 0 && cards[START]) { rail.scrollLeft = cards[START].offsetLeft - 4; }

  var sps = document.querySelectorAll('.sp');
  sps.forEach(function(b) {
    b.onclick = function() {
      rate = parseFloat(b.getAttribute('data-rate'));
      sps.forEach(function(x) { x.classList.remove('on'); x.setAttribute('aria-pressed', 'false'); });
      b.classList.add('on');
      b.setAttribute('aria-pressed', 'true');
    };
  });

  document.getElementById('play').onclick = function() {
    if (!synth) { alert('이 브라우저는 음성 읽기를 지원하지 않습니다.'); return; }
    synth.cancel();
    LINES.forEach(function(t) {
      var u = new SpeechSynthesisUtterance(t);
      u.lang = 'ko-KR';
      u.rate = rate;
      synth.speak(u);
    });
  };
  document.getElementById('stop').onclick = function() { if (synth) synth.cancel(); };
</script>
</body></html>
"""


def cards_html(songs: list) -> str:
    out = []
    for i, s in enumerate(songs, 1):
        h = int(hashlib.md5((s["title"] + s["artist"]).encode("utf-8")).hexdigest()[:6], 16) % 360
        c1 = f"hsl({h},85%,58%)"
        c2 = f"hsl({(h + 55) % 360},85%,42%)"
        c3 = f"hsl({(h + 180) % 360},90%,72%)"
        if s.get("yt"):
            go_main, go_sub = "유튜브에서 듣기", "가수 공식 음원"
            note = "가수 공식 음원 영상으로 연결됩니다."
        else:
            go_main, go_sub = "유튜브에서 찾기", "공식 음원 검색"
            note = "공식 음원 검색 결과로 연결됩니다."
        label = f"{i}번 곡. {s['title']}, {s['artist']}. 누르면 유튜브가 열립니다. {note}"
        out.append(
            f'<a class="card" href="{esc(youtube_url(s))}" target="_blank" rel="noopener noreferrer" '
            f'aria-label="{esc(label)}" style="--c1:{c1};--c2:{c2};--c3:{c3}">'
            f'<div class="art" aria-hidden="true"><span class="num">{i}</span><div class="vinyl"></div></div>'
            f'<div class="title">{esc(s["title"])}</div>'
            f'<div class="artist">{esc(s["artist"])}</div>'
            f'<div class="reason">{esc(s["reason"])}</div>'
            f'<div class="go">{go_main}<small>{go_sub}</small></div>'
            '</a>'
        )
    return "".join(out)


def render_carousel(result: dict, start: int):
    lines = json.dumps(build_speech_lines(result), ensure_ascii=False).replace("</", "<\\/")
    page = (CAROUSEL_TEMPLATE
            .replace("__LINES__", lines)
            .replace("__START__", str(int(start)))
            .replace("__CARDS__", cards_html(result["songs"])))
    components.html(page, height=456, scrolling=False)


# ---------- 콜백 ----------
def set_pending(kind: str):
    st.session_state.pending = kind


def go_home():
    st.session_state.page = "home"
    st.session_state.error = ""


# ---------- 추천 실행 ----------
pending = st.session_state.pending
if pending:
    st.session_state.pending = ""
    try:
        more = pending == "more" and bool(st.session_state.result)
        text = st.session_state.query if more else st.session_state.user_text.strip()
        if not text:
            raise ValueError("먼저 마이크로 말하거나 내용을 입력해 주세요.")
        with st.spinner("취향을 분석하고 노래를 찾는 중입니다. 잠시만 기다려 주세요."):
            res = recommend(text, COUNT, st.session_state.history if more else [])
        if more:
            st.session_state.start = len(st.session_state.result["songs"])
            st.session_state.result["songs"] += res["songs"]
        else:
            st.session_state.query = text
            st.session_state.result = res
            st.session_state.history = []
            st.session_state.start = 0
        st.session_state.history += [s["title"] for s in res["songs"]]
        st.session_state.page = "result"
        st.session_state.error = ""
    except Exception as e:
        st.session_state.error = str(e) if isinstance(e, ValueError) else friendly_error(e)


# ---------- 첫 화면 ----------
def render_home():
    st.markdown(
        '<div class="hero"><div class="disc" aria-hidden="true"></div>'
        '<h1 class="brand">음악 나침반</h1>'
        '<div class="sub">듣고 싶은 노래를 말하거나 써 주세요</div></div>',
        unsafe_allow_html=True,
    )

    if not get_api_key():
        st.warning("GEMINI_API_KEY가 설정되지 않았습니다. 배포 설정의 Secrets에 키를 등록해 주세요.")
    if st.session_state.error:
        st.error(st.session_state.error)

    audio = None
    if hasattr(st, "audio_input"):
        try:
            audio = st.audio_input("마이크 (눌러서 말하고, 끝나면 다시 눌러 주세요)")
        except Exception:
            audio = None

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
                    st.success("말씀하신 내용이 아래 내용창에 써졌습니다. 고칠 수 있어요.")
                else:
                    st.warning("말소리를 알아듣지 못했습니다. 다시 말씀해 주세요.")
        except Exception as e:
            st.error(friendly_error(e))

    st.text_area(
        "내용 (직접 써도 되고, 마이크로 말하면 여기에 글이 써집니다)",
        key="user_text",
        height=150,
        placeholder="예: 비 오는 날 듣기 좋은 잔잔한 노래 / 아이유 노래",
    )

    st.button("추천받기", type="primary", use_container_width=True,
              on_click=set_pending, args=("new",))


# ---------- 추천 곡 화면 ----------
def render_result():
    result = st.session_state.result
    if not result or not result.get("songs"):
        st.session_state.page = "home"
        render_home()
        return

    a = result.get("analysis", {})
    chips = []
    for key in ("mood", "genre"):
        v = a.get(key)
        if isinstance(v, list):
            chips += [str(x) for x in v if x]
    chips_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips[:6])
    summary = esc(a.get("summary", ""))

    st.markdown(
        f'<div><span class="rtitle">추천 노래</span>'
        f'<div class="rsum">{summary}</div>{chips_html}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.error:
        st.error(st.session_state.error)

    render_carousel(result, st.session_state.start)

    b1, b2, _sp = st.columns([2, 2, 3])
    with b1:
        st.button("다른 곡 더 추천받기", use_container_width=True,
                  on_click=set_pending, args=("more",))
    with b2:
        st.button("다시 입력하기", use_container_width=True, on_click=go_home)


if st.session_state.page == "result":
    render_result()
else:
    render_home()
