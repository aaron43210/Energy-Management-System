import { useEffect, useMemo, useState } from "react";
import { uploadVideo, getVideoStreamUrl, cleanupVideoSession, getVideoStreamStatus } from "./api";

export default function VideoUpload({ rooms }) {
  const defaultRoom = rooms[0]?.id || "UploadedVideo";
  const [roomId, setRoomId] = useState(defaultRoom);
  const [frameSkip, setFrameSkip] = useState(5);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("Upload an mp4 or avi clip to see live detection");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showStream, setShowStream] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [videoStatus, setVideoStatus] = useState(null);

  // Poll video occupancy status every 500ms
  useEffect(() => {
    if (!showStream || !sessionId) return;
    
    const interval = setInterval(async () => {
      try {
        const data = await getVideoStreamStatus(sessionId);
        setVideoStatus(data);
      } catch (err) {
        console.error("Error fetching video status:", err);
      }
    }, 500);
    
    return () => clearInterval(interval);
  }, [showStream, sessionId]);

  useEffect(() => {
    if (rooms.length === 0) return;
    if (!rooms.find((room) => room.id === roomId)) {
      setRoomId(rooms[0].id);
    }
  }, [rooms, roomId]);

  const eventHighlights = useMemo(() => {
    if (!result?.events?.length) return [];
    return result.events.slice(0, 20);
  }, [result]);

  const handleUpload = async (e) => {
    e.preventDefault();
    setError(null);
    setShowStream(false);

    if (!file) {
      setError("Choose a video file first.");
      return;
    }

    setUploading(true);
    setStatus("Analyzing and processing video...");
    setResult(null);

    try {
      const data = await uploadVideo(roomId, file, frameSkip);
      setResult(data);
      setSessionId(data.session_id);
      setStatus("Analysis complete. Starting live stream...");
      setShowStream(true);
      setVideoStatus({
        occupied: false,
        person_count: 0,
        light: false,
        ac: false
      });
    } catch (err) {
      setError(err.message || "Upload failed");
      setStatus("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleCleanup = async () => {
    if (sessionId) {
      try {
        await cleanupVideoSession(sessionId);
        setSessionId(null);
      } catch (err) {
        console.error("Cleanup error:", err);
      }
    }
    setResult(null);
    setShowStream(false);
    setFile(null);
    setVideoStatus(null);
    setStatus("Upload an mp4 or avi clip to see live detection");
  };

  return (
    <div className="section">
      <h2>📹 Video Upload with Live Detection</h2>
      <p style={{ fontSize: "14px", color: "#555", marginBottom: "16px" }}>
        Upload a video file to see real-time YOLO person detection with live power state updates. Watch detection boxes appear and lights/AC toggle as people are detected.
      </p>

      <form
        onSubmit={handleUpload}
        style={{
          backgroundColor: "#f9f9f9",
          padding: "16px",
          borderRadius: "10px",
          border: "1px solid #e0e0e0",
          marginBottom: "16px",
          display: "grid",
          gap: "12px",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          alignItems: "center",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "13px" }}>
          Room label
          <select
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            disabled={uploading}
            style={{ padding: "10px", borderRadius: "6px", border: "1px solid #ccc", opacity: uploading ? 0.6 : 1 }}
          >
            {rooms.map((room) => (
              <option key={room.id} value={room.id}>
                {room.id}
              </option>
            ))}
            <option value="UploadedVideo">UploadedVideo</option>
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "13px" }}>
          Frame skip (1=every frame, 5=every 5th)
          <input
            type="number"
            min="1"
            max="12"
            value={frameSkip}
            onChange={(e) => setFrameSkip(Number(e.target.value))}
            disabled={uploading}
            style={{ padding: "10px", borderRadius: "6px", border: "1px solid #ccc", opacity: uploading ? 0.6 : 1 }}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "13px" }}>
          Video file (mp4 / avi / mov)
          <input
            type="file"
            accept="video/mp4,video/x-m4v,video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={uploading}
            style={{ padding: "8px", borderRadius: "6px", border: "1px solid #ccc", opacity: uploading ? 0.6 : 1 }}
          />
        </label>

        <button
          type="submit"
          disabled={uploading}
          style={{
            padding: "12px 18px",
            backgroundColor: uploading ? "#ccc" : "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: uploading ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {uploading ? "Processing..." : "📤 Upload & Analyze"}
        </button>
      </form>

      <div
        style={{
          padding: "12px",
          borderRadius: "8px",
          border: "1px solid #e0e0e0",
          backgroundColor: error ? "#ffe0e0" : showStream ? "#fff3e0" : "#eef6ff",
          color: error ? "#c62828" : "#333",
          marginBottom: "16px",
          fontWeight: "600",
        }}
      >
        {error ? error : status}
      </div>

      {/* Live Video Stream with Status */}
      {showStream && sessionId && (
        <div
          style={{
            padding: "20px",
            backgroundColor: "#f0f0f0",
            borderRadius: "12px",
            border: "2px solid #FF9800",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ margin: 0 }}>🎥 Live Stream with YOLO Detection</h3>
            <button
              onClick={handleCleanup}
              style={{
                padding: "8px 12px",
                backgroundColor: "#f44336",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
              }}
            >
              Stop & Clear
            </button>
          </div>

          {/* Status Cards */}
          {videoStatus && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", marginBottom: "12px" }}>
              <StatusIndicator
                label="Person Count"
                value={videoStatus.person_count}
                color="#2196F3"
                unit="people"
              />
              <StatusIndicator
                label="Occupancy"
                value={videoStatus.occupied ? "🟠 Occupied" : "🟢 Empty"}
                color={videoStatus.occupied ? "#ff9800" : "#4CAF50"}
              />
              <StatusIndicator
                label="Light"
                value={videoStatus.light ? "💡 ON" : "⚫ OFF"}
                color={videoStatus.light ? "#4CAF50" : "#999"}
              />
              <StatusIndicator
                label="AC"
                value={videoStatus.ac ? "❄️ ON" : "⚫ OFF"}
                color={videoStatus.ac ? "#2196F3" : "#999"}
              />
            </div>
          )}

          <div
            style={{
              backgroundColor: "#000",
              borderRadius: "8px",
              overflow: "hidden",
              border: "2px solid #333",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: "400px",
            }}
          >
            <img
              key={sessionId}
              src={getVideoStreamUrl(sessionId)}
              alt="Live video with detection"
              style={{
                maxWidth: "100%",
                height: "auto",
                display: "block",
              }}
              onError={(e) => {
                console.error("Stream error");
              }}
            />
          </div>
          <p style={{ marginTop: "10px", fontSize: "12px", color: "#666", textAlign: "center" }}>
            🎯 Green boxes = detected persons · Status updates per frame
          </p>
        </div>
      )}

      {/* Analysis Results */}
      {result && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "20px" }}>
            <StatCard label="Frames analyzed" value={`${result.frames_analyzed} / ${result.frames_total}`} />
            <StatCard label="Video duration" value={`${result.duration_seconds}s @ ${result.fps} fps`} />
            <StatCard label="Occupied frames" value={`${result.occupied_frames}`} />
            <StatCard label="Occupancy ratio" value={`${Math.round(result.occupancy_ratio * 100)}%`} />
          </div>

          {eventHighlights.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <h3 style={{ marginBottom: "8px" }}>⚡ Power State Timeline (first 20 changes)</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {eventHighlights.map((evt, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "12px",
                      border: "1px solid #e0e0e0",
                      borderRadius: "8px",
                      backgroundColor: evt.occupied ? "#fff3e0" : "#e8f5e9",
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                      gap: "6px",
                      fontSize: "13px",
                    }}
                  >
                    <strong style={{ color: "#333" }}>t={evt.time_seconds}s</strong>
                    <span>👥 People: {evt.person_count}</span>
                    <span>Occupied: {evt.occupied ? "Yes" : "No"}</span>
                    <span>💡 Light: {evt.light ? "ON" : "OFF"}</span>
                    <span>❄️ AC: {evt.ac ? "ON" : "OFF"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusIndicator({ label, value, color, unit }) {
  return (
    <div
      style={{
        padding: "12px",
        backgroundColor: "#fff",
        borderRadius: "10px",
        border: `2px solid ${color}`,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
      }}
    >
      <div style={{ fontSize: "11px", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "18px", fontWeight: "700", marginTop: "4px", color }}>{value}</div>
      {unit && <div style={{ fontSize: "9px", color: "#999" }}>{unit}</div>}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div
      style={{
        padding: "14px",
        backgroundColor: "#fff",
        borderRadius: "10px",
        border: "1px solid #e0e0e0",
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
      }}
    >
      <div style={{ fontSize: "12px", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "20px", fontWeight: "700", marginTop: "6px" }}>{value}</div>
    </div>
  );
}
