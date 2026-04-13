interface MessageBubbleProps {
  text: string;
  timestamp?: string;
  side: "left" | "right";
  italic?: boolean;
}

export function MessageBubble({ text, timestamp, side, italic }: MessageBubbleProps) {
  const isLeft = side === "left";

  return (
    <div style={{ maxWidth: "85%", marginLeft: isLeft ? 0 : "auto" }}>
      <div
        style={{
          background: isLeft ? "#141b33" : "rgba(59,130,246,0.08)",
          border: isLeft ? "1px solid #1e2a4a" : "1px solid rgba(59,130,246,0.15)",
          borderRadius: isLeft ? "10px 10px 10px 2px" : "2px 10px 10px 10px",
          padding: "12px 14px",
        }}
      >
        <div
          style={{
            fontSize: 13,
            color: "#e2e8f0",
            lineHeight: 1.6,
            fontStyle: italic ? "italic" : "normal",
            whiteSpace: "pre-wrap",
          }}
        >
          {text}
        </div>
      </div>
      {timestamp && (
        <div
          style={{
            fontSize: 10,
            color: "#475569",
            marginTop: 4,
            textAlign: isLeft ? "left" : "right",
            padding: isLeft ? "0 0 0 4px" : "0 4px 0 0",
          }}
        >
          {timestamp}
        </div>
      )}
    </div>
  );
}
