// Application State
let mediaStream = null;
let currentImageBase64 = null;
let userCoords = { latitude: null, longitude: null };
let currentScanData = null;

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    // Auto-fetch GPS on page load for instant location availability
    autoFetchGPS();
});

async function checkHealth() {
    const statusElem = document.getElementById('ai-status');
    const statusText = document.getElementById('ai-status-text');

    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            statusElem.classList.remove('offline');
            statusElem.classList.add('online');
            statusText.textContent = 'AI Vision Ready';
        } else {
            throw new Error('Health check failed');
        }
    } catch (error) {
        statusElem.classList.remove('online');
        statusElem.classList.add('offline');
        statusText.textContent = 'Backend Offline';
    }
}

/**
 * High-accuracy automatic GPS grab
 */
function autoFetchGPS() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userCoords.latitude = position.coords.latitude;
            userCoords.longitude = position.coords.longitude;
            const statusText = document.getElementById('gps-coords-text');
            if (statusText) {
                statusText.textContent = `${userCoords.latitude.toFixed(4)}, ${userCoords.longitude.toFixed(4)}`;
            }
        },
        (err) => console.warn('Auto GPS pending permission or user action'),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
}

/**
 * Camera Toggle with mobile fallback constraints
 */
async function camera() {
    const video = document.getElementById('webcam');
    const preview = document.getElementById('image-preview');
    const placeholder = document.getElementById('camera-placeholder');
    const btnLabel = document.getElementById('camera-btn-label');

    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
        video.classList.add('hidden');
        placeholder.classList.remove('hidden');
        btnLabel.textContent = 'Toggle Camera';
        return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Camera access is not supported on this browser/protocol.');
        return;
    }

    const cameraConstraints = [
        { video: { facingMode: { exact: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
        { video: { facingMode: "environment" }, audio: false },
        { video: true, audio: false }
    ];

    let streamObtained = false;
    for (const constraints of cameraConstraints) {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            streamObtained = true;
            break;
        } catch (e) {
            console.warn('Camera mode retry...', e);
        }
    }

    if (streamObtained && mediaStream) {
        video.srcObject = mediaStream;
        video.classList.remove('hidden');
        preview.classList.add('hidden');
        placeholder.classList.add('hidden');
        btnLabel.textContent = 'Stop Camera';
        currentImageBase64 = null;
    } else {
        alert('Unable to access phone camera. Check browser permissions.');
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        currentImageBase64 = e.target.result;
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
            document.getElementById('camera-btn-label').textContent = 'Toggle Camera';
        }
        const video = document.getElementById('webcam');
        const preview = document.getElementById('image-preview');
        const placeholder = document.getElementById('camera-placeholder');

        video.classList.add('hidden');
        placeholder.classList.add('hidden');
        preview.src = currentImageBase64;
        preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
}

function gps() {
    const statusText = document.getElementById('gps-coords-text');
    if (!navigator.geolocation) {
        alert('Geolocation unsupported.');
        return;
    }
    statusText.textContent = 'Fetching GPS...';
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userCoords.latitude = position.coords.latitude;
            userCoords.longitude = position.coords.longitude;
            statusText.textContent = `${userCoords.latitude.toFixed(4)}, ${userCoords.longitude.toFixed(4)}`;
            restaurants(userCoords.latitude, userCoords.longitude);
        },
        (error) => {
            statusText.textContent = 'GPS Denied';
            alert('Enable location permission in browser settings.');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}

async function restaurants(lat, lng) {
    const loader = document.getElementById('restaurant-loader');
    const emptyMsg = document.getElementById('restaurant-empty');
    const grid = document.getElementById('restaurant-list');

    loader.classList.remove('hidden');
    emptyMsg.classList.add('hidden');
    grid.classList.add('hidden');
    grid.innerHTML = '';

    try {
        const response = await fetch('/api/restaurants', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        });
        const data = await response.json();
        loader.classList.add('hidden');

        if (data.status === 'success' && data.restaurants && data.restaurants.length > 0) {
            grid.classList.remove('hidden');
            data.restaurants.forEach(rest => {
                const card = document.createElement('div');
                card.className = 'restaurant-card';
                card.innerHTML = `
                    <div class="rest-header">
                        <span class="rest-name">${escapeHtml(rest.name)}</span>
                        <span class="rest-rating">★ ${rest.rating}</span>
                    </div>
                    <p class="rest-address">${escapeHtml(rest.address)}</p>
                    <span class="rest-distance">📍 ${rest.distance} away</span>
                `;
                grid.appendChild(card);
            });
        } else {
            emptyMsg.innerHTML = `<p>${data.message || 'No restaurants found nearby.'}</p>`;
            emptyMsg.classList.remove('hidden');
        }
    } catch (err) {
        loader.classList.add('hidden');
        emptyMsg.innerHTML = `<p>Error fetching restaurants.</p>`;
        emptyMsg.classList.remove('hidden');
    }
}

async function scan() {
    let payloadImage = null;

    if (currentImageBase64) {
        payloadImage = currentImageBase64;
    } else if (mediaStream) {
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('snapshot-canvas');
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        payloadImage = canvas.toDataURL('image/jpeg', 0.90);
    } else {
        alert('Please start camera or upload a photo first.');
        return;
    }

    // Refresh GPS coordinates right before scanning
    autoFetchGPS();

    const overlay = document.getElementById('scan-overlay');
    overlay.classList.remove('hidden');

    try {
        const response = await fetch('/api/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: payloadImage })
        });

        const result = await response.json();
        overlay.classList.add('hidden');

        if (result.error) {
            alert('Recognition Error: ' + result.error);
            return;
        }

        const timestamp = new Date().toLocaleString('en-US', {
            dateStyle: 'medium',
            timeStyle: 'short'
        });

        currentScanData = {
            food: result.food || 'Unknown Food',
            confidence: result.confidence || '92%',
            cuisine: result.cuisine || 'International',
            nutrition: result.nutrition || {},
            latitude: userCoords.latitude,
            longitude: userCoords.longitude,
            timestamp: timestamp
        };

        renderResults(currentScanData);
        notify(currentScanData);

    } catch (err) {
        overlay.classList.add('hidden');
        alert('Scan failed: ' + err.message);
    }
}

function renderResults(data) {
    document.getElementById('results-placeholder').classList.add('hidden');
    document.getElementById('results-content').classList.remove('hidden');

    document.getElementById('res-food-name').textContent = data.food;
    document.getElementById('res-cuisine').textContent = data.cuisine;
    document.getElementById('res-confidence').textContent = `${data.confidence} Confidence`;

    const nut = data.nutrition || {};
    document.getElementById('nut-calories').textContent = nut.calories || 'N/A';
    document.getElementById('nut-protein').textContent = nut.protein || 'N/A';
    document.getElementById('nut-carbs').textContent = nut.carbs || 'N/A';
    document.getElementById('nut-fat').textContent = nut.fat || 'N/A';
    document.getElementById('nut-fiber').textContent = nut.fiber || 'N/A';
}

async function notify(dataPayload) {
    const telegramBadge = document.getElementById('telegram-status');
    const payload = dataPayload || currentScanData;

    if (!payload) return;

    telegramBadge.className = 'badge badge-muted';
    telegramBadge.textContent = 'Sending Telegram...';

    try {
        const response = await fetch('/api/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();
        if (res.status === 'success') {
            telegramBadge.className = 'badge badge-success';
            telegramBadge.textContent = 'Telegram Sent ✓';
        } else {
            telegramBadge.className = 'badge';
            telegramBadge.textContent = 'Telegram Error';
        }
    } catch (err) {
        telegramBadge.className = 'badge';
        telegramBadge.textContent = 'Telegram Error';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}