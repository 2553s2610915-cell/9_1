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

        ctx.fillStyle = 'rgba(0,0,0,0.15)';
        ctx.fillRect(160, 0, 15, 95);
        ctx.fillRect(310, 0, 15, 95);

        ctx.fillStyle = '#111';
        ctx.fillRect(0, 95, canvas.width, 25);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(310, 97, 160, 21);
        
        ctx.fillStyle = '#e65100';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('EA SPORTS', 320, 112);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('FIFA ONLINE 3', 150, 112);

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

        ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
        for (let y = 145; y < canvas.height; y += 28) {
            ctx.fillRect(0, y, canvas.width, 14);
        }

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(30, 145);
        ctx.lineTo(450, 145);
        ctx.stroke();

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

            ctx.strokeStyle = '#1b1b1b';
            ctx.lineWidth = 5;
            ctx.beginPath();
            ctx.moveTo(-6, -10);
            ctx.lineTo(dir * 30, -15);
            ctx.stroke();

            ctx.fillStyle = '#80deea';
            ctx.beginPath();
            ctx.arc(dir * 32, -15, 4, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = '#1b1b1b';
            ctx.lineWidth = 5;
            ctx.beginPath();
            ctx.moveTo(-4, 10);
            ctx.lineTo(-15, 25);
            ctx.moveTo(4, 10);
            ctx.lineTo(15, 25);
            ctx.stroke();

            ctx.fillStyle = '#80deea';
            ctx.fillRect(-18, 24, 6, 4);
            ctx.fillRect(12, 24, 6, 4);
        } else {
            ctx.fillStyle = '#ffcc80';
            ctx.beginPath();
            ctx.arc(0, -22, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#4e342e';
            ctx.beginPath();
            ctx.arc(0, -24, 6, Math.PI, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#1b1b1b';
            ctx.fillRect(-10, -16, 20, 24);
            ctx.fillStyle = '#ffd54f';
            ctx.fillRect(-3, -12, 6, 5);

            ctx.strokeStyle = '#1b1b1b';
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(-10, -12);
            ctx.lineTo(-20, -2);
            ctx.moveTo(10, -12);
            ctx.lineTo(20, -2);
            ctx.stroke();

            ctx.fillStyle = '#80deea';
            ctx.beginPath();
            ctx.arc(-21, -1, 4, 0, Math.PI * 2);
            ctx.arc(21, -1, 4, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#111111';
            ctx.fillRect(-9, 8, 18, 10);

            ctx.strokeStyle = '#111111';
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(-5, 18);
            ctx.lineTo(-7, 28);
            ctx.moveTo(5, 18);
            ctx.lineTo(7, 28);
            ctx.stroke();

            ctx.fillStyle = '#80deea';
            ctx.fillRect(-10, 27, 6, 4);
            ctx.fillRect(4, 27, 6, 4);
        }

        ctx.restore();
    }

    function drawKicker() {
        ctx.save();
        ctx.translate(330, 325);

        ctx.fillStyle = 'rgba(0,0,0,0.35)';
        ctx.beginPath();
        ctx.ellipse(0, 42, 14, 5, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#5d4037';
        ctx.beginPath();
        ctx.arc(0, -8, 8, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#ffffff';
        ctx.fillRect(-12, 0, 24, 26);

        ctx.fillStyle = '#263238';
        ctx.font = '900 8px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('BALE', 0, 8);
        ctx.font = '900 12px sans-serif';
        ctx.fillText('32', 0, 21);

        ctx.fillStyle = '#eceff1';
        ctx.fillRect(-11, 26, 22, 10);

        ctx.fillStyle = '#ffcc80';
        ctx.fillRect(-9, 36, 6, 6);
        ctx.fillRect(3, 36, 6, 6);

        ctx.fillStyle = '#ffffff';
        ctx.fillRect(-10, 40, 7, 4);
        ctx.fillRect(3, 40, 7, 4);

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
        gGrad.addColorStop(0, '#f85149');
        gGrad.addColorStop(0.7, '#2ea44f');
        gGrad.addColorStop(1, '#f85149');
        
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
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            ctx.fillStyle = '#2ea44f';
            ctx.beginPath();
            ctx.arc(ball.currentX - 2, ball.currentY - 2, ball.size / 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        } else {
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(240, 318, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.stroke();
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
                ball.currentY = ball.startY + (ball.endY - ball.startY) * ball.progress;
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
            setFeedback("GOAL! PERFECT! ⚽", "#2ea44f");
            playHitEffect();
            playCheerCrowdSound();
            setTimeout(spawnBall, 1600);
        } else if (diff <= 0.32) {
            score += 50;
            setFeedback("GOAL! GOOD! 👍", "#e3b341");
            playHitEffect();
            playCheerCrowdSound();
            setTimeout(spawnBall, 1600);
        } else {
            handleMiss("타이밍 미스!");
        }

        updateUI();
    }

    function handleMiss(reason) {
        lives--;
        setFeedback("TIMING MISS! ❌", "#f85149");
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

    function startGame() {
        initAudio();
        isPlaying = true;
        score = 0;
        lives = 3;
        ball = null;
        keeperPos = { x: 240, y: 115, targetX: 240, isDiving: false, diveSide: 'none' };
        updateUI();

        document.getElementById('start-btn').style.display = 'none';

        speak("게임 시작! 소리를 듣고 골을 성공시키세요.");

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

components.html(game_html, height=560)
