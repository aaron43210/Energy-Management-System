// Room Status Card Component
// Displays real-time status for a single room.
// Shows:
//   - Room name and occupancy status
//   - Light state (ON/OFF with visual indicator)
//   - AC state (ON/OFF with visual indicator)
//   - AI monitoring status
// Uses color coding: orange border for occupied, green for empty.
// Animates when room is occupied to draw attention.

export default function RoomCard({ room }) {
  const isOccupied = room.occupied;
  const isLightOn = room.light;
  const isAcOn = room.ac;
  const isAiRunning = room.is_running;

  return (
    <div className="card" style={{
      backgroundColor: isOccupied ? "#fff8e1" : "#f0f0f0",
      borderLeft: `5px solid ${isOccupied ? "#ff9800" : "#4CAF50"}`,
      transition: "all 0.3s ease",
      position: "relative",
      overflow: "hidden",
    }}>
      {isOccupied && (
        <div style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: "3px",
          height: "100%",
          backgroundColor: "#ff9800",
          animation: "pulse 1s infinite",
        }} />
      )}

      <div style={{ padding: "0", position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <h3 style={{ margin: 0, fontSize: "18px", color: "#333" }}>{room.id}</h3>
          <span style={{
            display: "inline-block",
            padding: "4px 8px",
            borderRadius: "12px",
            fontSize: "11px",
            fontWeight: "bold",
            backgroundColor: isOccupied ? "#ffb74d" : "#81c784",
            color: "white",
          }}>
            {isOccupied ? "OCCUPIED" : "EMPTY"}
          </span>
        </div>

        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "1fr 1fr", 
          gap: "10px",
          marginBottom: "12px",
          padding: "10px",
          backgroundColor: "rgba(255, 255, 255, 0.6)",
          borderRadius: "4px",
        }}>
          <div style={{
            padding: "8px",
            backgroundColor: isLightOn ? "#fff9c4" : "#f5f5f5",
            borderRadius: "4px",
            textAlign: "center",
            border: `2px solid ${isLightOn ? "#fbc02d" : "#e0e0e0"}`,
          }}>
            <span style={{ fontSize: "20px", display: "block" }}>Light</span>
            <span style={{ fontSize: "11px", fontWeight: "bold", color: "#666" }}>
              {isLightOn ? "ON" : "OFF"}
            </span>
          </div>
          <div style={{
            padding: "8px",
            backgroundColor: isAcOn ? "#b3e5fc" : "#f5f5f5",
            borderRadius: "4px",
            textAlign: "center",
            border: `2px solid ${isAcOn ? "#03a9f4" : "#e0e0e0"}`,
          }}>
            <span style={{ fontSize: "20px", display: "block" }}>AC</span>
            <span style={{ fontSize: "11px", fontWeight: "bold", color: "#666" }}>
              {isAcOn ? "ON" : "OFF"}
            </span>
          </div>
        </div>

        <div style={{
          padding: "10px",
          backgroundColor: isAiRunning ? "#e8f5e9" : "#fce4ec",
          borderRadius: "4px",
          border: `1px solid ${isAiRunning ? "#4CAF50" : "#e91e63"}`,
          textAlign: "center",
          fontSize: "12px",
          fontWeight: "bold",
          color: isAiRunning ? "#2e7d32" : "#c2185b",
        }}>
          {isAiRunning ? "AI Monitoring Active" : "AI Not Running"}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0% { opacity: 0.6; }
          50% { opacity: 1; }
          100% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}