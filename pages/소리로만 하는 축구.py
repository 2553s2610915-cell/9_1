import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="FIFA Style PK 오디오 축구",
    page_icon="⚽",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #ffffff;
    }
    .big-title {
        text-align: center;
        font-size: 2.1rem;
        font-weight: bold;
        color: #2ea44f;
        margin-bottom: 5px;
    }
    .sub-title {
        text-align: center;
        color: #8b949e;
        font-size: 0.95rem;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">⚽ Real PK Audio Soccer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">실사 그래픽 PK 게임! 키퍼가 막으면 라이프 차감 없음 & 환호/야유 음성 연동</div>', unsafe_allow_html=True)

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
            background-color: #0b0f19;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        #game-container {
            width: 100%;
            max-width: 500px;
            height: 540px;
            background-color: #161b22;
            border: 2px solid #30363d;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 10px;
            position: relative;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        }
        .stats-bar {
            width: 100%;
            display: flex;
            justify-content: space-between;
            font-size: 1.1rem;
            font-weight: bold;
            background: #21262d;
            padding: 8px 15px;
            border-radius: 8px;
            border: 1px solid #30363d;
        }
        .score { color: #2ea44f; }
        .heart { color: #f85149; }
        
        canvas {
            width: 100%;
            height: 410px;
            border-radius: 8px;
            cursor: pointer;
        }
        
        #start-btn {
            width: 100%;
            padding: 14px;
            font-size: 1.2rem;
            font-weight: bold;
            color: #ffffff;
            background-color: #238636;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
        }
        #start-btn:active {
            transform: scale(0.98);
        }
    </style>
</head>
<body>

<div id="game-container">
    <div class="stats-bar">
        <div>점수: <span id="score-val" class="score">0</span></div>
        <div>라이프: <span id="lives-val" class="heart">❤️❤️❤️</span></div>
    </div>

    <canvas id="gameCanvas" width="480" height="410"></canvas>

    <button id="start-btn" onclick="startGame()">⚽ 게임 시작</button>
</div>

<script>
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    
    let audioCtx = null;
    let isPlaying = false;
    let score = 0;
    let lives = 3;
    
    let ball = null; 
    let keeperPos = { x: 240, y: 115, targetX: 240, isDiving: false, diveSide: 'none' };
    let animationFrameId = null;
    let feedbackText = "";
    let feedbackColor = "";
    let feedbackTimer = 0;
    let voicedNow = false;

    function speak(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.25;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    function initAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
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
        
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = audioCtx.createBufferSource();
        noise.buffer = buffer;

        const filter = audioCtx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(850, audioCtx.currentTime);
        filter.Q.setValueAtTime(1.4, audioCtx.currentTime);

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
        osc1.frequency.linearRampToValueAtTime(95, audioCtx.currentTime + 1.2);

        osc2.frequency.setValueAtTime(115, audioCtx.currentTime);
        osc2.frequency.linearRampToValueAtTime(100, audioCtx.currentTime + 1.2);

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

    function playHitEffect() {
        if (!audioCtx) return;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(350, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(750, audioCtx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
    }

    function drawStadium()
