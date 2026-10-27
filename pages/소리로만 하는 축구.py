import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="PK 오디오 축구 게임",
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

st.markdown('<div class="big-title">⚽ FIFA Style PK Audio Soccer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">이어폰을 착용하고 소리와 음성 안내에 따라 타이밍에 맞춰 터치하세요!</div>', unsafe_allow_html=True)

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
            height: 530px;
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
            height: 400px;
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

    <canvas id="gameCanvas" width="480" height="400"></canvas>

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
    let feedbackText = "";
    let feedbackColor = "";
    let feedbackTimer = 0;
    let voicedNow = false;

    // 한국어 TTS 음성 안내
    function speak(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.2;
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

    // 좌/우 3D 오디오 생성
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

    function playEffect(type) {
        if (!audioCtx) return;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === 'hit') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(350, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(750, audioCtx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
        } else {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(160, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(60, audioCtx.currentTime + 0.3);
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.3);
        }
    }

    // 경기장 비주얼 그리기 (FIFA PK 시점)
    function drawStadium() {
        // 1. 관중석 & 경기장 배경
        let grad = ctx.createLinearGradient(0, 0, 0, 160);
        grad.addColorStop(0, '#2b3a42');
        grad.addColorStop(1, '#475b63');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, 160);

        // 관중석 텍스처 느낌
        ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
        for (let i = 0; i < 80; i++) {
            let rx = Math.random() * canvas.width;
            let ry = Math.random() * 90;
            ctx.fillRect(rx, ry, 3, 3);
        }

        // 2. 스폰서 보드
        ctx.fillStyle = '#1e252b';
        ctx.fillRect(0, 95, canvas.width, 25);
        ctx.fillStyle = '#f0a612';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('EA SPORTS FIFA ONLINE • AUDIO SOCCER ⚽', canvas.width / 2, 112);

        // 3. 골대 (백색 프레임 & 그물망)
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 4;
        ctx.strokeRect(60, 45, 360, 95);

        // 골대 그물망
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 75; x < 420; x += 15) {
            ctx.moveTo(x, 45);
            ctx.lineTo(x, 140);
        }
        for (let y = 55; y < 140; y += 12) {
            ctx.moveTo(60, y);
            ctx.lineTo(420, y);
        }
        ctx.stroke();

        // 4. 초록색 잔디 피치
        let pitchGrad = ctx.createLinearGradient(0, 120, 0, canvas.height);
        pitchGrad.addColorStop(0, '#388e3c');
        pitchGrad.addColorStop(1, '#1b5e20');
        ctx.fillStyle = pitchGrad;
        ctx.fillRect(0, 140, canvas.width, canvas.height - 140);

        // 잔디 줄무늬 패턴
        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
        for (let y = 140; y < canvas.height; y += 30) {
            ctx.fillRect(0, y, canvas.width, 15);
        }

        // 5. 골키퍼 (중앙 수비)
        ctx.fillStyle = '#111';
        // 키퍼 머리
        ctx.beginPath();
        ctx.arc(240, 110, 8, 0, Math.PI * 2);
        ctx.fill();
        // 키퍼 몸통 및 팔
        ctx.fillRect(233, 118, 14, 22);
        ctx.fillRect(222, 120, 36, 6);

        // 6. 페널티 스폿 및 키커 뒷모습
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(240, 320, 4, 0, Math.PI * 2);
        ctx.fill();

        // 키커 캐릭터 (하단)
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(320, 330, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillRect(313, 340, 14, 25);
        ctx.fillStyle = '#111';
        ctx.font = 'bold 9px sans-serif';
        ctx.fillText('32', 320, 354);
    }

    // 하단 타이밍 게이지 바
    function drawGaugeBar(progress) {
        let barWidth = 260;
        let barHeight = 16;
        let startX = (canvas.width - barWidth) / 2;
        let startY = 370;

        ctx.fillStyle = '#161b22';
        ctx.fillRect(startX - 2, startY - 2, barWidth + 4, barHeight + 4);

        // 삼색 게이지 (빨강 -> 초록 -> 빨강)
        let gGrad = ctx.createLinearGradient(startX, 0, startX + barWidth, 0);
        gGrad.addColorStop(0, '#f85149');
        gGrad.addColorStop(0.7, '#2ea44f');
        gGrad.addColorStop(1, '#f85149');
        
        ctx.fillStyle = gGrad;
        ctx.fillRect(startX, startY, barWidth, barHeight);

        // 현재 위치 포인터
        if (progress > 0 && progress <= 1.0) {
            let posX = startX + (barWidth * progress);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(posX - 2, startY - 4, 4, barHeight + 8);
        }
    }

    function drawScene() {
        drawStadium();

        let currentProgress = 0;

        // 축구공 이동
        if (ball && ball.active) {
            currentProgress = ball.progress;

            // 공 그리기
            ctx.save();
            ctx.beginPath();
            ctx.arc(ball.currentX, ball.currentY, ball.size, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.stroke();

            // 공 오색 무늬
            ctx.fillStyle = '#2ea44f';
            ctx.beginPath();
            ctx.arc(ball.currentX - 2, ball.currentY - 2, ball.size / 2.8, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        } else {
            // 정지 상태 페널티 스폿 위의 공
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(240, 318, 7, 0, Math.PI * 2);
            ctx.fill();
        }

        // 게이지 바 출력
        drawGaugeBar(currentProgress);

        // 피드백 메시지
        if (feedbackTimer > 0) {
            ctx.font = 'bold 30px sans-serif';
            ctx.fillStyle = feedbackColor;
            ctx.textAlign = 'center';
            ctx.fillText(feedbackText, canvas.width / 2, 220);
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
        let endY = 85;

        voicedNow = false;

        ball = {
            startX: startX,
            startY: startY,
            endX: endX,
            endY: endY,
            currentX: startX,
            currentY: startY,
            size: 7,
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

            // "지금 터치하세요!" 음성 트리거 (타이밍 70% 시점)
            if (ball.progress >= 0.65 && !voicedNow) {
                voicedNow = true;
                speak("지금 터치하세요!");
            }

            if (ball.progress <= 1.0) {
                ball.currentX = ball.startX + (ball.endX - ball.startX) * ball.progress;
                ball.currentY = ball.startY + (ball.endY - ball.startY) * ball.progress;
                ball.size = 7 + (ball.progress * 11); // 날아오면서 공이 커짐
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

        let diff = Math.abs(0.85 - ball.progress);

        if (diff <= 0.15) {
            score += 100;
            setFeedback("PERFECT SAVE! 🧤", "#2ea44f");
            playEffect('hit');
            setTimeout(spawnBall, 1200);
        } else if (diff <= 0.32) {
            score += 50;
            setFeedback("GOOD SAVE! 👍", "#e3b341");
            playEffect('hit');
            setTimeout(spawnBall, 1200);
        } else {
            handleMiss("타이밍 미스!");
        }

        updateUI();
    }

    function handleMiss(reason) {
        lives--;
        setFeedback("GOAL IN! ❌", "#f85149");
        playEffect('miss');
        updateUI();

        if (lives <= 0) {
            gameOver();
        } else {
            setTimeout(spawnBall, 1400);
        }
    }

    function setFeedback(text, color) {
        feedbackText = text;
        feedbackColor = color;
        feedbackTimer = 40;
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

        speak("게임 시작! 소리를 듣고 공을 막아내세요.");

        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        animationFrameId = requestAnimationFrame(gameLoop);

        setTimeout(spawnBall, 1800);
    }

    function gameOver() {
        isPlaying = false;
        document.getElementById('start-btn').style.display = 'block';
        document.getElementById('start-btn').innerText = '🔄 다시 시작';
        speak("게임 오버. 최종 점수는 " + score + "점입니다.");
    }

    canvas.addEventListener('touchstart', handleTouch, { passive: false });
    canvas.addEventListener('mousedown', handleTouch);
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' || e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
            handleTouch();
        }
    });

    drawScene();
</script>
</body>
</html>
"""

components.html(game_html, height=550)
