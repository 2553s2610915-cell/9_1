import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="VALORANT Style PK Audio Soccer",
    page_icon="⚽",
    layout="wide"
)

# Custom CSS - Streamlit 기본 여백 제거
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #ffffff;
        padding: 0rem;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

game_html = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * {
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
        }
        body {
            margin: 0;
            padding: 0;
            background: radial-gradient(circle at center, #1b2735 0%, #090a0f 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow: hidden;
        }

        /* 발로란트 스타일 상단 바 */
        .valo-navbar {
            width: 100%;
            height: 50px;
            background: rgba(15, 23, 36, 0.85);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 30px;
            position: absolute;
            top: 0;
            z-index: 10;
        }
        .valo-logo {
            font-size: 1.2rem;
            font-weight: 900;
            letter-spacing: 2px;
            color: #ff4655;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .valo-nav-items {
            display: flex;
            gap: 25px;
            font-size: 0.85rem;
            font-weight: bold;
            color: #8b9bb4;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .valo-nav-item.active {
            color: #ece8e1;
            border-bottom: 2px solid #ff4655;
            padding-bottom: 12px;
        }

        #bgm-toggle-btn {
            background: rgba(255, 70, 85, 0.2);
            border: 1px solid #ff4655;
            color: #fff;
            padding: 6px 14px;
            font-size: 0.8rem;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: 0.2s;
        }
        #bgm-toggle-btn:hover {
            background: #ff4655;
        }

        /* 메인 대기실 카드 레이아웃 */
        #lobby-container {
            width: 90%;
            max-width: 950px;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 60px;
        }

        .cards-wrapper {
            display: flex;
            justify-content: center;
            gap: 15px;
            width: 100%;
            margin: 20px 0;
        }

        .valo-card {
            width: 170px;
            height: 320px;
            background: rgba(20, 30, 48, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 15px;
            position: relative;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            cursor: pointer;
            backdrop-filter: blur(5px);
        }

        .valo-card:hover, .valo-card.selected {
            transform: translateY(-10px) scale(1.03);
            border-color: #00f2fe;
            box-shadow: 0 0 20px rgba(0, 242, 254, 0.4);
            background: rgba(20, 35, 60, 0.85);
        }

        .valo-card.selected::before {
            content: "SELECTED";
            position: absolute;
            top: -12px;
            background: #00f2fe;
            color: #000;
            font-size: 0.65rem;
            font-weight: 900;
            padding: 2px 8px;
            border-radius: 3px;
        }

        .card-img-placeholder {
            width: 100%;
            height: 180px;
            background: linear-gradient(180deg, #1f2d40 0%, #0d1520 100%);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
        }

        .card-title {
            font-size: 1rem;
            font-weight: bold;
            color: #fff;
            text-align: center;
            margin-top: 8px;
        }
        .card-sub {
            font-size: 0.75rem;
            color: #8b9bb4;
            text-align: center;
        }

        /* 게임 실행 버튼 영역 */
        #play-start-btn {
            width: 280px;
            padding: 16px;
            font-size: 1.2rem;
            font-weight: 900;
            letter-spacing: 2px;
            color: #000;
            background: #00f2fe;
            border: none;
            clip-path: polygon(10px 0, 100% 0, calc(100% - 10px) 100%, 0 100%);
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 15px;
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.5);
        }

        #play-start-btn:hover {
            background: #ff4655;
            color: #fff;
            box-shadow: 0 0 20px rgba(255, 70, 85, 0.7);
        }

        /* 인게임 캔버스 영역 */
        #game-screen {
            display: none;
            flex-direction: column;
            align-items: center;
            width: 100%;
            max-width: 500px;
        }

        .stats-bar {
            width: 100%;
            display: flex;
            justify-content: space-between;
            font-size: 1.1rem;
            font-weight: bold;
            background: rgba(15, 23, 36, 0.9);
            padding: 8px 15px;
            border-radius: 8px;
            border: 1px solid #30363d;
            margin-bottom: 10px;
        }
        .score { color: #00f2fe; }
        .heart { color: #ff4655; }

        canvas {
            width: 100%;
            height: 410px;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(0,0,0,0.8);
        }

        #back-to-lobby-btn {
            margin-top: 10px;
            background: rgba(255,255,255,0.1);
            border: 1px solid #8b9bb4;
            color: #fff;
            padding: 8px 20px;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
</head>
<body>

<!-- 발로란트 상단 네비게이션 -->
<div class="valo-navbar">
    <div class="valo-logo">⚽ AUDIO SOCCER</div>
    <div class="valo-nav-items">
        <span class="valo-nav-item active">시작하기</span>
        <span class="valo-nav-item">경쟁전</span>
        <span class="valo-nav-item">스파이크 돌격</span>
        <span class="valo-nav-item">데스매치</span>
    </div>
    <button id="bgm-toggle-btn" onclick="toggleBGM()">🎵 Royal 44 BGM: ON</button>
</div>

<!-- 발로란트 대기실 로비 화면 -->
<div id="lobby-container">
    <div style="font-size: 0.85rem; color: #00f2fe; letter-spacing: 2px; margin-bottom: 5px;">SELECT GAME MODE</div>
    <div style="font-size: 1.8rem; font-weight: 900; letter-spacing: 1px; margin-bottom: 15px;">시작하기 (PLAY)</div>

    <div class="cards-wrapper">
        <div class="valo-card">
            <div class="card-img-placeholder">🎯</div>
            <div>
                <div class="card-title">기본 연습</div>
                <div class="card-sub">기본 슛 타격</div>
            </div>
        </div>
        <div class="valo-card">
            <div class="card-img-placeholder">🔥</div>
            <div>
                <div class="card-title">경쟁전</div>
                <div class="card-sub">랭크 매치</div>
            </div>
        </div>
        <div class="valo-card selected">
            <div class="card-img-placeholder">⚽</div>
            <div>
                <div class="card-title">지역 점령</div>
                <div class="card-sub">PK 오디오 모드</div>
            </div>
        </div>
        <div class="valo-card">
            <div class="card-img-placeholder">⚡</div>
            <div>
                <div class="card-title">데스매치</div>
                <div class="card-sub">무한 슈팅</div>
            </div>
        </div>
        <div class="valo-card">
            <div class="card-img-placeholder">🏆</div>
            <div>
                <div class="card-title">사용자 지정</div>
                <div class="card-sub">커스텀 게임</div>
            </div>
        </div>
    </div>

    <button id="play-start-btn" onclick="launchGame()">대기열 시작</button>
</div>

<!-- 인게임 화면 -->
<div id="game-screen">
    <div class="stats-bar">
        <div>점수: <span id="score-val" class="score">0</span></div>
        <div>라이프: <span id="lives-val" class="heart">❤️❤️❤️</span></div>
    </div>

    <canvas id="gameCanvas" width="480" height="410"></canvas>
    <button id="back-to-lobby-btn" onclick="returnToLobby()">🔙 로비로 돌아가기</button>
</div>

<script>
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    
    let audioCtx = null;
    let isPlaying = false;
    let isBgmOn = true;
    let bgmInterval = null;
    let score = 0;
    let lives = 3;
    
    let ball = null; 
    let keeperPos = { x: 240, y: 115, targetX: 240, isDiving: false, diveSide: 'none' };
    let animationFrameId = null;
    let feedbackText = "";
    let feedbackColor = "";
    let feedbackTimer = 0;
    let voicedNow = false;

    function initAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    /* 🎵 래퍼 로얄44 (Royal 44) 스타일 808 비트 & 힙합 BGM 루프 */
    function startRoyal44BGM() {
        if (!isBgmOn) return;
        initAudio();

        let step = 0;
        // 808 트랩 / 몽환적인 싱잉 비트 노트 스케일
        const notes = [130.81, 146.83, 164.81, 196.00, 220.00];

        if (bgmInterval) clearInterval(bgmInterval);

        bgmInterval = setInterval(() => {
            if (!isBgmOn || !audioCtx) return;

            const time = audioCtx.currentTime;

            // 1. 808 딥 베이스 (드롭)
            if (step % 4 === 0) {
                const bOsc = audioCtx.createOscillator();
                const bGain = audioCtx.createGain();
                bOsc.type = 'sine';
                bOsc.frequency.setValueAtTime(65, time);
                bOsc.frequency.exponentialRampToValueAtTime(32, time + 0.35);

                bGain.gain.setValueAtTime(0.3, time);
                bGain.gain.exponentialRampToValueAtTime(0.01, time + 0.35);

                bOsc.connect(bGain);
                bGain.connect(audioCtx.destination);
                bOsc.start(time);
                bOsc.stop(time + 0.35);
            }

            // 2. 몽환적인 트랩 신스 멜로디 (로얄44 스타일)
            if (step % 2 === 0) {
                const mOsc = audioCtx.createOscillator();
                const mGain = audioCtx.createGain();
                mOsc.type = 'triangle';

                const freq = notes[(step * 3) % notes.length];
                mOsc.frequency.setValueAtTime(freq, time);

                mGain.gain.setValueAtTime(0.08, time);
                mGain.gain.linearRampToValueAtTime(0.01, time + 0.25);

                mOsc.connect(mGain);
                mGain.connect(audioCtx.destination);
                mOsc.start(time);
                mOsc.stop(time + 0.25);
            }

            // 3. 하이햇 (트랩 스네어)
            if (step % 2 === 1) {
                const hBuf = audioCtx.createBuffer(1, audioCtx.sampleRate * 0.05, audioCtx.sampleRate);
                const hData = hBuf.getChannelData(0);
                for (let i = 0; i < hBuf.length; i++) hData[i] = Math.random() * 2 - 1;

                const hNode = audioCtx.createBufferSource();
                hNode.buffer = hBuf;

                const hFilter = audioCtx.createBiquadFilter();
                hFilter.type = 'highpass';
                hFilter.frequency.value = 7000;

                const hGain = audioCtx.createGain();
                hGain.gain.setValueAtTime(0.05, time);
                hGain.gain.linearRampToValueAtTime(0.01, time + 0.05);

                hNode.connect(hFilter);
                hFilter.connect(hGain);
                hGain.connect(audioCtx.destination);
                hNode.start(time);
            }

            step = (step + 1) % 16;
        }, 180);
    }

    function toggleBGM() {
        isBgmOn = !isBgmOn;
        const btn = document.getElementById('bgm-toggle-btn');
        if (isBgmOn) {
            btn.innerText = "🎵 Royal 44 BGM: ON";
            btn.style.background = "rgba(255, 70, 85, 0.2)";
            startRoyal44BGM();
        } else {
            btn.innerText = "🔇 Royal 44 BGM: OFF";
            btn.style.background = "rgba(255, 255, 255, 0.1)";
            if (bgmInterval) clearInterval(bgmInterval);
        }
    }

    function speak(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.25;
            window.speechSynthesis.speak(utterance);
        }
    }

    function playSoccerSound(side, duration) {
        if (!audioCtx) return;

        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        const panner = audioCtx.createStereoPanner();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(140, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(360, audioCtx.currentTime + duration);

        const panVal = (side === 'left') ? -0.95 : 0.95;
        panner.pan.setValueAtTime(panVal, audioCtx.currentTime);

        gainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.8, audioCtx.currentTime + duration - 0.05);
        gainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + duration);

        osc.connect(gainNode);
        gainNode.connect(panner);
        panner.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    }

    function playCheerCrowdSound() {
        if (!audioCtx) return;
        const bufferSize = audioCtx.sampleRate * 1.5;
        const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;

        const noise = audioCtx.createBufferSource();
        noise.buffer = buffer;

        const filter = audioCtx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(850, audioCtx.currentTime);

        const gain = audioCtx.createGain();
        gain.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.5, audioCtx.currentTime + 0.3);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 1.5);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(audioCtx.destination);

        noise.start();
        noise.stop(audioCtx.currentTime + 1.5);
    }

    function playBooingCrowdSound() {
        if (!audioCtx) return;
        const osc1 = audioCtx.createOscillator();
        const osc2 = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc1.type = 'sawtooth';
        osc2.type = 'sine';
        osc1.frequency.setValueAtTime(110, audioCtx.currentTime);
        osc2.frequency.setValueAtTime(115, audioCtx.currentTime);

        gain.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.4, audioCtx.currentTime + 0.2);
        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 1.2);

        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(audioCtx.destination);

        osc1.start();
        osc2.start();
        osc1.stop(audioCtx.currentTime + 1.2);
        osc2.stop(audioCtx.currentTime + 1.2);
    }

    function drawStadium() {
        ctx.fillStyle = '#cfd8dc';
        ctx.fillRect(0, 0, canvas.width, 160);

        const colors = ['#b71c1c', '#0d47a1', '#ffffff', '#37474f', '#880e4f'];
        for (let i = 0; i < 220; i++) {
            let rx = (i * 13) % canvas.width;
            let ry = (i * 7) % 95;
            ctx.fillStyle = colors[i % colors.length];
            ctx.fillRect(rx, ry, 6, 8);
            ctx.fillStyle = '#ffcc80';
            ctx.fillRect(rx + 1, ry - 3, 4, 3);
        }

        ctx.fillStyle = '#111';
        ctx.fillRect(0, 95, canvas.width, 25);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('VALORANT • ROYAL 44 AUDIO SOCCER ⚽', canvas.width / 2, 112);

        ctx.strokeStyle = '#f5f5f5';
        ctx.lineWidth = 5;
        ctx.strokeRect(40, 35, 400, 110);

        ctx.strokeStyle = 'rgba(200, 200, 200, 0.4)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 52; x < 440; x += 12) {
            ctx.moveTo(x, 35);
            ctx.lineTo(x, 145);
        }
        for (let y = 45; y < 145; y += 10) {
            ctx.moveTo(40, y);
            ctx.lineTo(440, y);
        }
        ctx.stroke();

        let pitchGrad = ctx.createLinearGradient(0, 140, 0, canvas.height);
        pitchGrad.addColorStop(0, '#558b2f');
        pitchGrad.addColorStop(0.3, '#33691e');
        pitchGrad.addColorStop(1, '#1b5e20');
        ctx.fillStyle = pitchGrad;
        ctx.fillRect(0, 140, canvas.width, canvas.height - 140);

        drawKeeper();
        drawKicker();
    }

    function drawKeeper() {
        let x = keeperPos.x;
        let y = keeperPos.y;

        ctx.save();
        ctx.translate(x, y);

        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.beginPath();
        ctx.ellipse(0, 28, 16, 5, 0, 0, Math.PI * 2);
        ctx.fill();

        if (keeperPos.isDiving) {
            let dir = keeperPos.diveSide === 'left' ? -1 : 1;
            ctx.rotate(dir * 0.8);
            ctx.fillStyle = '#1b1b1b';
            ctx.fillRect(-8, -15, 16, 26);
            ctx.fillStyle = '#ffcc80';
            ctx.beginPath();
            ctx.arc(0, -22, 6, 0, Math.PI * 2);
            ctx.fill();
        } else {
            ctx.fillStyle = '#ffcc80';
            ctx.beginPath();
            ctx.arc(0, -22, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#1b1b1b';
            ctx.fillRect(-10, -16, 20, 24);
        }

        ctx.restore();
    }

    function drawKicker() {
        ctx.save();
        ctx.translate(330, 325);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(-12, 0, 24, 26);
        ctx.fillStyle = '#263238';
        ctx.font = '900 8px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('BALE', 0, 8);
        ctx.fillText('32', 0, 21);
        ctx.restore();
    }

    function drawGaugeBar(progress) {
        let barWidth = 260;
        let barHeight = 16;
        let startX = (canvas.width - barWidth) / 2;
        let startY = 375;

        ctx.fillStyle = '#161b22';
        ctx.fillRect(startX - 2, startY - 2, barWidth + 4, barHeight + 4);

        let gGrad = ctx.createLinearGradient(startX, 0, startX + barWidth, 0);
        gGrad.addColorStop(0, '#ff4655');
        gGrad.addColorStop(0.7, '#00f2fe');
        gGrad.addColorStop(1, '#ff4655');
        
        ctx.fillStyle = gGrad;
        ctx.fillRect(startX, startY, barWidth, barHeight);

        if (progress > 0 && progress <= 1.0) {
            let posX = startX + (barWidth * progress);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(posX - 2, startY - 4, 4, barHeight + 8);
        }
    }

    function drawScene() {
        drawStadium();

        let currentProgress = 0;

        if (ball && ball.active) {
            currentProgress = ball.progress;

            ctx.save();
            ctx.beginPath();
            ctx.arc(ball.currentX, ball.currentY, ball.size, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.restore();
        } else {
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(240, 318, 6, 0, Math.PI * 2);
            ctx.fill();
        }

        drawGaugeBar(currentProgress);

        if (feedbackTimer > 0) {
            ctx.font = '900 26px sans-serif';
            ctx.fillStyle = feedbackColor;
            ctx.textAlign = 'center';
            ctx.fillText(feedbackText, canvas.width / 2, 225);
            feedbackTimer--;
        }
    }

    function spawnBall() {
        if (!isPlaying) return;

        const side = Math.random() < 0.5 ? 'left' : 'right';
        const duration = Math.max(1.1, 2.0 - (score * 0.04));

        let startX = 240;
        let startY = 318;
        let endX = side === 'left' ? 100 : 380;
        let endY = 80;

        let willSave = Math.random() < (0.25 + score * 0.001);

        keeperPos = {
            x: 240,
            y: 115,
            targetX: willSave ? endX : 240,
            isDiving: false,
            diveSide: side
        };

        voicedNow = false;

        ball = {
            startX: startX,
            startY: startY,
            endX: endX,
            endY: endY,
            currentX: startX,
            currentY: startY,
            size: 6,
            progress: 0,
            duration: duration,
            side: side,
            willSave: willSave,
            active: true,
            hit: false,
            startTime: performance.now()
        };

        playSoccerSound(side, duration);
    }

    function gameLoop(timestamp) {
        if (isPlaying && ball && ball.active) {
            let elapsed = (timestamp - ball.startTime) / 1000;
            ball.progress = elapsed / ball.duration;

            if (ball.progress >= 0.65 && !voicedNow) {
                voicedNow = true;
                speak("지금 터치하세요!");
            }

            if (ball.willSave && ball.progress > 0.4) {
                keeperPos.x += (keeperPos.targetX - keeperPos.x) * 0.16;
                keeperPos.isDiving = true;
            }

            if (ball.progress <= 1.0) {
                ball.currentX = ball.startX + (ball.endX - ball.startX) * ball.progress;
                ball.currentY = ball.startY + (ball.endY - ball.startX) * ball.progress;
                ball.size = 6 + (ball.progress * 12);
            } else if (!ball.hit) {
                ball.active = false;
                handleMiss("놓침!");
            }
        }

        drawScene();

        if (isPlaying) {
            animationFrameId = requestAnimationFrame(gameLoop);
        }
    }

    function handleTouch(e) {
        if (e) e.preventDefault();
        if (!isPlaying || !ball || !ball.active || ball.hit) return;

        ball.hit = true;
        ball.active = false;

        // 🔥 키퍼가 막으면 라이프 차감 없음
        if (ball.willSave && ball.progress > 0.6) {
            setFeedback("SAVED BY KEEPER! 🧤 (노 차감)", "#38bdf8");
            playBooingCrowdSound();
            updateUI();
            setTimeout(spawnBall, 1600);
            return;
        }

        let diff = Math.abs(0.85 - ball.progress);

        if (diff <= 0.15) {
            score += 100;
            setFeedback("GOAL! PERFECT! ⚽", "#00f2fe");
            playCheerCrowdSound();
            setTimeout(spawnBall, 1600);
        } else if (diff <= 0.32) {
            score += 50;
            setFeedback("GOAL! GOOD! 👍", "#e3b341");
            playCheerCrowdSound();
            setTimeout(spawnBall, 1600);
        } else {
            handleMiss("타이밍 미스!");
        }

        updateUI();
    }

    function handleMiss(reason) {
        lives--;
        setFeedback("TIMING MISS! ❌", "#ff4655");
        playBooingCrowdSound();
        updateUI();

        if (lives <= 0) {
            gameOver();
        } else {
            setTimeout(spawnBall, 1600);
        }
    }

    function setFeedback(text, color) {
        feedbackText = text;
        feedbackColor = color;
        feedbackTimer = 45;
    }

    function updateUI() {
        document.getElementById('score-val').innerText = score;
        let hearts = '';
        for (let i = 0; i < lives; i++) hearts += '❤️';
        document.getElementById('lives-val').innerText = hearts || '💀';
    }

    function launchGame() {
        initAudio();
        if (isBgmOn) startRoyal44BGM();

        document.getElementById('lobby-container').style.display = 'none';
        document.getElementById('game-screen').style.display = 'flex';

        isPlaying = true;
        score = 0;
        lives = 3;
        ball = null;
        updateUI();

        speak("게임 시작! 소리를 듣고 골을 성공시키세요.");

        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        animationFrameId = requestAnimationFrame(gameLoop);

        setTimeout(spawnBall, 1800);
    }

    function returnToLobby() {
        isPlaying = false;
        document.getElementById('game-screen').style.display = 'none';
        document.getElementById('lobby-container').style.display = 'flex';
    }

    function gameOver() {
        isPlaying = false;
        speak("게임 오버. 최종 점수는 " + score + "점입니다.");
        setTimeout(() => {
            alert("게임 오버! 최종 점수: " + score + "점");
            returnToLobby();
        }, 1000);
    }

    canvas.addEventListener('touchstart', handleTouch, { passive: false });
    canvas.addEventListener('mousedown', handleTouch);
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' || e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
            handleTouch();
        }
    });

    // 시작 시 BGM 구동
    window.addEventListener('click', () => {
        initAudio();
        if (isBgmOn && !bgmInterval) startRoyal44BGM();
    }, { once: true });
</script>
</body>
</html>
"""

components.html(game_html, height=620)
