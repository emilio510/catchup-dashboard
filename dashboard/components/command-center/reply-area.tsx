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
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const sourceLabel = SOURCE_CONFIG[item.source]?.label ?? item.source;

  function handleSend() {
    if (!replyText.trim() || !item.chat_id) return;
    setError(null);
    startTransition(async () => {
      try {
        await sendReply(item.id, replyText);
        setSent(true);
        router.refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send reply");
      }
    });
  }

  if (sent) {
    return (
      <div className="glass m-3 p-3">
        <div className="font-sans text-[12px] text-[var(--color-ok)]">
          Reply queued -- will be sent within 2 minutes
        </div>
      </div>
    );
  }

  const errorBanner = error ? (
    <div className="mt-2 rounded-[10px] border border-[var(--color-risk-soft)] bg-[var(--color-risk-soft)] px-3.5 py-2.5">
      <div className="font-sans text-[12px] text-[var(--color-risk)]">{error}</div>
    </div>
  ) : null;

  if (!editing && item.draft_reply) {
    return (
      <div className="glass m-3 p-3">
        <button onClick={() => setEditing(true)} className="w-full text-left">
          <MessageBubble text={item.draft_reply} side="right" italic />
        </button>
        <div className="mt-1 pr-1 text-right font-mono text-[10px] text-[var(--color-text-ghost)]">
          AI-drafted -- click to edit
        </div>
        {item.chat_id && (
          <div className="mt-2 flex justify-end">
            <button
              onClick={handleSend}
              disabled={isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-ok-soft)] px-2.5 py-1 font-mono text-[11px] font-medium text-[var(--color-ok)] transition-colors hover:bg-[color:rgba(48,209,88,0.18)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPending ? "Queuing..." : `Send via ${sourceLabel}`}
            </button>
          </div>
        )}
        {errorBanner}
      </div>
    );
  }

  return (
    <div className="glass m-3 p-3">
      <div className="mb-1.5 font-mono text-[9px] uppercase tracking-[0.5px] text-[var(--color-text-ghost)]">
        Your Reply
      </div>
      <div className="rounded-[10px] border border-[var(--color-border)] bg-[var(--color-bg)] transition-colors focus-within:border-[var(--color-border-strong)]">
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          maxLength={4096}
          placeholder="Type your reply..."
          className="w-full resize-y bg-transparent px-3.5 py-3 font-sans text-[13px] leading-[1.5] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:outline-none"
          style={{ minHeight: 80 }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] text-[var(--color-text-ghost)]">
          {item.draft_reply ? "AI-drafted -- edit before sending" : ""}
        </span>
        {item.chat_id && (
          <button
            onClick={handleSend}
            disabled={isPending || !replyText.trim()}
            className="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-ok-soft)] px-2.5 py-1 font-mono text-[11px] font-medium text-[var(--color-ok)] transition-colors hover:bg-[color:rgba(48,209,88,0.18)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? "Queuing..." : `Send via ${sourceLabel}`}
          </button>
        )}
      </div>
      {errorBanner}
    </div>
  );
}
