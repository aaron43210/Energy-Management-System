// CCTV Real Mode Component
// Allows connection to professional CCTV security cameras for production use.
// Features:
//   - Configure CCTV IP, username, password, and channel
//   - Connect/disconnect from cameras
//   - Poll real-time occupancy and person count
//   - Display live video stream with YOLO detections
//   - Show occupancy status and energy control state
// For use with RTSP-enabled security cameras in real buildings.
// Automatically controls energy based on detected occupancy.

import { useState, useEffect } from "react";
import { getStreamUrl } from "./api";

export default function CctvRealMode({ rooms, onRoomsUpdate }) {
  const [selectedRoom, setSelectedRoom] = useState(rooms[0]?.id || "Classroom");
  const [cctvIp, setCctvIp] = useState("");
  const [cctvUsername, setCctvUsername] = useState("");
  const [cctvPassword, setCctvPassword] = useState("");
  const [cctvChannel, setCctvChannel] = useState("0");
  const [configStatus, setConfigStatus] = useState("");
  const [connected, setConnected] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [personCount, setPersonCount] = useState(0);
  const [isOccupied, setIsOccupied] = useState(false);
  const [cctvStatus, setCctvStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  
  // Poll CCTV status every 1 second when connected
  useEffect(() => {
    if (!connected) return;
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8002/api/cctv/status/${selectedRoom}`);
        if (response.ok) {
          const data = await response.json();
          setPersonCount(data.person_count || 0);
          setIsOccupied(data.occupied || false);
          setCctvStatus(data);
        }
      } catch (err) {
        console.error("Error fetching CCTV status:", err);
      }
    }, 1000);
    
    return () => clearInterval(interval);
  }, [connected, selectedRoom]);

  const handleConnectCctv = async () => {
    if (!cctvIp || !cctvUsername || !cctvPassword) {
      setConfigStatus("Please fill in all CCTV credentials");
      return;
    }

    try {
      setConfigStatus("Connecting to camera...");
      setLoadingStatus(true);

      const response = await fetch("http://localhost:8002/api/cctv/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: selectedRoom,
          cctv_ip: cctvIp,
          cctv_username: cctvUsername,
          cctv_password: cctvPassword,
          cctv_channel: cctvChannel,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to connect");
      }

      setConfigStatus(`Connected: ${data.message}`);
      setConnected(true);
      onRoomsUpdate();
    } catch (err) {
      setConfigStatus(`Error: ${err.message}`);
      setConnected(false);
    } finally {
      setLoadingStatus(false);
    }
  };

  const handleDisconnectCctv = async () => {
    try {
      setConfigStatus("Disconnecting...");
      setLoadingStatus(true);

      const response = await fetch("http://localhost:8002/api/cctv/disconnect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: selectedRoom }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to disconnect");
      }

      setConfigStatus(`Disconnected: ${data.message}`);
      setConnected(false);
      setShowPreview(false);
      setPersonCount(0);
      setIsOccupied(false);
      setCctvStatus(null);
      onRoomsUpdate();
    } catch (err) {
      setConfigStatus(`Error: ${err.message}`);
    } finally {
      setLoadingStatus(false);
    }
  };

  return (
    <div className="section">
      <h2>CCTV Real Mode - Live Detection</h2>

      <p style={{ fontSize: "14px", color: "#666", marginBottom: "20px" }}>
        Connect to a real CCTV camera and run YOLOv8 person detection on the live feed.
      </p>

      {/* Room Selection */}
      <div style={{ marginBottom: "20px" }}>
        <label>
          <strong>Select Room:</strong>
          <select
            value={selectedRoom}
            onChange={(e) => setSelectedRoom(e.target.value)}
            disabled={connected}
            style={{ marginLeft: "10px", padding: "8px", opacity: connected ? 0.5 : 1 }}
          >
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.id}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* CCTV Configuration Form */}
      <div style={{ backgroundColor: "#f9f9f9", padding: "20px", borderRadius: "8px", marginBottom: "20px" }}>
        <h3>📷 CCTV Credentials (RTSP)</h3>

        <div style={{ marginBottom: "15px" }}>
          <label>
            <strong>CCTV IP Address:</strong>
            <input
              type="text"
              placeholder="e.g., 192.168.1.100"
              value={cctvIp}
              onChange={(e) => setCctvIp(e.target.value)}
              disabled={connected}
              style={{ marginLeft: "10px", padding: "8px", width: "200px" }}
            />
          </label>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>
            <strong>Username:</strong>
            <input
              type="text"
              placeholder="admin"
              value={cctvUsername}
              onChange={(e) => setCctvUsername(e.target.value)}
              disabled={connected}
              style={{ marginLeft: "10px", padding: "8px", width: "200px" }}
            />
          </label>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>
            <strong>Password:</strong>
            <input
              type="password"
              placeholder="••••••••"
              value={cctvPassword}
              onChange={(e) => setCctvPassword(e.target.value)}
              disabled={connected}
              style={{ marginLeft: "10px", padding: "8px", width: "200px" }}
            />
          </label>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <label>
            <strong>Channel:</strong>
            <select
              value={cctvChannel}
              onChange={(e) => setCctvChannel(e.target.value)}
              disabled={connected}
              style={{ marginLeft: "10px", padding: "8px" }}
            >
              {["0", "1", "2", "3"].map((ch) => (
                <option key={ch} value={ch}>
                  Channel {ch}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={handleConnectCctv}
            disabled={connected || loadingStatus}
            style={{
              padding: "10px 20px",
              backgroundColor: connected ? "#ccc" : "#2196F3",
              color: "white",
              border: "none",
              borderRadius: "5px",
              cursor: connected || loadingStatus ? "not-allowed" : "pointer",
              fontSize: "14px",
            }}
          >
            {loadingStatus ? "🔄 Connecting..." : "🔌 Connect CCTV"}
          </button>

          {connected && (
            <button
              onClick={handleDisconnectCctv}
              disabled={loadingStatus}
              style={{
                padding: "10px 20px",
                backgroundColor: loadingStatus ? "#ccc" : "#f44336",
                color: "white",
                border: "none",
                borderRadius: "5px",
                cursor: loadingStatus ? "not-allowed" : "pointer",
                fontSize: "14px",
              }}
            >
              {loadingStatus ? "🔄 Disconnecting..." : "🔓 Disconnect"}
            </button>
          )}
        </div>

        <p style={{ marginTop: "15px", fontSize: "12px", color: "#666" }}>
          ℹ️ RTSP URL will be constructed as:
          <br />
          <code style={{ backgroundColor: "#fff", padding: "5px", borderRadius: "3px" }}>
            rtsp://username:password@ip:554/Streaming/Channels/channel
          </code>
        </p>
      </div>

      {/* Status Display */}
      {configStatus && (
        <div
          style={{
            padding: "15px",
            marginBottom: "20px",
            backgroundColor: configStatus.includes("✅") ? "#c8e6c9" : configStatus.includes("❌") ? "#ffcdd2" : "#e3f2fd",
            borderRadius: "8px",
            fontWeight: "bold",
            border: `2px solid ${configStatus.includes("✅") ? "#4CAF50" : configStatus.includes("❌") ? "#f44336" : "#2196F3"}`,
          }}
        >
          {configStatus}
        </div>
      )}

      {/* Real-time Status */}
      {connected && cctvStatus && (
        <div style={{ marginBottom: "20px" }}>
          <h3>📊 Real-time Detection Status</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
            <div
              style={{
                padding: "15px",
                backgroundColor: "#f0f7ff",
                borderRadius: "8px",
                border: "2px solid #2196F3",
              }}
            >
              <div style={{ fontSize: "12px", color: "#666" }}>Person Count</div>
              <div style={{ fontSize: "32px", fontWeight: "bold", color: "#2196F3" }}>
                {personCount}
              </div>
            </div>

            <div
              style={{
                padding: "15px",
                backgroundColor: isOccupied ? "#fff3e0" : "#e8f5e9",
                borderRadius: "8px",
                border: `2px solid ${isOccupied ? "#ff9800" : "#4CAF50"}`,
              }}
            >
              <div style={{ fontSize: "12px", color: "#666" }}>Occupancy</div>
              <div
                style={{
                  fontSize: "24px",
                  fontWeight: "bold",
                  color: isOccupied ? "#ff9800" : "#4CAF50",
                }}
              >
                {isOccupied ? "🟠 Occupied" : "🟢 Empty"}
              </div>
            </div>

            <div
              style={{
                padding: "15px",
                backgroundColor: cctvStatus?.light ? "#fff3e0" : "#e8f5e9",
                borderRadius: "8px",
                border: "2px solid #FF9800",
              }}
            >
              <div style={{ fontSize: "12px", color: "#666" }}>Light Status</div>
              <div style={{ fontSize: "18px", fontWeight: "bold" }}>
                {cctvStatus?.light ? "💡 ON" : "⚫ OFF"}
              </div>
            </div>

            <div
              style={{
                padding: "15px",
                backgroundColor: cctvStatus?.ac ? "#e1f5fe" : "#e8f5e9",
                borderRadius: "8px",
                border: "2px solid #03A9F4",
              }}
            >
              <div style={{ fontSize: "12px", color: "#666" }}>AC Status</div>
              <div style={{ fontSize: "18px", fontWeight: "bold" }}>
                {cctvStatus?.ac ? "❄️ ON" : "⚫ OFF"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Toggle */}
      {connected && (
        <div style={{ marginBottom: "20px" }}>
          <button
            onClick={() => setShowPreview(!showPreview)}
            style={{
              padding: "12px 24px",
              fontSize: "14px",
              backgroundColor: "#FF9800",
              color: "white",
              border: "none",
              borderRadius: "5px",
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            {showPreview ? "🙈 Hide Live Preview" : "👁️ Show Live Preview"}
          </button>
        </div>
      )}

      {/* Live MJPEG Preview with YOLO Annotations */}
      {showPreview && connected && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            backgroundColor: "#f0f0f0",
            borderRadius: "8px",
            border: "2px solid #FF9800",
          }}
        >
          <h3>🎥 Live MJPEG Stream (with YOLO Detection)</h3>
          <div style={{ position: "relative", backgroundColor: "#000", borderRadius: "5px", overflow: "hidden" }}>
            <img
              key={selectedRoom}
              src={getStreamUrl(selectedRoom)}
              alt={`${selectedRoom} CCTV Stream`}
              style={{
                maxWidth: "100%",
                height: "auto",
                borderRadius: "5px",
                display: "block",
              }}
              onError={(e) => {
                e.target.style.display = "none";
                e.target.parentElement.innerHTML = `
                  <div style="padding: 50px; color: #999; text-align: center; background: #222;">
                    <div style="font-size: 18px; margin-bottom: 10px;">🔄 Waiting for stream...</div>
                    <div style="font-size: 12px;">Person detection is running in the background</div>
                  </div>
                `;
              }}
            />
          </div>
          <p style={{ marginTop: "10px", fontSize: "12px", color: "#666" }}>
            🎯 Green boxes show detected people · Numbers indicate confidence level
          </p>
        </div>
      )}

      {/* Information & Testing Guide */}
      <div
        style={{
          marginTop: "30px",
          padding: "20px",
          backgroundColor: "#fff3e0",
          borderRadius: "8px",
          fontSize: "13px",
          lineHeight: "1.6",
          border: "2px solid #FF9800",
        }}
      >
        <strong>🚀 Quick Start Guide:</strong>
        <ul style={{ marginTop: "10px", marginBottom: "15px" }}>
          <li><strong>For Testing:</strong> Use a public RTSP demo stream:
            <br/><code style={{ backgroundColor: "#fff", padding: "3px" }}>rtsp://admin:admin@192.168.88.1:554/stream1</code></li>
          <li>Enter IP, username, password, and channel</li>
          <li>Click "🔌 Connect CCTV" to start detection</li>
          <li>Click "👁️ Show Live Preview" to see the stream with YOLO detection</li>
          <li>Person count updates in real-time</li>
          <li>Lights and AC automatically turn ON when people detected, OFF when empty</li>
        </ul>

        <strong>🏢 Production Deployment:</strong>
        <ul style={{ marginTop: "10px" }}>
          <li>Ensure CCTV camera is on the same network as the server</li>
          <li>RTSP streaming must be enabled in camera settings</li>
          <li>Test RTSP URL with VLC before deployment: File → Open Network Stream</li>
          <li>Use strong passwords for camera accounts</li>
          <li>Consider firewall rules to restrict camera access</li>
          <li>The AI runs continuously, detecting occupancy and controlling energy 24/7</li>
          <li>YOLOv8 runs at ~30 FPS (depends on hardware)</li>
        </ul>

        <strong>📊 What's Happening:</strong>
        <ul style={{ marginTop: "10px" }}>
          <li>Frame capture from RTSP stream runs in background thread</li>
          <li>YOLOv8 person detection runs on each frame (class 0 only)</li>
          <li>Detected people shown with green bounding boxes + confidence %</li>
          <li>Person count updates in real-time</li>
          <li>Occupancy changes trigger automatic energy control callbacks</li>
          <li>MJPEG stream shows detection overlays for visualization</li>
        </ul>
      </div>
    </div>
  );
}
