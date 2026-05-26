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
    <div className="flex h-full flex-col overflow-hidden bg-[var(--color-bg)]">
      {/* Header strip */}
      <div className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[color:rgba(10,10,12,0.6)] px-4 py-3 backdrop-blur-[20px]">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <Avatar name={item.chat_name} priority={item.priority as Priority} />
            <div>
              <div className="text-[14px] font-semibold text-[var(--color-text)]">
                {item.chat_name}
              </div>
              <div className="mt-0.5 flex items-center gap-1.5 font-mono text-[11px] text-[var(--color-text-dim)]">
                {item.chat_type === "dm" ? "DM" : "Group"}
                {waitText && <span>-- {waitText}</span>}
                <SourceBadge source={item.source} />
                <span
                  className="rounded px-1 py-px text-[9px] font-semibold"
                  style={{
                    background: `${priorityConfig.color}15`,
                    color: priorityConfig.color,
                  }}
                >
                  {item.priority}
                </span>
              </div>
            </div>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={() => handleAction(snoozeItem)}
              disabled={isPending}
              className="inline-flex items-center gap-1 rounded-md px-3 py-1 font-mono text-[11px] text-[var(--color-text-ghost)] transition-colors hover:bg-[var(--color-bg-elev)] hover:text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Snooze
            </button>
            <button
              onClick={() => handleAction(markItemDone)}
              disabled={isPending}
              className="inline-flex items-center gap-1 rounded-md bg-[var(--color-ok-soft)] px-3 py-1 font-mono text-[11px] font-medium text-[var(--color-ok)] transition-colors hover:bg-[color:rgba(48,209,88,0.18)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Done
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-3">
          {item.preview && (
            <MessageBubble
              text={item.preview}
              timestamp={relativeTime(item.last_message_at)}
              side="left"
            />
          )}

          {item.context_summary && (
            <div className="border-l-2 border-[var(--color-border-strong)] py-2 pl-3">
              <div className="font-sans text-[11px] leading-[1.5] text-[var(--color-text-dim)]">
                {item.context_summary}
              </div>
            </div>
          )}

          {actionError && (
            <div className="rounded-[10px] border border-[var(--color-risk-soft)] bg-[var(--color-risk-soft)] px-3.5 py-2.5">
              <div className="font-sans text-[12px] text-[var(--color-risk)]">{actionError}</div>
            </div>
          )}
        </div>
      </div>

      <ReplyArea key={item.id} item={item} />
    </div>
  );
}
