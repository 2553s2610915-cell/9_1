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

    st.markdown(
        '<div style="background:#20202a;border:1px solid #555563;border-radius:16px;'
        'padding:14px 18px;margin:18px 0 8px 0;">'
        '<div style="font-size:1.12rem;font-weight:800;color:#ffd54a;">🎙️ 마이크로 취향 말하기</div>'
        '<div style="font-size:0.98rem;line-height:1.6;color:#f0f0f4;margin-top:5px;">'
        '흰색 마이크 버튼을 누르고 원하는 가수, 노래 제목 또는 음악 분위기를 말해 주세요. '
        '말하기를 마치면 다시 눌러 주세요.</div></div>',
        unsafe_allow_html=True,
    )

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
        "✍️ 입력된 내용 확인 및 수정",
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
