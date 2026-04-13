"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { markItemDone, snoozeItem } from "@/app/actions";
import { Avatar } from "@/components/ui/avatar";
import { SourceBadge } from "@/components/ui/source-badge";
import { MessageBubble } from "./message-bubble";
import { ReplyArea } from "./reply-area";
import type { TriageItem, Priority } from "@/lib/types";
import { PRIORITY_CONFIG } from "@/lib/types";

interface DetailConversationProps {
  item: TriageItem;
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function DetailConversation({ item }: DetailConversationProps) {
  const [isPending, startTransition] = useTransition();
  const [actionError, setActionError] = useState<string | null>(null);
  const router = useRouter();
  const priorityConfig = PRIORITY_CONFIG[item.priority as Priority];
  const waitText =
    item.waiting_days != null
      ? item.waiting_days < 1
        ? "<1d waiting"
        : `${Math.round(item.waiting_days)}d waiting`
      : null;

  function handleAction(action: (id: string) => Promise<void>) {
    setActionError(null);
    startTransition(async () => {
      try {
        await action(item.id);
        router.refresh();
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Action failed");
      }
    });
  }

  return (
    <div style={{ padding: "24px 32px", height: "100%", overflowY: "auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 20,
          paddingBottom: 16,
          borderBottom: "1px solid #1e2a4a",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Avatar name={item.chat_name} priority={item.priority as Priority} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0" }}>
              {item.chat_name}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "#64748b",
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginTop: 2,
              }}
            >
              {item.chat_type === "dm" ? "DM" : "Group"}
              {waitText && <span>-- {waitText}</span>}
              <SourceBadge source={item.source} />
              <span
                style={{
                  fontSize: 9,
                  padding: "1px 5px",
                  borderRadius: 3,
                  background: `${priorityConfig.color}15`,
                  color: priorityConfig.color,
                  fontWeight: 600,
                }}
              >
                {item.priority}
              </span>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => handleAction(snoozeItem)}
            disabled={isPending}
            style={{
              padding: "4px 12px",
              borderRadius: 6,
              fontSize: 11,
              border: "1px solid transparent",
              background: "transparent",
              color: "#64748b",
              cursor: "pointer",
              opacity: isPending ? 0.5 : 1,
            }}
          >
            Snooze
          </button>
          <button
            onClick={() => handleAction(markItemDone)}
            disabled={isPending}
            style={{
              padding: "4px 12px",
              borderRadius: 6,
              fontSize: 11,
              border: "none",
              background: "#238636",
              color: "white",
              cursor: "pointer",
              opacity: isPending ? 0.5 : 1,
            }}
          >
            Done
          </button>
        </div>
      </div>

      {item.preview && (
        <div style={{ marginBottom: 14 }}>
          <MessageBubble
            text={item.preview}
            timestamp={relativeTime(item.last_message_at)}
            side="left"
          />
        </div>
      )}

      {item.context_summary && (
        <div
          style={{
            borderLeft: "2px solid #60a5fa",
            padding: "8px 12px",
            marginBottom: 14,
          }}
        >
          <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.5 }}>
            {item.context_summary}
          </div>
        </div>
      )}

      {actionError && (
        <div
          style={{
            background: "rgba(248,113,113,0.08)",
            border: "1px solid rgba(248,113,113,0.2)",
            borderRadius: 10,
            padding: "10px 14px",
            marginBottom: 14,
          }}
        >
          <div style={{ fontSize: 12, color: "#f87171" }}>{actionError}</div>
        </div>
      )}

      <ReplyArea key={item.id} item={item} />
    </div>
  );
}
