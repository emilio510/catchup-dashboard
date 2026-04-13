import { DetailConversation } from "./detail-conversation";
import type { TriageItem, Priority } from "@/lib/types";

interface DetailPaneProps {
  item: TriageItem | null;
  byPriority: Record<Priority, number>;
  total: number;
}

export function DetailPane({ item, byPriority, total }: DetailPaneProps) {
  if (!item) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          color: "#475569",
          gap: 8,
        }}
      >
        <div style={{ fontSize: 40, opacity: 0.2 }}>&#9993;</div>
        <div style={{ fontSize: 13 }}>Select an item to view details</div>
        <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
          {byPriority.P0 > 0 && (
            <span style={{ color: "#f87171" }}>{byPriority.P0} urgent</span>
          )}
          {byPriority.P0 > 0 && byPriority.P1 > 0 && " | "}
          {byPriority.P1 > 0 && (
            <span style={{ color: "#fbbf24" }}>{byPriority.P1} this week</span>
          )}
          {(byPriority.P0 > 0 || byPriority.P1 > 0) && " | "}
          <span>{total} total</span>
        </div>
      </div>
    );
  }

  return <DetailConversation key={item.id} item={item} />;
}
