import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="오징어 게임 PK 오디오 축구",
    page_icon="⚽",
    layout="wide"
)

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
        }

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
            backdrop-filter: blur(5px);
        }

        .valo-card.selected {
            border-color: #ff4655;
            box-shadow: 0 0 20px rgba(255, 70, 85, 0.4);
            background: rgba(35, 20, 30, 0.85);
        }

        .card-img-placeholder {
            width: 100%;
            height: 180px;
            background: linear-gradient(180deg, #2d1f27 0%, #150d14 100%);
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
        }
        .card-sub {
            font-size: 0.75rem;
            color: #8b9bb4;
            text-align: center;
        }

        #play-start-btn {
            width: 280px;
            padding: 16px;
            font-size: 1.2rem;
            font-weight: 900;
            color: #fff;
            background: #ff4655;
            border: none;
            clip-path: polygon(10px 0, 100% 0, calc(100% - 10px) 100%, 0 100%);
            cursor: pointer;
            box-shadow: 0 0 15px rgba(255, 70, 85, 0.5);
        }

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

<div class="valo-navbar">
    <div class="valo-logo">🦑 SQUID GAME AUDIO SOCCER</div>
    <button id="bgm-toggle-btn" onclick="toggleBGM()">🎵 Royal 44 BGM: ON</button>
</div>

<div id="lobby-container">
    <div style="font-size: 0.85rem; color: #ff4655; letter-spacing: 2px; margin-bottom: 5px;">SQUID GAME EDITION</div>
    <div style="font-size: 1.8rem; font-weight: 900; letter-spacing: 1px; margin-bottom: 15px;">게임 시작 (PLAY)</div>

    <div class="cards-wrapper">
        <div class="valo-card selected">
            <div class="card-img-placeholder">🦑</div>
            <div>
                <div class="card-title">영희 VS 분홍 가드</div>
                <div class="card-sub">500점당 속도 증가</div>
            </div>
        </div>
    </div>

    <button id="play-start-btn" onclick="launchGame()">대기열 시작</button>
</div>

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
    let keeperPos = { x: 240, y: 110, targetX: 240, isDiving: false, diveSide: 'none' };
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

    function startRoyal44BGM() {
        if (!isBgmOn) return;
        initAudio();

        let step = 0;
        const notes = [130.81, 146.83, 164.81, 196.00, 220.00];

        if (bgmInterval) clearInterval(bgmInterval);

        bgmInterval = setInterval(() => {
            if (!isBgmOn || !audioCtx) return;

            const time = audioCtx.currentTime;

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

            step = (step + 1) % 16;
        }, 180);
    }

    function toggleBGM() {
        isBgmOn = !isBgmOn;
        const btn = document.getElementById('bgm-toggle-btn');
        if (isBgmOn) {
            btn.innerText = "🎵 Royal 44 BGM: ON";
            startRoyal44BGM();
        } else {
            btn.innerText = "🔇 Royal 44 BGM: OFF";
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

    // 경기장 비주얼
    function drawStadium() {
        ctx.fillStyle = '#1e1c2a';
        ctx.fillRect(0, 0, canvas.width, 160);

        // 관중석
        const colors = ['#e91e63', '#ff9800', '#2196f3', '#4caf50', '#ffffff'];
        for (let i = 0; i < 220; i++) {
            let rx = (i * 13) % canvas.width;
            let ry = (i * 7) % 95;
            ctx.fillStyle = colors[i % colors.length];
            ctx.fillRect(rx, ry, 6, 8);
        }

        ctx.fillStyle = '#111';
        ctx.fillRect(0, 95, canvas.width, 25);
        ctx.fillStyle = '#ff4655';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('SQUID GAME • 500PTS SPEED UP 🦑', canvas.width / 2, 112);

        // 골대
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
        pitchGrad.addColorStop(0, '#a37c54');
        pitchGrad.addColorStop(1, '#6d4c2b');
        ctx.fillStyle = pitchGrad;
        ctx.fillRect(0, 140, canvas.width, canvas.height - 140);

        drawYoungheeKeeper();
        drawPinkGuardKicker();
    }

    // 1. 골키퍼: 오징어 게임
