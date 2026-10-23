import streamlit as st

st.set_page_config(
    page_title="소리눈 | 실시간 장애물 감지",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #101820;
        color: #F4F7FA;
    }
    h1, h2, h3, p, label {
        color: #F4F7FA !important;
    }
    .hero {
        background: linear-gradient(135deg, #183B4E, #145A50);
        padding: 24px;
        border-radius: 18px;
        border: 1px solid #34776E;
        margin-bottom: 18px;
    }
    .hero h1 {
        font-size: 2.1rem;
        margin: 0 0 8px 0;
    }
    .hero p {
        font-size: 1.05rem;
        margin: 0;
    }
    .notice {
        background: #292B20;
        border-left: 5px solid #F4C95D;
        padding: 14px 16px;
        border-radius: 8px;
        margin: 12px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>🔊 소리눈</h1>
        <p>카메라로 주변을 살피고, 음성으로 전방의 물체를 알려주는 보행 보조 시제품</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### 사용 방법")
st.markdown(
    """
    1. 아래 화면에서 **감지 시작**을 누르고 카메라 사용을 허용합니다.
    2. 카메라를 전방으로 향하게 합니다.
    3. 감지된 물체가 화면 중앙에 있거나 크게 보이면 음성 안내를 확인합니다.
    4. 이동을 멈추거나 사용을 마치면 **감지 정지**를 누릅니다.
    """
)

st.markdown(
    """
    <div class="notice">
    <strong>안전 안내</strong><br>
    물체의 크기는 실제 거리와 같지 않습니다. 이 앱은 실제 충돌 거리나
    안전한 보행 경로를 보장하지 않습니다. 보행 중에는 지팡이·안내견 등
    기존 보조 수단을 계속 사용하고, 주변을 직접 확인하세요.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### 실시간 카메라")

app_html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js"></script>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 12px;
  background: #101820;
  color: #f4f7fa;
  font-family: Arial, sans-serif;
}
button, select {
  min-height: 50px;
  font-size: 17px;
  font-weight: bold;
  border-radius: 10px;
  padding: 10px 15px;
}
button {
  border: 2px solid transparent;
  cursor: pointer;
}
button:focus, select:focus {
  outline: 3px solid #f4c95d;
  outline-offset: 3px;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
#start { background: #42d6a4; color: #09251c; }
#stop { background: #ffcf70; color: #332300; }
#voice { background: #d9e8ff; color: #102a43; }
#status {
  padding: 14px;
  border-radius: 10px;
  background: #263746;
  font-size: 19px;
  font-weight: bold;
  margin-bottom: 12px;
  line-height: 1.5;
}
#videoWrap {
  width: 100%;
  max-width: 760px;
  margin: auto;
  position: relative;
  background: #05090d;
  border-radius: 14px;
  overflow: hidden;
  border: 2px solid #536575;
  min-height: 220px;
}
video, canvas {
  width: 100%;
  height: auto;
  display: block;
}
video {
  transform: scaleX(-1);
}
canvas {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
}
#log {
  background: #1c2a35;
  border-radius: 10px;
  padding: 14px;
  margin-top: 12px;
  min-height: 60px;
  font-size: 16px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.small {
  color: #c8d5df;
  font-size: 14px;
  line-height: 1.6;
}
</style>
</head>
<body>
<div class="controls">
  <button id="start">감지 시작</button>
  <button id="stop" disabled>감지 정지</button>
  <button id="voice" aria-pressed="true">음성 안내: 켜짐</button>
</div>

<div id="status" role="status" aria-live="polite">
  준비 완료. '감지 시작' 버튼을 누르세요.
</div>

<div id="videoWrap">
  <video id="video" autoplay playsinline muted></video>
  <canvas id="canvas"></canvas>
</div>

<div id="log" role="status" aria-live="polite">
  감지를 시작하면 물체 감지 결과가 여기에 표시됩니다.
</div>

<p class="small">
  AI 모델: COCO-SSD · 브라우저 내 분석<br>
  물체 크기는 대략적인 시각적 단서일 뿐 실제 거리 측정값이 아닙니다.
</p>

<script>
window.addEventListener("load", () => {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  const startBtn = document.getElementById("start");
  const stopBtn = document.getElementById("stop");
  const voiceBtn = document.getElementById("voice");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log");

  let model = null;
  let stream = null;
  let running = false;
  let busy = false;
  let voiceEnabled = true;
  let lastSpoken = "";
  let lastSpokenAt = 0;
  let lastDetectionAt = 0;
  let animationId = null;
  let generation = 0;

  const labels = {
    person: "사람",
    bicycle: "자전거",
    car: "자동차",
    motorcycle: "오토바이",
    bus: "버스",
    truck: "트럭",
    chair: "의자",
    bench: "벤치",
    suitcase: "여행 가방",
    dog: "개",
    potted plant: "화분",
    dining table: "탁자",
    couch: "소파",
    skateboard: "스케이트보드"
  };

  function setStatus(message) {
    statusEl.textContent = message;
  }

  function speak(message, force = false) {
    if (!voiceEnabled || !("speechSynthesis" in window)) return;

    const now = Date.now();
    if (!force && message === lastSpoken && now - lastSpokenAt < 5000) return;
    if (!force && now - lastSpokenAt < 3500) return;

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.lang = "ko-KR";
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      const voices = window.speechSynthesis.getVoices();
      const koreanVoice = voices.find(v => v.lang.toLowerCase().startsWith("ko"));
      if (koreanVoice) utterance.voice = koreanVoice;

      window.speechSynthesis.speak(utterance);
      lastSpoken = message;
      lastSpokenAt = now;
    } catch (error) {
      logEl.textContent = "음성 안내 오류: " + error.message;
    }
  }

  function stopCamera() {
    running = false;
    generation++;

    if (animationId !== null) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }

    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }

    video.srcObject = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    startBtn.disabled = false;
    stopBtn.disabled = true;
    setStatus("감지가 정지되었습니다.");
    logEl.textContent = "카메라가 종료되었습니다.";

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  async function loadModel() {
    if (model) return model;

    setStatus("AI 모델을 불러오는 중입니다...");

    if (!window.tf || !window.cocoSsd) {
      throw new Error("TensorFlow.js 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인하세요.");
    }

    await window.tf.ready();
    model = await window.cocoSsd.load();
    return model;
  }

  function getDescription(prediction) {
    const name = labels[prediction.class] || prediction.class;
    const [x, y, width, height] = prediction.bbox;
    const videoWidth = video.videoWidth || 1;
    const videoHeight = video.videoHeight || 1;

    const centerX = (x + width / 2) / videoWidth;
    const areaRatio = (width * height) / (videoWidth * videoHeight);

    let direction = "전방";
    if (centerX < 0.35) direction = "왼쪽 전방";
    else if (centerX > 0.65) direction = "오른쪽 전방";

    const visuallyLarge = areaRatio > 0.16;
    const centrallyLocated = centerX >= 0.25 && centerX <= 0.75;

    return { name, direction, visuallyLarge, centrallyLocated };
  }

  async function
