// Main Dashboard Component
// Core UI component that:
//   - Fetches and displays all rooms status in real-time
//   - Provides navigation between 3 modes: Dashboard, Webcam Test, CCTV Real Mode
//   - Auto-refreshes room data at configurable intervals
//   - Handles API errors and connection issues
// Manages auto-refresh toggle and refresh rate settings.
// Renders RoomCard components for each room.

import { useEffect, useState, useCallback } from "react";
import RoomCard from "./RoomCard";
import WebcamTestMode from "./WebcamTestMode";
import CctvRealMode from "./CctvRealMode";
import VideoUpload from "./VideoUpload";
import { fetchRooms } from "./api";

export default function Dashboard() {
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard"); 
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshRate, setRefreshRate] = useState(1000);

  const loadRooms = useCallback(async () => {
    try {
      const data = await fetchRooms();
      setRooms(data.rooms || []);
      setLastUpdate(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      console.error("Backend error:", err);
      setError("🔴 Could not connect to backend. Ensure it's running on port 8002.");
      setRooms([]);
    }
  }, []);

  useEffect(() => {
    loadRooms();
    if (!autoRefresh) return;
    
    const interval = setInterval(loadRooms, refreshRate);
    return () => clearInterval(interval);
  }, [loadRooms, autoRefresh, refreshRate]);

  return (
    <div className="container">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1>⚡ AI Energy Management System</h1>
          <p style={{ color: "#666", margin: "5px 0" }}>
            Real-time occupancy detection & automatic energy control
          </p>
        </div>
        <div style={{ textAlign: "right", fontSize: "12px", color: "#888" }}>
          {lastUpdate && <p>Last update: {lastUpdate}</p>}
          <label style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh every
            <select
              value={refreshRate}
              onChange={(e) => setRefreshRate(Number(e.target.value))}
              style={{ padding: "4px", fontSize: "11px" }}
            >
              <option value={500}>500ms</option>
              <option value={1000}>1s</option>
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
            </select>
          </label>
          <button
            onClick={loadRooms}
            style={{
              marginTop: "8px",
              padding: "6px 12px",
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "11px",
            }}
          >
            🔄 Refresh Now
          </button>
        </div>
      </header>

      {error && (
        <div style={{
          backgroundColor: "#ffe0e0",
          border: "1px solid #ff6b6b",
          color: "#d63031",
          padding: "12px",
          borderRadius: "4px",
          marginBottom: "20px",
          fontSize: "14px",
        }}>
          {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="tabs">
        <button
          className={`tab-button ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          📊 Dashboard
        </button>
        <button
          className={`tab-button ${activeTab === "webcam" ? "active" : ""}`}
          onClick={() => setActiveTab("webcam")}
        >
          🎥 Webcam Test Mode
        </button>
        <button
          className={`tab-button ${activeTab === "cctv" ? "active" : ""}`}
          onClick={() => setActiveTab("cctv")}
        >
          📹 CCTV Real Mode
        </button>
        <button
          className={`tab-button ${activeTab === "upload" ? "active" : ""}`}
          onClick={() => setActiveTab("upload")}
        >
          ⬆️ Upload Video
        </button>
      </div>

      {/* Dashboard Tab - Auto-updating Live Status */}
      {activeTab === "dashboard" && (
        <div>
          {!error && rooms.length === 0 && (
            <p style={{ textAlign: "center", color: "#999", padding: "20px" }}>
              Loading rooms...
            </p>
          )}
          <div className="room-grid">
            {rooms.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </div>
          {rooms.length > 0 && (
            <div style={{
              backgroundColor: "#f0f8ff",
              padding: "15px",
              borderRadius: "4px",
              marginTop: "20px",
              fontSize: "13px",
              color: "#555",
              textAlign: "center",
            }}>
              ✅ {rooms.length} room(s) configured • Dashboard updates every {refreshRate}ms
            </div>
          )}
        </div>
      )}

      {/* Webcam Test Mode Tab */}
      {activeTab === "webcam" && (
        <WebcamTestMode rooms={rooms} onRoomsUpdate={loadRooms} />
      )}

      {/* CCTV Real Mode Tab */}
      {activeTab === "cctv" && (
        <CctvRealMode rooms={rooms} onRoomsUpdate={loadRooms} />
      )}

      {activeTab === "upload" && (
        <VideoUpload rooms={rooms} />
      )}
    </div>
  );
}
