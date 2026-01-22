import { useState } from "react";

/**
 * Simplified MJPEG Player using native img tag for better performance
 * The browser handles MJPEG streaming natively which is faster than manual parsing
 */
export default function MjpegPlayer({ src, alt = "Stream", ...props }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  return (
    <div style={{ position: "relative", width: "100%", ...props.style }}>
      {loading && !error && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#000",
            color: "#fff",
            fontSize: "14px",
          }}
        >
          Loading stream...
        </div>
      )}
      
      {error && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.7)",
            color: "red",
            fontSize: "14px",
            textAlign: "center",
            padding: "20px",
          }}
        >
          {`Stream Error: ${error}`}
        </div>
      )}
      
      {/* Native img tag handles MJPEG streaming efficiently */}
      <img
        src={src}
        alt={alt}
        onLoad={() => setLoading(false)}
        onError={(e) => {
          setError("Failed to load stream");
          setLoading(false);
        }}
        style={{
          width: "100%",
          height: "auto",
          maxHeight: "600px",
          display: loading ? "none" : "block",
          backgroundColor: "#000",
        }}
      />
    </div>
  );
}
