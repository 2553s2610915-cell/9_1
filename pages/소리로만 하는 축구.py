import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="PK 오디오 축구 게임 - 관중 반응 추가",
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

st.markdown('<div class="big-title">⚽ FIFA Style PK (관중 환호 & 야유)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">이어폰을 끼고 소리에 집중하세요! 골 성공 시 환호, 막힐 시 야유 소리가 들립니다.</div>', unsafe_allow_html=True)

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
    
    let ball = null; 
    let keeperPos = { x: 240, y: 120, targetX: 240, isDiving: false };
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

    // 3D 오디오 (좌/우 슈팅 소리)
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

    // 관중 환호 소리 (노이즈 필터링 노드 사용)
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
        filter.frequency.setValueAtTime(800, audioCtx.currentTime);
        filter.Q.setValueAtTime(1.5, audioCtx.currentTime);

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

    // 관중 야유 소리 (낮은 야유음)
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

    // 경기장 렌더링
    function drawStadium() {
        let grad = ctx.createLinearGradient(0, 0, 0, 160);
        grad.addColorStop(0, '#2b3a42');
        grad.addColorStop(1, '#475b63');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, 160);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
        for (let i = 0; i < 80; i++) {
            let rx = (i * 17) % canvas.width;
            let ry = (i * 11) % 90;
            ctx.fillRect(rx, ry, 3, 3);
        }

        ctx.fillStyle = '#1e252b';
        ctx.fillRect(0, 95, canvas.width, 25);
        ctx.fillStyle = '#f0a612';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('EA SPORTS FIFA ONLINE • CROWD REACTION ⚽', canvas.width / 2, 112);

        // 골대
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 4;
        ctx.strokeRect(60, 45, 360, 95);

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

        // 잔디
        let pitchGrad = ctx.createLinearGradient(0, 120, 0, canvas.height);
        pitchGrad.addColorStop(0, '#388e3c');
        pitchGrad.addColorStop(1, '#1b5e20');
        ctx.fillStyle = pitchGrad;
        ctx.fillRect(0, 140, canvas.width, canvas.height - 140);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
        for (let y = 140; y < canvas.height; y += 30) {
            ctx.fillRect(0, y, canvas.width, 15);
        }

        // 골키퍼 그리기
        ctx.fillStyle = '#111';
        ctx.beginPath();
        ctx.arc(keeperPos.x, keeperPos.y - 10, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillRect(keeperPos.x - 7, keeperPos.y - 2, 14, 22);

        if (keeperPos.isDiving) {
            ctx.fillRect(keeperPos.x - 20, keeperPos.y, 40, 6); // 다이빙 동작
        } else {
            ctx.fillRect(keeperPos.x - 18, keeperPos.y, 36, 6);
        }

        // 키커 뒷모습
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(240, 320, 4, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(320, 330, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillRect(313, 340, 14, 25);
        ctx.fillStyle = '#111';
        ctx.font = 'bold 9px sans-serif';
        ctx.fillText('32', 320, 354);
    }

    function drawGaugeBar(progress) {
        let barWidth = 260;
        let barHeight = 16;
        let startX = (canvas.width - barWidth) / 2;
        let startY = 370;

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
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = '#2ea44f';
            ctx.beginPath();
            ctx.arc(ball.currentX - 2, ball.currentY - 2, ball.size / 2.8, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        } else {
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(240, 318, 7, 0, Math.PI * 2);
            ctx.fill();
        }

        drawGaugeBar(currentProgress);

        if (feedbackTimer > 0) {
            ctx.font = 'bold 28px sans-serif';
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

        // 골키퍼 선방 AI 확률 계산 (25% + 점수비례)
        let willSave = Math.random() < (0.25 + score * 0.001);

        keeperPos = {
            x: 240,
            y: 120,
            targetX: willSave ? endX : 240,
            isDiving: false
        };

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

            // 골키퍼 이동 애니메이션
            if (ball.willSave && ball.progress > 0.4) {
                keeperPos.x += (keeperPos.targetX - keeperPos.x) * 0.15;
                keeperPos.isDiving = true;
            }

            if (ball.progress <= 1.0) {
                ball.currentX = ball.startX + (ball.endX - ball.startX) * ball.progress;
                ball.currentY = ball.startY + (ball.endY - ball.startY) * ball.progress;
                ball.size = 7 + (ball.progress * 11);
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

        // 골키퍼가 선방한 경우 (막힘 -> 야유 소리)
        if (ball.willSave && ball.progress > 0.6) {
            lives--;
            setFeedback("KEEPER SAVED! 🧤 (야유~)", "#f85149");
            playBooingCrowdSound();
            updateUI();
            
            if (lives <= 0) {
                gameOver();
            } else {
                setTimeout(spawnBall, 1600);
            }
            return;
        }

        let diff = Math.abs(0.85 - ball.progress);

        if (diff <= 0.15) {
            score += 100;
            setFeedback("GOAL! PERFECT! ⚽ (환호)", "#2ea44f");
            playHitEffect();
            playCheerCrowdSound();
            setTimeout(spawnBall, 1600);
        } else if (diff <= 0.32) {
            score += 50;
            setFeedback("GOAL! GOOD! 👍 (환호)", "#e3b341");
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
        setFeedback("MISS! ❌ (야유~)", "#f85149");
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
        keeperPos = { x: 240, y: 120, targetX: 240, isDiving: false };
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

components.html(game_html, height=550)
