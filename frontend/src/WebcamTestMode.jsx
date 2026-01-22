// Webcam Demo Mode Component
// Allows users to test the system using their device camera.
// Features:
//   - Start/stop buttons to control webcam demo
//   - Status display showing if camera is running
//   - Live status monitoring every 2 seconds
//   - Instructions for using the demo
//   - Technical details about the implementation
// Perfect for demonstrations without needing CCTV hardware.
// Uses backend endpoints to start/stop camera process.

import { useState, useEffect } from "react";
import MjpegPlayer from "./MjpegPlayer";

export default function WebcamTestMode({ rooms, onRoomsUpdate }) {
  const [webcamRunning, setWebcamRunning] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [lastUpdate, setLastUpdate] = useState(null);

  // Check webcam status on mount and periodically
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8002/api/webcam/test/status");
        const data = await response.json();
        setWebcamRunning(data.status === "running");
      } catch (err) {
        console.error("Error checking webcam status:", err);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStartWebcam = async () => {
    try {
      setStatus("Starting camera...");

      const response = await fetch(
        "http://127.0.0.1:8002/api/webcam/test/start",
        { method: "POST" }
      );

      const data = await response.json();

      if (data.status === "Webcam test started") {
        setWebcamRunning(true);
        setStatus(
          "Camera started. Check your device screen for detection."
        );
        setLastUpdate(new Date().toLocaleTimeString());
      } else if (data.status === "Webcam test already running") {
        setStatus("Camera already running");
        setWebcamRunning(true);
      } else {
        setStatus(`Error: ${data.detail || "Unknown error"}`);
      }

      onRoomsUpdate();
    } catch (err) {
      setStatus(`✗ Connection error: ${err.message}`);
      console.error(err);
    }
  };

  const handleStopWebcam = async () => {
    try {
      setStatus("Stopping camera...");

      const response = await fetch(
        "http://127.0.0.1:8002/api/webcam/test/stop",
        { method: "POST" }
      );

      const data = await response.json();

      if (data.status === "Webcam test stopped") {
        setWebcamRunning(false);
        setStatus("Camera stopped");
      } else if (data.status === "Webcam test not running") {
        setStatus("Camera was not running");
        setWebcamRunning(false);
      } else {
        setStatus(`Error: ${data.detail || "Unknown error"}`);
      }

      onRoomsUpdate();
    } catch (err) {
      setStatus(`Connection error: ${err.message}`);
      console.error(err);
    }
  };

  return (
    <div className="section">
      <h2>Webcam Test Mode</h2>

      <p style={{ fontSize: "14px", color: "#666", marginBottom: "20px" }}>
        Uses your device camera to detect people in real-time. When people are detected,
        lights turn ON. When empty, lights turn OFF.
      </p>

      <div
        style={{
          padding: "15px",
          marginBottom: "20px",
          backgroundColor:
            status.includes("Camera started") && webcamRunning
              ? "#c8e6c9"
              : status.includes("Error")
                ? "#ffcdd2"
                : "#e3f2fd",
          borderRadius: "8px",
          fontWeight: "bold",
          fontSize: "15px",
        }}
      >
        {status}
      </div>

      <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
        <button
          onClick={handleStartWebcam}
          disabled={webcamRunning}
          style={{
            padding: "14px 28px",
            fontSize: "16px",
            fontWeight: "bold",
            backgroundColor: webcamRunning ? "#ccc" : "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "5px",
            cursor: webcamRunning ? "not-allowed" : "pointer",
          }}
        >
          Start Camera Detection
        </button>

        <button
          onClick={handleStopWebcam}
          disabled={!webcamRunning}
          style={{
            padding: "14px 28px",
            fontSize: "16px",
            fontWeight: "bold",
            backgroundColor: !webcamRunning ? "#ccc" : "#f44336",
            color: "white",
            border: "none",
            borderRadius: "5px",
            cursor: !webcamRunning ? "not-allowed" : "pointer",
          }}
        >
          Stop Camera
        </button>
      </div>

      {webcamRunning && (
        <div
          style={{
            padding: "15px",
            marginBottom: "20px",
            backgroundColor: "#fff9c4",
            borderRadius: "8px",
            border: "2px solid #fbc02d",
          }}
        >
          <strong>Camera is running</strong>
          <p style={{ margin: "10px 0 0 0", fontSize: "14px" }}>
            Live camera feed displayed below with real-time person detection
          </p>
          {lastUpdate && (
            <p style={{ margin: "10px 0 0 0", fontSize: "12px", color: "#666" }}>
              Last updated: {lastUpdate}
            </p>
          )}
        </div>
      )}

      {webcamRunning && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "8px",
            overflow: "hidden",
            border: "2px solid #ddd",
            backgroundColor: "#000",
            minHeight: "400px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <MjpegPlayer
            key="webcam-stream"
            src="http://127.0.0.1:8002/api/webcam/stream"
            alt="Live webcam feed"
          />
        </div>
      )}

      <div
        style={{
          padding: "15px",
          backgroundColor: "#e8f5e9",
          borderRadius: "8px",
          fontSize: "14px",
          lineHeight: "1.6",
        }}
      >
        <strong>How to use:</strong>
        <ol style={{ marginTop: "10px" }}>
          <li>Click "Start Camera Detection" button above</li>
          <li>Live camera feed will appear below with detection boxes</li>
          <li>Move in front of the camera - lights turn ON</li>
          <li>Step away - lights turn OFF</li>
          <li>Check the Dashboard tab to see real-time updates</li>
        </ol>
      </div>

      <div
        style={{
          marginTop: "20px",
          padding: "15px",
          backgroundColor: "#f5f5f5",
          borderRadius: "8px",
          fontSize: "12px",
          color: "#666",
          borderLeft: "4px solid #2196F3",
        }}
      >
        <strong>Technical:</strong>
        <ul style={{ marginTop: "8px" }}>
          <li>Uses YOLOv8 person detection</li>
          <li>Runs as background process on backend</li>
          <li>Sends occupancy updates to API</li>
          <li>Energy logic controls lights automatically</li>
        </ul>
      </div>
    </div>
  );
}
