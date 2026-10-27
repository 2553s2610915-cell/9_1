import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="오디오 축구 게임 (Audio Soccer)",
    page_icon="⚽",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #ffffff;
    }
    .big-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: bold;
        color: #2ea44f;
        margin-bottom: 10px;
    }
    .sub-title {
        text-align: center;
        color: #8b949e;
        font-size: 1rem;
        margin-bottom: 25px;
    }
    .info-box {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">⚽ Audio Soccer (오디오 축구)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">이어폰을 착용하고 소리만 들어 공을 받아쳐내세요!</div>', unsafe_allow_html=True)

with st.expander("📖 게임 방법 & 주의사항", expanded=True):
    st.markdown("""
    1. **이어폰 또는 헤드폰 필수**: 좌/우 입체 음향으로 공의 위치를 감지합니다.
    2. **준비하기**: 화면 중앙의 **[게임 시작]** 버튼을 누릅니다.
    3. **공 슈팅 소리**:
       - **왼쪽 소리**: 공이 왼쪽에서 날아옴
       - **오른쪽 소리**: 공이 오른쪽에서 날아옴
    4. **방어 타이밍**: 소리가 가장 가까워졌을 때 **화면 전체 검은 영역** 아무 곳이나 터치/클릭하세요!
    """)

# Web Audio API 및 HTML/JS 기반 인터랙티브 게임 컴포넌트
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
            height: 480px;
            background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
            border: 2px solid #30363d;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 20px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .stats-bar {
            width: 100%;
            display: flex;
            justify-content: space-between;
            font-size: 1.2rem;
            font-weight: bold;
            background: rgba(255,255,255,0.05);
            padding: 10px 20px;
            border-radius: 10px;
        }
        .heart { color: #ff4d4d; }
        .score { color: #2ea44f; }
        
        #touch-zone {
            width: 100%;
            height: 260px;
            border: 2px dashed #484f58;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background-color 0.1s;
            text-align: center;
        }
        #touch-zone:active {
            background-color: rgba(46, 164, 79, 0.2);
            border-color: #2ea44f;
        }
        .touch-msg {
            font-size: 1.3rem;
            font-weight: bold;
            color: #c9d1d9;
            pointer-events: none;
        }
        .touch-sub {
            font-size: 0.9rem;
            color: #8b949e;
            margin-top: 8px;
            pointer-events: none;
        }
        
        #start-btn {
            width: 100%;
            padding: 16px;
            font-size: 1.3rem;
            font-weight: bold;
            color: #ffffff;
            background-color: #238636;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
        }
        #start-btn:active {
            transform: scale(0.98);
        }
        
        #feedback {
            position: absolute;
            top: 45%;
            font-size: 2.5rem;
            font-weight: 900;
            text-shadow: 0 0 10px rgba(0,0,0,0.8);
            opacity: 0;
            transition: opacity 0.2s, transform 0.2s;
            pointer-events: none;
        }
        .perfect { color: #2ea44f; }
        .good { color: #e3b341; }
        .miss { color: #f85149; }
    </style>
</head>
<body>

<div id="game-container">
    <div class="stats-bar">
        <div>점수: <span id="score-val" class="score">0</span></div>
        <div>라이프: <span id="lives-val" class="heart">❤️❤️❤️</span></div>
    </div>

    <div id="touch-zone">
        <div class="touch-msg">🎧 소리를 듣고 터치하세요!</div>
        <div class="touch-sub">(화면 아무 곳이나 눌러도 됩니다)</div>
    </div>

    <div id="feedback">PERFECT!</div>

    <button id="start-btn" onclick="startGame()">⚽ 게임 시작</button>
</div>

<script>
    let audioCtx = null;
    let isPlaying = false;
    let score = 0;
    let lives = 3;
    
    let currentBall = null; // { direction: 'left'|'right', startTime: number, duration: number, hit: boolean }
    let gameLoopTimeout = null;

    // TTS 음성 안내
    function speak(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.1;
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

    // Web Audio API 기반 3D 소리 생성 함수
    function playSoccerBallSound(direction, duration) {
        if (!audioCtx) return;

        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        const panner = audioCtx.createStereoPanner();

        osc.type = 'sine';
        // 공이 날아오며 높낮이가 변하는 소리
        osc.frequency.setValueAtTime(120, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(320, audioCtx.currentTime + duration);

        // 오디오 패닝 설정 (-1: 완전 왼쪽, 1: 완전 오른쪽)
        const panValue = (direction === 'left') ? -0.95 : 0.95;
        panner.pan.setValueAtTime(panValue, audioCtx.currentTime);

        // 공이 가까워질수록 소리가 커지는 효과
        gainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.8, audioCtx.currentTime + duration - 0.05);
        gainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + duration);

        osc.connect(gainNode);
        gainNode.connect(panner);
        panner.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    }

    // 성공/실패 효과음
    function playEffect(type) {
        if (!audioCtx) return;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === 'hit') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(400, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
        } else if (type === 'miss') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(150, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(60, audioCtx.currentTime + 0.3);
            gain.gain.setValueAtTime(0.6, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.3);
        }
    }

    function startGame() {
        initAudio();
        isPlaying = true;
        score = 0;
        lives = 3;
        updateUI();

        document.getElementById('start-btn').style.display = 'none';
        speak("게임 시작! 소리에 집중하세요.");

        setTimeout(nextBall, 2000);
    }

    function nextBall() {
        if (!isPlaying) return;

        const direction = Math.random() < 0.5 ? 'left' : 'right';
        // 점수가 높아질수록 속도가 빨라짐 (1.2초 ~ 2.0초)
        const duration = Math.max(1.0, 2.0 - (score * 0.05));
        
        currentBall = {
            direction: direction,
            startTime: audioCtx.currentTime,
            duration: duration,
            hit: false
        };

        playSoccerBallSound(direction, duration);

        // 공이 지나갈 때까지 터치 안 하면 MISS 판정
        gameLoopTimeout = setTimeout(() => {
            if (currentBall && !currentBall.hit && isPlaying) {
                handleMiss("놓침!");
            }
        }, duration * 1000 + 100);
    }

    function handleTouch(e) {
        if (e) e.preventDefault();
        if (!isPlaying || !currentBall || currentBall.hit) return;

        const currentTime = audioCtx.currentTime;
        const elapsedTime = currentTime - currentBall.startTime;
        const timeDiff = Math.abs(elapsedTime - currentBall.duration);

        currentBall.hit = true;
        clearTimeout(gameLoopTimeout);

        // 판정 기준 (0.2초 이내 Perfect, 0.4초 이내 Good)
        if (timeDiff <= 0.20) {
            score += 100;
            showFeedback("PERFECT! ⚽", "perfect");
            playEffect('hit');
        } else if (timeDiff <= 0.40) {
            score += 50;
            showFeedback("GOOD! 👍", "good");
            playEffect('hit');
        } else {
            handleMiss("타이밍 미스!");
            return;
        }

        updateUI();
        setTimeout(nextBall, 1200);
    }

    function handleMiss(reason) {
        lives -= 1;
        playEffect('miss');
        showFeedback("MISS! ❌", "miss");
        updateUI();

        if (lives <= 0) {
            gameOver();
        } else {
            setTimeout(nextBall, 1500);
        }
    }

    function showFeedback(text, className) {
        const fb = document.getElementById('feedback');
        fb.innerText = text;
        fb.className = className;
        fb.style.opacity = '1';
        fb.style.transform = 'scale(1.2)';

        setTimeout(() => {
            fb.style.opacity = '0';
            fb.style.transform = 'scale(1.0)';
        }, 600);
    }

    function updateUI() {
        document.getElementById('score-val').innerText = score;
        let hearts = '';
        for (let i = 0; i < lives; i++) hearts += '❤️';
        document.getElementById('lives-val').innerText = hearts || '💀';
    }

    function gameOver() {
        isPlaying = false;
        currentBall = null;
        document.getElementById('start-btn').style.display = 'block';
        document.getElementById('start-btn').innerText = '🔄 다시 시작';
        
        speak("게임 오버. 최종 점수는 " + score + "점입니다.");
    }

    // Touch & Click Event Listener
    const touchZone = document.getElementById('touch-zone');
    touchZone.addEventListener('touchstart', handleTouch, { passive: false });
    touchZone.addEventListener('mousedown', handleTouch);
</script>
</body>
</html>
"""

components.html(game_html, height=520)
