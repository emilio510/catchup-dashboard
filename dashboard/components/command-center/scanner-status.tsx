"use client";

interface ScannerStatusProps {
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
}

export function ScannerStatus({ scannedAt, dialogsListed, dialogsClassified }: ScannerStatusProps) {
  const scannedDate = new Date(scannedAt);
  const seconds = Math.floor((Date.now() - scannedDate.getTime()) / 1000);
  let timeAgo = "just now";
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) timeAgo = `${minutes}m ago`;
    else {
      const hours = Math.floor(minutes / 60);
      timeAgo = hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
    }
  }

  return (
    <div>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Scanner
      </div>
      <div style={{ background: "#1a2340", borderRadius: 6, padding: "10px 12px", fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
        <span
          style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#4ade80",
            marginRight: 6,
            animation: "pulse 2s infinite",
          }}
        />
        Last scan: {timeAgo}
        <br />
        {dialogsClassified}/{dialogsListed} dialogs classified
      </div>
    </div>
  );
}
