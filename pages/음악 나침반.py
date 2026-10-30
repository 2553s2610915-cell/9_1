import hashlib
import html as htmllib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import streamlit as st
import streamlit.components.v1 as components

# 앞에서부터 시도합니다. 서버가 바쁘거나 모델이 종료되면 다음 모델로 넘어갑니다.
MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
]
COUNT = 6           # 비슷한 느낌의 곡 수 / 가수의 곡 수
YT_LOOKUP_MAX = 12  # 공식 음원 영상을 찾아보는 곡 수 (나머지는 유튜브 검색 링크)

# 사용 방법 설명 (정보 아이콘에 마우스를 올리면 보이는 글)
HOWTO = [
    ("마이크로 말하기",
     "마이크 버튼을 눌러 말하고, 끝나면 다시 눌러 주세요. 말한 내용이 내용창에 글로 써지고, 틀린 부분은 고칠 수 있어요."),
    ("가수와 제목",
     "가수와 제목은 한 줄에 같이 써요. '아이유 좋은날'처럼 써도 되고 '좋은날 아이유'처럼 순서를 바꿔도 돼요. "
     "가수를 여러 명 쓸 때는 Enter 키로 줄을 나눠 주세요."),
    ("가수 이름",
     "가수 이름은 한글도 영어도 돼요. 숀이라고 써도 SHAUN이라고 써도 같은 가수를 찾아요."),
    ("한 줄만 쓸 때",
     "가수 이름 없이 쓰면 띄어쓰기가 있어도 전체가 노래 제목이에요. 분위기만 써도 돼요."),
    ("말로 가수와 제목 입력",
     '"가수 아이유, 제목 좋은날"이라고 말하면 내용창에 "아이유 좋은날"처럼 한 줄로 써져요. '
     '가수를 여러 명 말하면 줄이 나뉘어 써져요. "가수", "제목"이라는 말을 쓰지 않으면 말한 그대로 써져요.'),
    ("추천받기",
     "추천받기 버튼을 누르면 곡 카드가 나와요. 글을 누르면 읽어 주고, 오른쪽 위 스위치로 읽기를 켜고 끌 수 있어요."),
]

st.set_page_config(page_title="음악 나침반", page_icon="🧭", layout="centered")

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 19px; }
    .stApp {
        background: radial-gradient(circle at 50% -10%, #1b1b26 0%, #050507 55%, #000000 100%);
        color-scheme: dark;
    }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container, [data-testid="stMainBlockContainer"] { max-width: 920px; padding-top: 2rem; }
    .stApp p, .stApp label, .stApp h2, .stApp h3, .stApp span { color: #ffffff; }
    [data-testid="stAlert"] { background: #ffffff !important; border-radius: 14px; }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span { color: #111111 !important; }

    .hero { text-align: center; margin: 4px 0 14px 0; }
    .hero .brand { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 12px 0 0 0; padding: 0; }
    .hero .sub { color: #d6d6de; font-size: 1.05rem; margin-top: 4px; }
    .disc {
        width: 96px; height: 96px; border-radius: 50%; margin: 0 auto; position: relative;
        background: conic-gradient(from 0deg, #1b1464, #ff2d55, #6a11cb, #00c6ff, #ff2d55, #1b1464);
        box-shadow: 0 10px 30px rgba(255, 45, 85, 0.35);
        animation: spin 9s linear infinite;
    }
    .disc::after {
        content: ""; position: absolute; top: 38%; left: 38%; width: 24%; height: 24%;
        border-radius: 50%; background: #000000; box-shadow: inset 0 0 0 3px #3a3a46;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) { .disc { animation: none; } }

    /* 사용 방법 정보 아이콘 (마우스를 올리면 설명이 보입니다) */
    .infowrap { display: flex; justify-content: center; margin: 0 0 12px 0; }
    .info {
        position: relative; display: inline-flex; align-items: center; flex-wrap: wrap;
        gap: 10px; cursor: help; padding: 4px 10px; border-radius: 999px;
    }
    .info .ic {
        position: relative; display: inline-block; width: 34px; height: 34px; border-radius: 50%;
        background: #a3a3ab; flex-shrink: 0;
    }
    .info .ic::before {
        content: ""; position: absolute; left: 50%; top: 7px; width: 5px; height: 5px;
        margin-left: -2.5px; border-radius: 50%; background: #000000;
    }
    .info .ic::after {
        content: ""; position: absolute; left: 50%; top: 15px; width: 5px; height: 12px;
        margin-left: -2.5px; border-radius: 3px; background: #000000;
    }
    .info:hover .ic, .info:focus .ic, .info.open .ic { background: #ffd54a; }
    .info .lab { font-weight: 800; font-size: 1.05rem; color: #ffffff; }
    .info .sm { font-size: 0.85rem; color: #b9b9c4; }
    .info .tip {
        display: none; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
        margin-top: 10px; width: min(540px, 88vw); background: #15151a; border: 2px solid #ffd54a;
        border-radius: 14px; padding: 12px 18px; z-index: 1000; text-align: left; cursor: default;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
    }
    .info .tip::before { content: ""; position: absolute; left: 0; right: 0; top: -14px; height: 14px; }
    .info:hover .tip, .info:focus .tip, .info:focus-within .tip, .info.open .tip { display: block; }
    .info .tip p { margin: 6px 0; font-size: 0.98rem; line-height: 1.55; color: #ffffff; }
    .info .tip b { color: #ffd54a; }

    .rtitle { font-size: 1.9rem; font-weight: 800; color: #ffffff; }
    .rsum { color: #e6e6ec; font-size: 1rem; margin: 4px 0 6px 0; line-height: 1.45; }
    .chip {
        display: inline-block; background: #17171c; color: #ffd54a;
        border: 1px solid #ffd54a; border-radius: 999px;
        padding: 2px 12px; margin: 0 6px 6px 0; font-size: 0.9rem; font-weight: 700;
    }

    .stButton > button, .stLinkButton > a, a[data-testid^="stBaseLinkButton"] {
        font-size: 1rem; font-weight: 700; padding: 0.4rem 1.1rem; min-height: 0;
        border-radius: 999px;
        border: 2px solid #ffffff !important; background: transparent !important; color: #ffffff !important;
    }
    .stButton > button:hover, .stLinkButton > a:hover { background: #22222a !important; }
    .stButton > button p, .stLinkButton > a p { color: inherit !important; font-size: 1rem; }
    button[data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
        background: #ffd54a !important; color: #000000 !important; border: 2px solid #ffd54a !important;
        padding: 0.5rem 1.4rem;
    }
    button[data-testid="stBaseButton-primary"]:hover { background: #ffe58a !important; }

    .stTextArea textarea {
        font-size: 1.1rem !important; background: #15151a !important; color: #ffffff !important;
        border: 2px solid #4a4a55 !important; border-radius: 14px !important;
    }
    .stTextArea textarea:focus { border-color: #ffd54a !important; }
    .stTextArea textarea::placeholder { color: #9a9aa6 !important; }

    [data-testid="stAudioInput"] { background: #15151a; border-radius: 14px; padding: 4px; }
    [data-testid="stAudioInput"] * { color: #ffffff; }

/* 마이크 아이콘 검정색으로 변경 */
[data-testid="stAudioInput"] button svg {
    fill: #000000 !important;
    color: #000000 !important;
    stroke: #000000 !important;
}

[data-testid="stAudioInput"] button {
    background: #ffffff !important;
}
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
# 화면이 바뀌어도 입력한 내용이 사라지지 않게 유지
st.session_state.user_text = st.session_state.user_text


# ---------- 소리로 읽어 주기 (글을 누르면 읽어 주는 기능, 기본 켜짐) ----------
PARENT_JS = r"""
(function () {
  if (window.__mcSpeech) return;
  var on = true;
  try { if (localStorage.getItem('mcSpeech') === 'off') on = false; } catch (e) {}
  var last = '', lastT = 0;
  function say(t) {
    var s = window.speechSynthesis;
    if (!s || !t) return;
    try {
      s.cancel();
      var u = new SpeechSynthesisUtterance(t);
      u.lang = 'ko-KR';
      u.rate = 1.0;
      s.speak(u);
    } catch (e) {}
  }
  window.__mcSpeech = {
    isOn: function () { return on; },
    set: function (v) {
      on = !!v;
      try { localStorage.setItem('mcSpeech', on ? 'on' : 'off'); } catch (e) {}
      if (!on) { try { window.speechSynthesis.cancel(); } catch (e) {} }
    },
    say: say,
    speak: function (t) { if (on) say(t); }
  };
  function speakOnce(t) {
    t = (t || '').replace(/\s+/g, ' ').trim();
    if (!t) return;
    var now = Date.now();
    if (t === last && now - lastT < 500) return;
    last = t; lastT = now;
    say(t);
  }
  /* 글을 누르면 읽어 줍니다 (버튼과 입력칸은 제외). 정보 아이콘은 누르면 설명을 열고 닫습니다. */
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var info = t.closest('.info');
    var opened = document.querySelectorAll('.info.open');
    for (var i = 0; i < opened.length; i++) {
      if (opened[i] !== info) { opened[i].classList.remove('open'); }
    }
    if (info) { info.classList.toggle('open'); }
    if (!on) return;
    if (t.closest('button, a, textarea, input, select, [role="button"], [data-testid="stAudioInput"]')) return;
    var el = info || t.closest('[data-testid="stAlert"]') ||
             t.closest('.rsum, .rtitle, .chip, .sub, .brand, h1, h2, h3, label, li, p');
    if (!el) return;
    var sp = el.getAttribute ? el.getAttribute('data-speak') : '';
    speakOnce(sp || el.innerText || el.textContent);
  }, true);
  /* 버튼이나 입력칸이나 정보 아이콘으로 이동하면 기능을 설명해 줍니다 */
  document.addEventListener('focusin', function (e) {
    if (!on) return;
    var t = e.target;
    if (!t || !t.closest || !t.matches('button, textarea, input, a, .info')) return;
    var txt = '';
    if (t.closest('[data-testid="stAudioInput"]')) {
      txt = '마이크로 말하기 버튼';
    } else if (t.tagName === 'TEXTAREA' || t.tagName === 'INPUT') {
      var box = t.closest('[data-testid="stTextArea"]');
      var lab = box ? box.querySelector('label') : null;
      txt = (lab ? lab.innerText : (t.getAttribute('aria-label') || '')) + '. 글을 쓰는 칸입니다.';
    } else if (t.classList && t.classList.contains('info')) {
      txt = t.getAttribute('data-speak') || '사용 방법';
    } else {
      txt = (t.getAttribute('aria-label') || t.innerText || '') + ' 버튼';
    }
    speakOnce(txt);
  }, true);
})();
"""


def install_js() -> str:
    code = json.dumps(PARENT_JS).replace("</", "<\\/")
    return (
        "try{var P=window.parent;if(!P.__mcSpeech){"
        "var sc=P.document.createElement('script');"
        "sc.textContent=" + code + ";"
        "P.document.head.appendChild(sc);}}catch(e){}"
    )


TOGGLE_HTML = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.bar{display:flex;align-items:center;justify-content:flex-end;gap:12px;height:54px}
.lbl{text-align:right;cursor:pointer;line-height:1.25}
.lbl b{display:block;font-size:16px;color:#fff}
.lbl span{font-size:12.5px;color:#c9c9d1}
.sw{position:relative;width:96px;height:44px;border-radius:999px;border:3px solid;cursor:pointer;
  padding:0;flex-shrink:0;transition:background .2s,border-color .2s;font-family:inherit}
.sw.on{background:linear-gradient(#2bdc62,#14b645);border-color:#0f9a38;
  box-shadow:inset 0 3px 6px rgba(0,0,0,.25)}
.sw.off{background:linear-gradient(#d8d8de,#ececf0);border-color:#b8b8c0;
  box-shadow:inset 0 3px 6px rgba(0,0,0,.18)}
.txt{position:absolute;top:50%;transform:translateY(-50%);font-weight:900;font-size:17px;letter-spacing:1px}
.sw.on .txt{left:14px;color:#0b8a32;text-shadow:0 1px 0 rgba(255,255,255,.35)}
.sw.off .txt{right:12px;color:#a9a9b3;text-shadow:0 1px 0 rgba(255,255,255,.8)}
.knob{position:absolute;top:2px;width:34px;height:34px;border-radius:50%;
  background:linear-gradient(#ffffff,#ececf0);box-shadow:0 3px 6px rgba(0,0,0,.35);transition:left .2s}
.sw.on .knob{left:52px}
.sw.off .knob{left:4px}
button:focus{outline:4px solid #ffd54a;outline-offset:2px}
@media (prefers-reduced-motion:reduce){.knob,.sw{transition:none}}
</style></head>
<body>
<div class="bar">
  <div class="lbl" id="lbl"><b>소리로 읽어 주기</b><span>글을 누르면 읽어 줘요</span></div>
  <button class="sw on" id="sw" type="button" role="switch" aria-checked="true"
    aria-label="소리로 읽어 주기 스위치. 누르면 켜고 끕니다."><span class="txt" id="txt">ON</span><span class="knob"></span></button>
</div>
<script>
  __INSTALL__
  var S = null;
  try { S = window.parent.__mcSpeech || null; } catch (e) {}
  if (!S) {
    S = {
      state: true,
      isOn: function () { return this.state; },
      set: function (v) { this.state = !!v; if (!v) { try { speechSynthesis.cancel(); } catch (e) {} } },
      say: function (t) {
        try { speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(t); u.lang = 'ko-KR'; speechSynthesis.speak(u); } catch (e) {}
      },
      speak: function (t) { if (this.state) this.say(t); }
    };
  }
  var sw = document.getElementById('sw');
  var txt = document.getElementById('txt');
  function render() {
    var on = S.isOn();
    sw.className = 'sw ' + (on ? 'on' : 'off');
    sw.setAttribute('aria-checked', on ? 'true' : 'false');
    txt.textContent = on ? 'ON' : 'OFF';
  }
  sw.onclick = function () {
    var next = !S.isOn();
    S.set(next);
    render();
    if (next) {
      S.say('소리로 읽어 주기를 켰습니다. 글을 누르면 읽어 드립니다.');
    } else {
      S.say('소리로 읽어 주기를 껐습니다.');
    }
  };
  document.getElementById('lbl').onclick = function () {
    S.speak('소리로 읽어 주기. 지금은 ' + (S.isOn() ? '켜져' : '꺼져') +
            ' 있습니다. 오른쪽 스위치로 켜고 끌 수 있습니다.');
  };
  render();
</script>
</body></html>
"""


def render_toggle():
    components.html(TOGGLE_HTML.replace("__INSTALL__", install_js()), height=58, scrolling=False)


def esc(x) -> str:
    return htmllib.escape(str(x or ""), quote=True)


def info_html() -> str:
    """정보(i) 아이콘. 마우스를 올리거나 누르면 사용 방법이 보입니다."""
    speak = "사용 방법. " + " ".join(f"{t}. {d}" for t, d in HOWTO)
    items = "".join(f'<p><b>{esc(t)}</b> {esc(d)}</p>' for t, d in HOWTO)
    return (
        '<div class="infowrap">'
        f'<div class="info" tabindex="0" role="note" aria-label="{esc(speak)}" data-speak="{esc(speak)}">'
        '<span class="ic" aria-hidden="true"></span>'
        '<span class="lab">사용 방법</span>'
        '<span class="sm">마우스를 올리거나 눌러 보세요</span>'
        f'<div class="tip">{items}</div>'
        '</div></div>'
    )


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
    """서버가 바쁘면(503) 잠시 기다려 다시 시도하고, 안 되면 다음 모델로 넘어갑니다."""
    client = get_client()
    last = None
    for model in MODELS:
        for attempt in range(3):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except Exception as e:
                last = e
                s = str(e)
                low = s.lower()
                if "404" in s or "NOT_FOUND" in s or "no longer available" in low:
                    break
                if "429" in s or "RESOURCE_EXHAUSTED" in s:
                    break
                if ("503" in s or "UNAVAILABLE" in s or "high demand" in low
                        or "overloaded" in low or "500" in s or "INTERNAL" in s or "deadline" in low):
                    if attempt < 2:
                        time.sleep(1.0 + attempt)
                        continue
                    break
                raise
    raise last if last else RuntimeError("모델을 찾지 못했습니다.")


def friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "NO_KEY" in msg:
        return ("GEMINI_API_KEY가 설정되지 않았습니다. "
                "Streamlit Cloud의 Secrets에 GEMINI_API_KEY를 등록해 주세요.")
    if "503" in msg or "UNAVAILABLE" in msg or "high demand" in low or "overloaded" in low:
        return "지금 AI 서버에 사용자가 몰려 있습니다. 잠시 후 추천받기를 다시 눌러 주세요."
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
        "다음 음성을 들리는 그대로 글자로 받아 적어 주세요. 주로 한국어입니다. "
        "설명이나 따옴표 없이 받아쓴 내용만 출력하세요. 말소리가 없으면 빈 문자열만 출력하세요.\n"
        "단, 말하는 사람이 '가수'라고 말한 뒤 이름을, '제목'이라고 말한 뒤 노래 제목을 말했다면 "
        "'가수', '제목'이라는 말은 빼고 '가수이름 노래제목'을 한 줄로 적으세요. "
        "가수를 여러 명 말했다면 가수마다 줄을 나눠서 적으세요. "
        "그렇지 않으면 말한 그대로 한 줄로 적으세요."
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


def str_list(v) -> list:
    return [str(x).strip() for x in v if x] if isinstance(v, list) else []


# ---------- 이름 비교 도구 ----------
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


def norm_artist(s: str) -> str:
    n = norm(s)
    if n.startswith("the") and len(n) > 5:
        n = n[3:]
    return n


def same_artist(names: list, store: str) -> bool:
    """가수 이름이 사실상 같은 경우만 True (비슷한 이름의 다른 가수는 걸러냅니다)."""
    parts = [store] + re.split(r"\s*(?:,|&|/| feat\.? | ft\.? | with )\s*", store or "", flags=re.I)
    for p in parts:
        pn = norm_artist(p)
        if not pn:
            continue
        for n in names:
            nn = norm_artist(n)
            if nn and (nn == pn or SequenceMatcher(None, nn, pn).ratio() >= 0.9):
                return True
    return False


def uniq(items: list) -> list:
    out = []
    keys = set()
    for x in items:
        x = (x or "").strip()
        k = norm(x)
        if not k or k in keys:
            continue
        keys.add(k)
        out.append(x)
    return out


def strip_artist(line: str, typed: list) -> str:
    """줄에서 가수 이름 부분을 빼고 남은 말(제목)을 돌려줍니다."""
    out = line
    for t in sorted(typed, key=len, reverse=True):
        new = re.sub(re.escape(t), " ", out, count=1, flags=re.I)
        if new != out:
            out = new
            break
    return re.sub(r"\s+", " ", out).strip(" ,.-")


def dedupe_songs(items: list) -> list:
    out = []
    keys = set()
    for s in items:
        k = norm(s["title"]) + "|" + norm_artist(s["artist"])
        if k in keys:
            continue
        keys.add(k)
        out.append(s)
    return out


# ---------- AI: 줄 해석 + 취향 분석 ----------
def ask_model(lines: list, ask_count: int, exclude: list) -> dict:
    """줄마다 가수와 제목을 나누고, 취향을 분석하고, (가수가 없을 때 쓸) 비슷한 느낌의 곡을 받습니다."""
    from google.genai import types

    numbered = "\n".join(f"{i + 1}. {l}" for i, l in enumerate(lines))
    exclude_text = ", ".join(exclude[-50:]) if exclude else "없음"
    prompt = f"""
당신은 시각 장애인을 위한 친절한 음악 안내자 '음악 나침반'입니다.
사용자가 입력한 내용을 분석해 취향에 맞는 노래를 추천하세요.

[입력: 줄마다 따로 해석합니다. 줄바꿈은 가수를 여러 명 쓸 때 사용합니다]
{numbered}

[줄 해석 규칙]
- 한 줄에는 가수 이름과 노래 제목이 함께 있을 수 있습니다. 순서는 "가수 제목"도, "제목 가수"도 가능합니다.
- 가수 이름과 노래 제목 안에도 띄어쓰기가 있을 수 있습니다.
- 줄에 실제로 있는 가수(또는 그룹) 이름이 확실할 때만 artist에 적으세요. artist는 사용자가 쓴 표기 그대로 적으세요.
- 가수 이름만 있는 줄이면 artist만 적고 title은 빈 문자열로 두세요.
- title에는 가수 이름을 뺀 나머지 중 노래 제목인 부분을 사용자가 쓴 그대로 적으세요. 고치거나 번역하지 마세요.
- mood에는 분위기나 상황을 설명하는 말만 적으세요. 없으면 빈 문자열.
- 일반 단어나 문장은 가수가 아닙니다. 노래 제목만 있는 줄이거나 가수 이름이 확실하지 않으면 artist는 빈 문자열로 두세요.
- artist_aliases에는 그 가수의 한글 표기와 영문 표기를 모두 적으세요. 사용자가 쓴 표기도 포함하세요. (예: 숀과 SHAUN, 아이유와 IU)

[songs 규칙: 모든 줄에 가수가 없을 때만, 아니면 빈 목록]
- 사용자가 단어나 제목만 썼다면, 그 단어와 비슷한 분위기의 곡을 쓰세요. 제목이 같은 곡은 따로 찾으니 쓰지 마세요.
- 추천 곡 수: {ask_count}곡
- 이미 나온 곡(중복 금지): {exclude_text}
- 가수가 직접 발표한 원곡만, 반드시 실제로 발매된 아주 유명한 곡만 쓰세요. 확실하지 않으면 쓰지 마세요.
- 리메이크, 커버, MR, 반주, 노래방 버전은 안 됩니다.
- title과 artist는 음원 사이트에 표기된 공식 이름 그대로 쓰세요.
- artist_alt에는 같은 가수의 다른 언어 표기, title_alt에는 곡 제목의 다른 언어 표기를 쓰세요. 없으면 빈 문자열.
- 설명은 귀로 듣기 편하도록 짧고 쉬운 한국어 문장으로 쓰세요. 이모지, 특수기호, 마크다운은 쓰지 마세요.

[출력 형식: 아래 JSON만 출력]
{{
  "lines": [
    {{"line": 1, "artist": "", "artist_aliases": [], "title": "", "mood": ""}}
  ],
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
        types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3),
    )
    data = parse_json(resp.text)

    by_idx = {}
    raw_lines = data.get("lines")
    if isinstance(raw_lines, list):
        for it in raw_lines:
            if isinstance(it, dict):
                try:
                    by_idx[int(it.get("line")) - 1] = it
                except Exception:
                    continue

    infos = []
    for i, line in enumerate(lines):
        it = by_idx.get(i, {})
        artist = str(it.get("artist", "") or "").strip()
        aliases = str_list(it.get("artist_aliases"))
        title = str(it.get("title", "") or "").strip()
        mood = str(it.get("mood", "") or "").strip()
        ln = norm(line)
        # AI가 말한 가수가 실제로 줄에 쓰여 있는지 확인합니다 (지어낸 가수 방지)
        typed = [x for x in [artist] + aliases if x and norm(x) and norm(x) in ln]
        if not artist or not typed:
            infos.append({"artist": "", "aliases": [], "title": "", "mood": ""})
            continue
        artist = typed[0]
        if title and norm(title) not in ln:
            title = strip_artist(line, typed)
        if norm(title) == norm(artist):
            title = ""
        infos.append({"artist": artist, "aliases": uniq(aliases), "title": title, "mood": mood})

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
    return {"analysis": analysis, "lines": infos, "songs": clean}


def pick_from_catalog(user_text: str, cands: list, count: int) -> list:
    """스토어에 실제로 있는 곡 목록에서, 취향에 맞는 곡의 번호만 AI가 고릅니다."""
    from google.genai import types

    listing = "\n".join(f"{i + 1}. {c['artist']} - {c['title']}" for i, c in enumerate(cands))
    prompt = f"""
아래는 실제로 발매된 곡의 번호 목록입니다. 사용자의 요청에 가장 잘 맞는 곡을 {count}곡 고르세요.
반드시 목록에 있는 번호만 고르세요. 요청에 분위기나 장르가 없으면 가장 유명한 곡 위주로 고르세요.
reason은 귀로 듣기 편한 짧은 한국어 한 문장입니다. 이모지와 특수기호는 쓰지 마세요.

[사용자 요청]
{user_text}

[곡 목록]
{listing}

[출력 형식: 아래 JSON만 출력]
{{"picks": [{{"n": 1, "reason": "추천 이유 한 문장"}}]}}
"""
    chosen = []
    used = set()
    try:
        resp = generate(
            prompt,
            types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3),
        )
        data = parse_json(resp.text)
        for p in data.get("picks", []):
            if not isinstance(p, dict):
                continue
            try:
                n = int(p.get("n"))
            except Exception:
                continue
            if 1 <= n <= len(cands) and n not in used:
                used.add(n)
                chosen.append((n - 1, str(p.get("reason", "")).strip()))
    except Exception:
        pass  # AI가 실패해도 목록 앞쪽의 곡으로 채웁니다

    for i in range(len(cands)):
        if len(chosen) >= count:
            break
        if (i + 1) not in used:
            used.add(i + 1)
            chosen.append((i, ""))

    out = []
    for idx, reason in chosen[:count]:
        c = cands[idx]
        out.append({
            "title": c["title"], "title_alt": "",
            "artist": c["artist"], "artist_alt": "",
            "reason": reason or f"{c['artist']}의 곡입니다.",
            "yt": "", "url": "", "tag": "", "match": False,
        })
    return out


# ---------- 음원 스토어(실제 곡 목록) ----------
@st.cache_data(ttl=3600, show_spinner=False)
def itunes_get(url: str) -> list:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    res = data.get("results", [])
    return res if isinstance(res, list) else []


def itunes_search(term: str, country: str, entity: str = "song",
                  attribute: str = "", limit: int = 10) -> list:
    p = {"term": term, "media": "music", "entity": entity, "country": country, "limit": limit}
    if attribute:
        p["attribute"] = attribute
    return itunes_get("https://itunes.apple.com/search?" + urlencode(p))


def itunes_lookup_songs(artist_id, country: str) -> list:
    p = {"id": artist_id, "entity": "song", "limit": 200, "country": country}
    return itunes_get("https://itunes.apple.com/lookup?" + urlencode(p))


BAD_TITLE_RE = re.compile(
    r"\b(?:inst|instrumental|karaoke|remix|live|mr|cover|sped up|slowed|off vocal)\b|리믹스|반주|노래방|커버|라이브",
    re.I,
)
BAD_ALBUM_RE = re.compile(r"instrumental|karaoke|off vocal|\bmr\b|노래방|반주", re.I)


def is_bad_track(title: str, album: str) -> bool:
    extra = " ".join(re.findall(r"[\(\[](.*?)[\)\]]", title or ""))
    if " - " in (title or ""):
        extra += " " + title.split(" - ", 1)[1]
    if BAD_TITLE_RE.search(extra):
        return True
    return bool(BAD_ALBUM_RE.search(album or ""))


def resolve_artist(aliases: list):
    """한글/영어 이름으로 스토어에서 가수를 찾습니다. (가수 id 목록, 스토어에 적힌 이름 목록)"""
    ids = []
    store_names = []
    seen_ids = set()
    for name in aliases[:4]:
        for country in ("KR", "US"):
            try:
                rows = itunes_search(name, country, entity="musicArtist", limit=5)
            except Exception:
                continue
            for r in rows:
                aid = r.get("artistId")
                an = (r.get("artistName") or "").strip()
                if aid and an and aid not in seen_ids and same_artist(aliases, an):
                    seen_ids.add(aid)
                    ids.append((aid, country))
                    store_names.append(an)
        if len(ids) >= 2:
            break
    return ids[:2], uniq(store_names)


def artist_catalog(ids: list, names: list) -> list:
    """가수의 실제 곡 목록을 스토어에서 가져옵니다."""
    tracks = []
    for aid, country in ids[:3]:
        try:
            rows = itunes_lookup_songs(aid, country)
        except Exception:
            continue
        for r in rows:
            if r.get("wrapperType") == "track" and r.get("kind") == "song":
                tracks.append(r)

    if not tracks:
        for name in names[:4]:
            for country in ("KR", "US"):
                try:
                    rows = itunes_search(name, country, entity="song", attribute="artistTerm", limit=200)
                except Exception:
                    continue
                for r in rows:
                    if r.get("kind") == "song" and same_artist(names, r.get("artistName", "")):
                        tracks.append(r)

    out = []
    seen = set()
    for r in tracks:
        title = (r.get("trackName") or "").strip()
        art = (r.get("artistName") or "").strip()
        if not title or not art:
            continue
        if is_bad_track(title, r.get("collectionName", "")):
            continue
        k = norm(title)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append({"title": title, "artist": art})
    return out[:120]


# ---------- 입력한 제목과 같은 곡 먼저 찾기 ----------
STOP_TOKENS = {
    "노래", "노래들", "곡", "곡들", "음악", "추천", "추천해줘", "추천해", "추천해주세요",
    "들려줘", "틀어줘", "해줘", "주세요", "좀", "찾아줘", "알려줘", "듣고", "싶어", "싶어요", "노래좀",
}


def build_title_queries(raw: str) -> list:
    """가수 이름이 없는 줄은 띄어쓰기가 있어도 전체를 제목으로 봅니다. (못 찾으면 군더더기 말을 뺀 것도 시도)"""
    raw = (raw or "").strip()
    if not raw or len(raw) > 40:
        return []
    out = [raw]
    tokens = [t for t in re.split(r"\s+", raw) if t and t not in STOP_TOKENS]
    stripped = " ".join(tokens).strip(" .,!?~\"'")
    if stripped and norm(stripped) != norm(raw):
        out.append(stripped)
    return out


def find_exact(queries: list, restrict: list, want_missing: bool, missing_artist: str):
    """스토어에서 제목이 같은 곡을 개수 제한 없이 모두 찾습니다.
    restrict가 있으면 그 가수의 곡만 인정합니다."""
    exact_items = []
    partial_items = []
    for q in queries:
        qn = norm(q)
        if not qn:
            continue
        terms = []
        for a in restrict[:2]:
            terms.append(f"{a} {q}")
        terms.append(q)
        rows = []
        for term in terms:
            for country in ("KR", "US"):
                try:
                    rows += itunes_search(term, country, limit=200)
                except Exception:
                    continue

        ex_q, pa_q = [], []
        for r in rows:
            if r.get("kind") != "song":
                continue
            title = (r.get("trackName") or "").strip()
            art = (r.get("artistName") or "").strip()
            if not title or not art:
                continue
            if is_bad_track(title, r.get("collectionName", "")):
                continue
            if restrict and not same_artist(restrict, art):
                continue
            tn = norm(title)
            if not tn:
                continue
            if tn == qn:
                ex_q.append((title, art, q, True))
            elif len(qn) >= 2 and qn in tn:
                pa_q.append((title, art, q, False))
        if ex_q:
            exact_items = ex_q
            break
        partial_items += pa_q

    picks = exact_items if exact_items else partial_items
    found = []
    seen_keys = set()
    for title, art, q, is_exact in picks:
        key = norm(title) + "|" + norm_artist(art)
        if key in seen_keys:
            continue  # 같은 가수의 같은 곡이 앨범별로 여러 번 있으면 한 번만
        seen_keys.add(key)
        found.append({
            "title": title, "title_alt": "", "artist": art, "artist_alt": "",
            "reason": (f"입력하신 {q} 와 제목이 같은 곡입니다." if is_exact
                       else f"제목에 {q} 가 들어 있는 곡입니다."),
            "yt": "", "url": "",
            "tag": "제목이 같은 곡" if is_exact else "제목에 단어 포함",
            "match": True,
        })

    missing = []
    if want_missing and not found and queries:
        q = queries[0]
        missing.append({
            "title": q, "title_alt": "", "artist": missing_artist, "artist_alt": "",
            "reason": "음원 목록에서 찾지 못해 유튜브에서 찾아 드립니다.",
            "yt": "", "url": "", "tag": "입력한 곡", "match": True,
        })
    return found, missing


def verify_song(c: dict):
    """가수 이름이 없을 때 쓰는 확인. 스토어에서 찾은 곡만 통과시킵니다."""
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
                    "title": name, "title_alt": c.get("title_alt", ""),
                    "artist": art, "artist_alt": c.get("artist_alt", ""),
                    "reason": c.get("reason", ""), "yt": "", "url": "", "tag": "", "match": False,
                }
    if had_error and not had_success:
        return "error", None
    return "nomatch", None


def safe_verify(c: dict):
    try:
        return verify_song(c)
    except Exception:
        return "error", None


# ---------- 유튜브 공식 음원 찾기 (키 필요 없음) ----------
# 가수 본인 채널 또는 '가수명 - Topic' 채널의 영상만 고릅니다. MR, 반주, 노래방, 커버, 리믹스는 제외합니다.
BAD_WORDS = [
    "instrumental", "karaoke", "노래방", "반주", "cover", "커버", "remix", "리믹스",
    "reaction", "리액션", "sped up", "slowed", "nightcore", "금영", "tj미디어",
]
BAD_REGEX = re.compile(r"(?<![a-z])(m/?r|inst)(?![a-z])")
NOT_SONG_RE = re.compile(
    r"vlog|브이로그|메이킹|making|teaser|티저|behind|비하인드|interview|인터뷰|shorts|예고|trailer|paper|"
    r"playlist|플레이리스트|full album|풀 앨범|1 hour|1시간",
    re.I,
)


def is_bad_video(video_title: str, song_title: str) -> bool:
    v = (video_title or "").lower()
    s = (song_title or "").lower()
    for kw in BAD_WORDS:
        if kw in v and kw not in s:
            return True
    if BAD_REGEX.search(v) and not BAD_REGEX.search(s):
        return True
    return False


def channel_score(channel: str, artists: list) -> int:
    ch = (channel or "").strip()
    if re.search(r"\s*-\s*topic$", ch, flags=re.I):
        base = re.sub(r"\s*-\s*topic$", "", ch, flags=re.I).strip()
        return 2 if artist_ok(artists, base) else 0
    return 1 if artist_ok(artists, ch) else 0


@st.cache_data(ttl=86400, show_spinner=False)
def yt_search(q: str) -> list:
    """유튜브 검색 결과 페이지를 읽어 영상 목록을 만듭니다."""
    url = "https://www.youtube.com/results?" + urlencode(
        {"search_query": q, "hl": "ko", "gl": "KR"}
    )
    req = Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Cookie": "CONSENT=YES+1; SOCS=CAI",
    })
    with urlopen(req, timeout=8) as r:
        page = r.read().decode("utf-8", errors="ignore")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.DOTALL)
    if not m:
        raise ValueError("no data")
    data = json.loads(m.group(1))

    out = []

    def walk(o):
        if isinstance(o, dict):
            vr = o.get("videoRenderer")
            if isinstance(vr, dict) and vr.get("videoId"):
                title = "".join(x.get("text", "") for x in (vr.get("title") or {}).get("runs", []))
                owner = "".join(x.get("text", "") for x in (vr.get("ownerText") or {}).get("runs", []))
                out.append({"id": vr["videoId"], "title": title, "channel": owner})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    if not out:
        raise ValueError("no videos")
    return out[:15]


def find_official_youtube(song: dict) -> str:
    titles = [song["title"], song.get("title_alt", "")]
    artists = [song["artist"], song.get("artist_alt", "")]
    queries = [
        f"{song['artist']} {song['title']} Provided to YouTube by",
        f"{song['artist']} {song['title']} topic",
        f"{song['artist']} {song['title']} official audio",
    ]
    for q in queries:
        try:
            items = yt_search(q)
        except Exception:
            continue
        best, best_score = "", 0
        for it in items:
            vt = htmllib.unescape(it.get("title", "") or "")
            ch = htmllib.unescape(it.get("channel", "") or "")
            vid = it.get("id")
            if not vid or not vt:
                continue
            if is_bad_video(vt, song["title"]):
                continue
            if not any(t and (norm(t) in norm(vt) or similar(t, vt)) for t in titles):
                continue
            sc = channel_score(ch, artists)
            if sc > best_score:
                best, best_score = vid, sc
        if best:
            return "https://www.youtube.com/watch?v=" + best
    return ""


def safe_find(song: dict) -> str:
    if song.get("url") or song.get("yt"):
        return ""
    try:
        return find_official_youtube(song)
    except Exception:
        return ""


def clean_video_title(video_title: str, artist_names: list) -> str:
    t = htmllib.unescape(video_title or "").strip()
    t = re.sub(
        r"[\(\[\{【](?:[^\)\]\}】]*?)(?:official|audio|lyric|lyrics|mv|m/v|video|가사|뮤직비디오|visualizer)"
        r"(?:[^\)\]\}】]*?)[\)\]\}】]",
        "", t, flags=re.I,
    )
    for n in sorted([x for x in artist_names if x], key=len, reverse=True):
        t = re.sub(r"^\s*" + re.escape(n) + r"\s*[-–—:|]\s*", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -–—|")
    return t or htmllib.unescape(video_title or "").strip()


def artist_youtube_songs(names: list, seen: set, limit: int) -> list:
    """스토어에 가수가 없을 때: 유튜브에서 그 가수 본인 채널/Topic 채널의 영상을 곡으로 보여 줍니다."""
    if not names:
        return []
    main = names[0]
    out = []
    keys = set(seen)
    for q in (f"{main} topic", f"{main} 노래", f"{main} official audio"):
        try:
            items = yt_search(q)
        except Exception:
            continue
        for it in items:
            vt = htmllib.unescape(it.get("title", "") or "")
            ch = htmllib.unescape(it.get("channel", "") or "")
            vid = it.get("id")
            if not vid or not vt:
                continue
            if channel_score(ch, names) == 0:
                continue
            if is_bad_video(vt, "") or NOT_SONG_RE.search(vt):
                continue
            title = clean_video_title(vt, names)
            k = norm(title)
            if not k or k in keys:
                continue
            keys.add(k)
            out.append({
                "title": title, "title_alt": "", "artist": main, "artist_alt": "",
                "reason": f"{main}의 공식 영상입니다.",
                "yt": "https://www.youtube.com/watch?v=" + vid, "url": "", "tag": "", "match": False,
            })
            if len(out) >= limit:
                return out
    return out


# ---------- 추천 ----------
def recommend(user_text: str, count: int, exclude: list) -> dict:
    lines = [l.strip() for l in (user_text or "").replace("\r", "\n").split("\n") if l.strip()]
    if not lines:
        raise ValueError("먼저 마이크로 말하거나 내용을 입력해 주세요.")

    seen = set(norm(x) for x in exclude)
    data = ask_model(lines, min(count + 5, 15), exclude)
    analysis = data["analysis"]

    # 줄마다 가수가 있는 줄(groups)과 없는 줄(plain)로 나눕니다.
    groups = []
    plain = []
    for line, info in zip(lines, data["lines"]):
        artist = info["artist"]
        if artist:
            aliases = uniq([artist] + info["aliases"])
            ids, store_names = resolve_artist(aliases)
            title = info["title"]
            # 스토어에서 가수를 확인했거나, 가수 이름만 쓴 줄만 가수로 인정합니다.
            if ids or not title:
                display = store_names[0] if store_names else artist
                groups.append({
                    "display": display,
                    "names": uniq([display] + aliases + store_names),
                    "ids": ids,
                    "title": title,
                    "mood": info["mood"],
                })
                continue
        plain.append(line)

    # 1) 입력한 제목과 같은 곡을 먼저, 개수 제한 없이 모두 찾습니다 (처음 추천받을 때만)
    first = []
    if not exclude:
        for g in groups:
            if g["title"]:
                found, missing = find_exact([g["title"]], g["names"], True, g["display"])
                first += missing + found
        for line in plain:
            q = build_title_queries(line)
            if q:
                found, _m = find_exact(q, [], False, "")
                first += found
        first = dedupe_songs(first)
        for s in first:
            seen.add(norm(s["title"]))

    # 2) 그다음 가수의 곡 또는 비슷한 느낌의 곡을 찾습니다
    vibe = []
    if groups:
        per = min(count, max(3, -(-count // len(groups))))
        for g in groups:
            cands = [c for c in artist_catalog(g["ids"], g["names"]) if norm(c["title"]) not in seen]
            if cands:
                picked = pick_from_catalog(g["mood"] or "가장 유명한 곡", cands, per)
            else:
                picked = artist_youtube_songs(g["names"], seen, per)
            vibe += picked
        if not vibe and not first:
            if exclude:
                raise ValueError("이 가수의 곡을 더 찾지 못했습니다.")
            for g in groups:
                name = g["display"]
                vibe.append({
                    "title": f"{name} 노래 보기", "title_alt": "", "artist": name, "artist_alt": "",
                    "reason": "곡 목록을 찾지 못해, 유튜브에서 가수 이름으로 검색한 결과를 보여 드립니다.",
                    "yt": "", "url": "https://www.youtube.com/results?search_query=" + quote(name),
                    "tag": "가수 이름으로 검색", "match": False,
                })
        final = dedupe_songs(first + vibe)
    else:
        need = count
        tried = list(exclude)
        checked = 0
        errors = 0
        cands = data["songs"]
        for attempt in range(2):
            if attempt == 1:
                if len(vibe) >= need:
                    break
                try:
                    cands = ask_model(plain, min(need - len(vibe) + 5, 15), tried)["songs"]
                except Exception:
                    break
            if not cands:
                continue
            tried += [c["title"] for c in cands]
            with ThreadPoolExecutor(max_workers=5) as ex:
                results = list(ex.map(safe_verify, cands))
            for status, s in results:
                checked += 1
                if status == "error":
                    errors += 1
                if status != "ok":
                    continue
                k = norm(s["title"])
                if not k or k in seen:
                    continue
                seen.add(k)
                vibe.append(s)
        if not vibe and not first:
            if checked and errors == checked:
                raise RuntimeError("곡 확인에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
            raise ValueError("확인된 곡을 찾지 못했습니다. 조금 다르게 설명해서 다시 시도해 주세요.")
        final = dedupe_songs(first + vibe[:max(need, 1)])

    # 앞쪽 곡만 공식 음원 영상을 찾습니다 (곡이 많으면 느려지기 때문)
    head = final[:YT_LOOKUP_MAX]
    with ThreadPoolExecutor(max_workers=4) as ex:
        urls = list(ex.map(safe_find, head))
    for s, u in zip(head, urls):
        if u:
            s["yt"] = u

    return {"analysis": analysis or {}, "songs": final, "artists": [g["display"] for g in groups][:3]}


# ---------- 표시용 ----------
def youtube_url(song: dict) -> str:
    if song.get("url"):
        return song["url"]
    if song.get("yt"):
        return song["yt"]
    q = f"{song['artist']} {song['title']}"
    return "https://www.youtube.com/results?search_query=" + quote(q)


CAROUSEL_TEMPLATE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.wrap{display:flex;flex-direction:column;height:466px;padding:2px}
.bar{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
.hint{font-size:14px;font-weight:700;line-height:1.35;color:#e6e6ec;cursor:pointer}
.nav{display:flex;gap:6px;flex-shrink:0}
.pill{border:2px solid #fff;background:transparent;color:#fff;font-weight:800;font-size:14px;
  padding:6px 12px;border-radius:999px;cursor:pointer;font-family:inherit}
.pill:hover{background:#26262e}
.rail{flex:1;min-height:0;display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;
  position:relative;padding:4px;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.rail::-webkit-scrollbar{display:none}
.card{flex:0 0 78%;max-width:214px;scroll-snap-align:start;background:#17171c;border-radius:22px;
  border:1px solid #2c2c35;padding:12px;display:flex;flex-direction:column;color:#fff;cursor:pointer;
  box-shadow:0 14px 30px rgba(0,0,0,.65);transition:transform .15s,border-color .15s}
.card:hover{transform:translateY(-4px);border-color:#ffd54a}
.card:focus{outline:4px solid #ffd54a;outline-offset:2px}
.art{position:relative;height:130px;border-radius:16px;overflow:hidden;flex-shrink:0;
  background:linear-gradient(135deg,var(--c1),var(--c2))}
.num{position:absolute;left:12px;top:6px;font-size:42px;font-weight:900;line-height:1;
  color:rgba(255,255,255,.95);text-shadow:0 2px 8px rgba(0,0,0,.35)}
.vinyl{position:absolute;right:-34px;bottom:-34px;width:128px;height:128px;border-radius:50%;
  background:
   conic-gradient(rgba(255,255,255,0) 0 20%,rgba(255,255,255,.2) 25%,rgba(255,255,255,0) 30% 70%,rgba(255,255,255,.2) 75%,rgba(255,255,255,0) 80%),
   repeating-radial-gradient(circle at center,#0b0b10 0 3px,#22222c 3px 5px);
  box-shadow:0 0 0 3px rgba(255,255,255,.14);animation:spin 7s linear infinite}
.vinyl::after{content:"";position:absolute;left:50%;top:50%;width:40px;height:40px;margin:-20px 0 0 -20px;
  border-radius:50%;background:var(--c3);box-shadow:0 0 0 5px rgba(255,255,255,.35)}
@keyframes spin{to{transform:rotate(360deg)}}
.title{margin-top:10px;font-size:18px;font-weight:800;line-height:1.3;word-break:keep-all;color:#fff;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.artist{margin-top:2px;font-size:15px;font-weight:700;color:#ffd54a}
.tag{margin-top:6px;align-self:flex-start;font-size:12.5px;font-weight:800;padding:2px 10px;
  border-radius:999px;border:1.5px solid #ffd54a;color:#ffd54a}
.tag.ok{background:#ffd54a;color:#000}
.reason{margin-top:6px;font-size:13.5px;line-height:1.45;color:#c9c9d1;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.go{display:block;margin-top:auto;background:#ffd54a;color:#000;font-weight:800;font-size:15px;
  text-align:center;padding:9px 6px;border-radius:999px;text-decoration:none}
.go:hover{background:#ffe58a}
.go:focus{outline:4px solid #fff;outline-offset:2px}
button:focus{outline:4px solid #ffd54a;outline-offset:2px}
@media (max-width:480px){.nav{display:none}}
@media (prefers-reduced-motion:reduce){.vinyl{animation:none}.card{transition:none}}
</style></head>
<body>
<div class="wrap">
  <div class="bar">
    <div class="hint" id="hint">글을 누르면 읽어 주고, 노란 버튼을 누르면 유튜브가 열려요 (총 __TOTAL__곡)</div>
    <div class="nav">
      <button class="pill" id="prev" type="button">이전 곡</button>
      <button class="pill" id="next" type="button">다음 곡</button>
    </div>
  </div>
  <div class="rail" id="rail" role="region" aria-label="추천 노래 목록">__CARDS__</div>
</div>
<script>
  __INSTALL__
  function getS() { try { return window.parent.__mcSpeech || null; } catch (e) { return null; } }
  function isOn() { var s = getS(); return s ? s.isOn() : true; }
  function speak(t) {
    var s = getS();
    if (s) { s.speak(t); return; }
    try { speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(t); u.lang = 'ko-KR'; speechSynthesis.speak(u); } catch (e) {}
  }

  var START = __START__;
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

  document.getElementById('hint').onclick = function() { speak(this.innerText); };

  var cards = rail.querySelectorAll('.card');
  cards.forEach(function(c) {
    function act() {
      if (isOn()) {
        speak(c.getAttribute('data-speak'));
      } else {
        window.open(c.getAttribute('data-url'), '_blank', 'noopener');
      }
    }
    c.addEventListener('click', function(e) {
      if (e.target.closest('.go')) { return; }
      act();
    });
    c.addEventListener('keydown', function(e) {
      if ((e.key === 'Enter' || e.key === ' ') && e.target === c) {
        e.preventDefault();
        act();
      }
    });
  });
  if (START > 0 && cards[START]) { rail.scrollLeft = cards[START].offsetLeft - 4; }
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
        if s.get("tag"):
            tag_text = s["tag"]
            tag_cls = "tag ok" if s.get("match") else "tag"
        elif s.get("yt"):
            tag_text, tag_cls = "가수 공식 음원", "tag ok"
        else:
            tag_text, tag_cls = "유튜브에서 찾기", "tag"
        url = youtube_url(s)
        speak_text = f"{i}번. {s['artist']}의 {s['title']}. {tag_text}."
        if s.get("reason"):
            speak_text += " " + s["reason"]
        label = f"{i}번 곡. {s['title']}, {s['artist']}. 누르면 곡 설명을 읽어 줍니다."
        out.append(
            f'<div class="card" tabindex="0" role="button" aria-label="{esc(label)}" '
            f'data-url="{esc(url)}" data-speak="{esc(speak_text)}" '
            f'style="--c1:{c1};--c2:{c2};--c3:{c3}">'
            f'<div class="art"><span class="num">{i}</span><div class="vinyl"></div></div>'
            f'<div class="title">{esc(s["title"])}</div>'
            f'<div class="artist">{esc(s["artist"])}</div>'
            f'<div class="{tag_cls}">{esc(tag_text)}</div>'
            f'<div class="reason">{esc(s["reason"])}</div>'
            f'<a class="go" href="{esc(url)}" target="_blank" rel="noopener noreferrer" '
            f'aria-label="{i}번 곡 유튜브에서 듣기">유튜브에서 듣기</a>'
            '</div>'
        )
    return "".join(out)


def render_carousel(result: dict, start: int):
    page = (CAROUSEL_TEMPLATE
            .replace("__START__", str(int(start)))
            .replace("__TOTAL__", str(len(result["songs"])))
            .replace("__CARDS__", cards_html(result["songs"]))
            .replace("__INSTALL__", install_js()))
    components.html(page, height=476, scrolling=False)


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
            if not st.session_state.result.get("artists"):
                st.session_state.result["artists"] = res.get("artists", [])
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
    render_toggle()
    st.markdown(
        '<div class="hero"><div class="disc" aria-hidden="true"></div>'
        '<h1 class="brand">음악 나침반</h1>'
        '<div class="sub">듣고 싶은 노래를 말하거나 써 주세요</div></div>',
        unsafe_allow_html=True,
    )

    # 사용 방법: 정보 아이콘에 마우스를 올리면 설명이 보입니다
    st.markdown(info_html(), unsafe_allow_html=True)

    if not get_api_key():
        st.warning("GEMINI_API_KEY가 설정되지 않았습니다. 배포 설정의 Secrets에 키를 등록해 주세요.")
    if st.session_state.error:
        st.error(st.session_state.error)

    audio = None
    if hasattr(st, "audio_input"):
        try:
            audio = st.audio_input("마이크로 말하기 (눌러서 말하고, 끝나면 다시 눌러 주세요)")
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
                    st.session_state.user_text = (old + "\n" + text).strip() if old else text
                    st.success("말씀하신 내용이 아래 내용창에 써졌습니다. 고칠 수 있어요.")
                else:
                    st.warning("말소리를 알아듣지 못했습니다. 다시 말씀해 주세요.")
        except Exception as e:
            st.error(friendly_error(e))

    st.text_area(
        "내용 (가수를 여러 명 쓸 때는 Enter로 줄을 나눠 주세요)",
        key="user_text",
        height=150,
        placeholder="예: 아이유 좋은날\n좋은날 아이유\n가수 여러 명은 Enter로 줄을 나눠요",
    )

    st.button("추천받기", type="primary", on_click=set_pending, args=("new",))


# ---------- 추천 곡 화면 ----------
def render_result():
    result = st.session_state.result
    if not result or not result.get("songs"):
        st.session_state.page = "home"
        render_home()
        return

    render_toggle()

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
        st.button("다른 곡 더 추천받기", on_click=set_pending, args=("more",))
    with b2:
        st.button("처음부터 다시 입력하기", on_click=go_home)

    artists = result.get("artists") or []
    if artists:
        cols = st.columns(min(len(artists), 3))
        for i, name in enumerate(artists[:3]):
            with cols[i]:
                st.link_button(
                    f"{name} 유튜브에서 보기",
                    "https://www.youtube.com/results?search_query=" + quote(name),
                )


if st.session_state.page == "result":
    render_result()
else:
    render_home()
