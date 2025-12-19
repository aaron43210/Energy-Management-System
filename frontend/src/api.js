// API Service Layer
// Centralized module for all communication with the backend server.
// Exports functions for:
//   - Fetching room status
//   - Updating occupancy
//   - Managing AI processes
//   - Connecting/disconnecting CCTV cameras
//   - Getting video stream URLs
// Handles errors and JSON parsing for all API calls.
// Auto-detects backend URL (localhost or remote).

const BASE_URL = window.location.protocol === "https:" 
  ? `https://${window.location.hostname.replace("5173", "8002")}`
  : "http://127.0.0.1:8002";

async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
            throw new Error(`API ${response.status}: ${errorData.detail}`);
        }
        if (response.headers.get("content-type")?.includes("application/json")) {
            return response.json();
        }
        return response;
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
}

export async function fetchRooms() {
    return apiFetch(`${BASE_URL}/api/rooms`);
}

export async function sendOccupancy(roomId, occupied) {
    return apiFetch(`${BASE_URL}/api/occupancy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: roomId, occupied }),
    });
}

export async function startAi(roomId) {
    return apiFetch(`${BASE_URL}/api/ai/${roomId}/start`, {
        method: "POST",
    });
}

export async function stopAi(roomId) {
    return apiFetch(`${BASE_URL}/api/ai/${roomId}/stop`, {
        method: "POST",
    });
}

export async function connectCctv(roomId, cctvIp, cctvUsername, cctvPassword, cctvChannel = "0") {
    return apiFetch(`${BASE_URL}/api/cctv/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            room_id: roomId,
            cctv_ip: cctvIp,
            cctv_username: cctvUsername,
            cctv_password: cctvPassword,
            cctv_channel: cctvChannel,
        }),
    });
}

export async function disconnectCctv(roomId) {
    return apiFetch(`${BASE_URL}/api/cctv/disconnect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: roomId }),
    });
}

export async function getCctvStatus(roomId) {
    return apiFetch(`${BASE_URL}/api/cctv/status/${roomId}`);
}

export function getStreamUrl(roomId) {
    return `${BASE_URL}/api/stream/${roomId}`;
}
