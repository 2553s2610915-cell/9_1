import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="오디오 & 비주얼 축구 게임",
    page_icon="⚽",
    layout="centered"
)

# Custom CSS 스타일링
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .big-title {
        text-align: center;
        font-size: 2rem;
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

st.markdown('<div class="big-title">⚽ 스케치 기반 오디오 축구 게임</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">좌/우에서 날아오는 축구공의 소리와 궤적을 보고 타이밍 맞춰 터치하세요!</div>', unsafe_allow_html=True)

# HTML/JS/Canvas 게임 구현
game_html = """
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
            background-color: #0e1117;
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
            height: 520px;
            background-color: #ffffff;
            border: 3px solid #30363d;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 10px;
            position: relative;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            color: #000;
        }
        .stats-bar {
            width: 100%;
            display: flex;
            justify-content: space-between;
            font-size: 1.1rem;
            font-weight: bold;
            background: #f0f3f6;
            padding: 8px 15px;
            border-radius: 8px;
            border: 1px solid #d0d7de;
        }
        .score { color: #1f883d; }
        .heart { color: #cf222e; }
        
        canvas {
            width: 100%;
            height: 380px;
            background-color: #ffffff;
            border-radius: 8px;
            cursor: pointer;
        }
        
        #start-btn {
            width: 100%;
            padding: 12px;
            font-size: 1.2rem;
            font-weight: bold;
            color: #ffffff;
            background-color: #1f883d;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(31, 136, 61, 0.3);
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

    <canvas id="gameCanvas" width="480" height="380"></canvas>

    <button id="start-btn" onclick="startGame()">⚽ 게임 시작</button>
</div>

<script>
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    
    let audioCtx = null;
    let isPlaying = false;
    let score = 0;
    let lives = 3;
    
    let ball = null; // { startX, startY, endX, endY, progress, duration, side, active, hit }
    let animationFrameId = null;
    let lastTime = 0;
    let feedbackText = "";
    let feedbackColor = "";
    let feedbackTimer = 0;

    function initAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    // 소리 생성 및 입체 오디오 설정
    function playSoccerSound(side, duration) {
        if (!audioCtx) return;

        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        const panner = audioCtx.createStereoPanner();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(130, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(350, audioCtx.currentTime + duration);

        const panVal = (side === 'left') ? -0.9 : 0.9;
        panner.pan.setValueAtTime(panVal, audioCtx.currentTime);

        gainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.7, audioCtx.currentTime + duration - 0.05);
        gainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + duration);

        osc.connect(gainNode);
        gainNode.connect(panner);
        panner.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    }

    function playEffect(type) {
        if (!audioCtx) return;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === 'hit') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(300, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(700, audioCtx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
        } else {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(150, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(60, audioCtx.currentTime + 0.25);
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.25);
        }
    }

    function drawGoalNet() {
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        
        // 골대 외각 프레임
        ctx.strokeRect(100, 30, 280, 110);
        
        // 스케치 느낌의 그물망 그리기
        ctx.strokeStyle = '#888';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 115; x < 380; x += 20) {
            ctx.moveTo(x, 30);
            ctx.lineTo(x + 5, 140);
        }
        for (let y = 45; y < 140; y += 15) {
            ctx.moveTo(100, y);
            ctx.lineTo(380, y + 2);
        }
        ctx.stroke();
    }

    function drawCharacter(x, y, isBlue, label) {
        ctx.save();
        ctx.translate(x, y);

        // 머리
        ctx.beginPath();
        ctx.arc(0, -30, 18, 0, Math.PI * 2);
        ctx.fillStyle = isBlue ? '#d0e8ff' : '#ffffff';
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();

        // 눈 & 미소
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.arc(-6, -34, 2, 0, Math.PI * 2);
        ctx.arc(6, -34, 2, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, -28, 8, 0.2, Math.PI - 0.2);
        ctx.stroke();

        // 몸통 (직사각형)
        ctx.fillStyle = isBlue ? '#b6d7a8' : '#ffffff';
        ctx.fillRect(-15, -10, 30, 40);
        ctx.strokeRect(-15, -10, 30, 40);

        // 팔 (스케치 느낌)
        ctx.beginPath();
        ctx.moveTo(-15, -5);
        ctx.quadraticCurveTo(-30, 5, -25, 20);
        ctx.moveTo(15, -5);
        ctx.quadraticCurveTo(30, 5, 25, 20);
        ctx.stroke();

        // 다리
        ctx.beginPath();
        ctx.moveTo(-8, 30);
        ctx.lineTo(-12, 65);
        ctx.moveTo(8, 30);
        ctx.lineTo(12, 65);
        ctx.stroke();

        ctx.restore();
    }

    function drawScene() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 1. 골대 (상단)
        drawGoalNet();

        // 2. 스케치 캐릭터 2명 (왼쪽: 수비수, 오른쪽: 골키퍼)
        drawCharacter(130, 230, true, "수비수");
        drawCharacter(310, 230, false, "키퍼");

        // 3. 공 궤적 및 축구공
        if (ball && ball.active) {
            // 궤적 선 (스케치 화살표 느낌)
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(ball.startX, ball.startY);
            ctx.lineTo(ball.currentX, ball.currentY);
            ctx.stroke();

            // 축구공
            ctx.save();
            ctx.beginPath();
            ctx.arc(ball.currentX, ball.currentY, 18, 0, Math.PI * 2);
            ctx.fillStyle = '#2c1320'; // 스케치 이미지의 짙은 공 색상
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.stroke();

            // 공 내부 무늬
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.arc(ball.currentX - 4, ball.currentY - 4, 5, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        // 4. 피드백 텍스트 (PERFECT, GOOD, MISS)
        if (feedbackTimer > 0) {
            ctx.font = 'bold 28px sans-serif';
            ctx.fillStyle = feedbackColor;
            ctx.textAlign = 'center';
            ctx.fillText(feedbackText, canvas.width / 2, 190);
            feedbackTimer--;
        }
    }

    function spawnBall() {
        if (!isPlaying) return;

        const side = Math.random() < 0.5 ? 'left' : 'right';
        const duration = Math.max(0.9, 1.8 - (score * 0.04));

        let startX = side === 'left' ? 140 : 320;
        let startY = 280;
        let endX = side === 'left' ? 360 : 120; // 골대 쪽 궤적
        let endY = 70;

        ball = {
            startX: startX,
            startY: startY,
            endX: endX,
            endY: endY,
            currentX: startX,
            currentY: startY,
            progress: 0,
            duration: duration,
            side: side,
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

            if (ball.progress <= 1.0) {
                ball.currentX = ball.startX + (ball.endX - ball.startX) * ball.progress;
                ball.currentY = ball.startY + (ball.endY - ball.startY) * ball.progress;
            } else if (!ball.hit) {
                // 시간 초과 - MISS
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

        let diff = Math.abs(1.0 - ball.progress);

        if (diff <= 0.18) {
            score += 100;
            setFeedback("PERFECT! ⚽", "#1f883d");
            playEffect('hit');
            setTimeout(spawnBall, 1000);
        } else if (diff <= 0.38) {
            score += 50;
            setFeedback("GOOD! 👍", "#d97706");
            playEffect('hit');
            setTimeout(spawnBall, 1000);
        } else {
            handleMiss("타이밍 미스!");
        }

        updateUI();
    }

    function handleMiss(reason) {
        lives--;
        setFeedback("MISS! ❌", "#cf222e");
        playEffect('miss');
        updateUI();

        if (lives <= 0) {
            gameOver();
        } else {
            setTimeout(spawnBall, 1200);
        }
    }

    function setFeedback(text, color) {
        feedbackText = text;
        feedbackColor = color;
        feedbackTimer = 35;
    }

    function updateUI() {
        document.getElementById('score-val').innerText = score;
        let hearts = '';
        for (let i = 0; i < lives; i++) hearts += '❤️';
        document.getElementById('lives-val').innerText = hearts || '💀';
    }

    function startGame() {
        initAudio();
        isPlaying = true;
        score = 0;
        lives = 3;
        ball = null;
        updateUI();

        document.getElementById('start-btn').style.display = 'none';

        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        animationFrameId = requestAnimationFrame(gameLoop);

        setTimeout(spawnBall, 1000);
    }

    function gameOver() {
        isPlaying = false;
        document.getElementById('start-btn').style.display = 'block';
        document.getElementById('start-btn').innerText = '🔄 다시 시작';
    }

    // 터치, 클릭 및 키보드 이벤트
    canvas.addEventListener('touchstart', handleTouch, { passive: false });
    canvas.addEventListener('mousedown', handleTouch);
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' || e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
            handleTouch();
        }
    });

    // 초기 화면 렌더링
    drawScene();
</script>
</body>
</html>
"""

components.html(game_html, height=540)
