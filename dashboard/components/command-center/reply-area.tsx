"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { sendReply } from "@/app/actions";
import { SOURCE_CONFIG, type TriageItem } from "@/lib/types";
import { MessageBubble } from "./message-bubble";

interface ReplyAreaProps {
  item: TriageItem;
}

export function ReplyArea({ item }: ReplyAreaProps) {
  const [editing, setEditing] = useState(!item.draft_reply);
  const [replyText, setReplyText] = useState(item.draft_reply ?? "");
  const [sent, setSent] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const sourceLabel = SOURCE_CONFIG[item.source]?.label ?? item.source;

  function handleSend() {
    if (!replyText.trim() || !item.chat_id) return;
    startTransition(async () => {
      await sendReply(item.id, replyText);
      setSent(true);
      router.refresh();
    });
  }

  if (sent) {
    return (
      <div
        style={{
          background: "rgba(74,222,128,0.08)",
          border: "1px solid rgba(74,222,128,0.2)",
          borderRadius: 10,
          padding: "10px 14px",
          marginTop: 14,
        }}
      >
        <div style={{ fontSize: 12, color: "#4ade80" }}>
          Reply queued -- will be sent within 2 minutes
        </div>
      </div>
    );
  }

  if (!editing && item.draft_reply) {
    return (
      <div style={{ marginTop: 14 }}>
        <button onClick={() => setEditing(true)} className="w-full text-left">
          <MessageBubble text={item.draft_reply} side="right" italic />
        </button>
        <div
          style={{
            fontSize: 10,
            color: "#475569",
            marginTop: 4,
            textAlign: "right",
            paddingRight: 4,
          }}
        >
          AI-drafted -- click to edit
        </div>
        {item.chat_id && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            <button
              onClick={handleSend}
              disabled={isPending}
              style={{
                padding: "6px 16px",
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                background: "#3b82f6",
                color: "white",
                border: "none",
                cursor: "pointer",
                opacity: isPending ? 0.5 : 1,
              }}
            >
              {isPending ? "Queuing..." : `Send via ${sourceLabel}`}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ marginTop: 14 }}>
      <div
        style={{
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          color: "#475569",
          marginBottom: 6,
        }}
      >
        Your Reply
      </div>
      <textarea
        value={replyText}
        onChange={(e) => setReplyText(e.target.value)}
        placeholder="Type your reply..."
        style={{
          width: "100%",
          minHeight: 80,
          background: "#0c0f1a",
          border: "1px solid #1e2a4a",
          borderRadius: 10,
          padding: "12px 14px",
          fontSize: 13,
          color: "#e2e8f0",
          resize: "vertical",
          fontFamily: "inherit",
          lineHeight: 1.5,
          outline: "none",
        }}
        onFocus={(e) => (e.currentTarget.style.borderColor = "#60a5fa")}
        onBlur={(e) => (e.currentTarget.style.borderColor = "#1e2a4a")}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 8,
        }}
      >
        <span style={{ fontSize: 10, color: "#475569" }}>
          {item.draft_reply ? "AI-drafted -- edit before sending" : ""}
        </span>
        {item.chat_id && (
          <button
            onClick={handleSend}
            disabled={isPending || !replyText.trim()}
            style={{
              padding: "6px 16px",
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              background: "#3b82f6",
              color: "white",
              border: "none",
              cursor: "pointer",
              opacity: isPending || !replyText.trim() ? 0.5 : 1,
            }}
          >
            {isPending ? "Queuing..." : `Send via ${sourceLabel}`}
          </button>
        )}
      </div>
    </div>
  );
}
