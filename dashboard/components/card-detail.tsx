"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { TriageItem } from "@/lib/types";
import { markItemDone, snoozeItem, sendReply } from "@/app/actions";

interface CardDetailProps {
  item: TriageItem;
}

export function CardDetail({ item }: CardDetailProps) {
  const [isPending, startTransition] = useTransition();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [replyText, setReplyText] = useState(item.draft_reply ?? "");
  const [sent, setSent] = useState(false);
  const router = useRouter();

  function handleAction(action: (id: string) => Promise<void>, actionName: string) {
    setPendingAction(actionName);
    startTransition(async () => {
      await action(item.id);
      router.refresh();
      setPendingAction(null);
    });
  }

  function handleSend() {
    if (!replyText.trim() || !item.chat_id) return;
    setPendingAction("send");
    startTransition(async () => {
      await sendReply(item.id, item.chat_id!, replyText);
      setSent(true);
      router.refresh();
      setPendingAction(null);
    });
  }

  return (
    <div className="mt-3 pt-3 border-t border-[#30363d]">
      {item.context_summary && (
        <p className="text-[#8b949e] text-xs mb-2">{item.context_summary}</p>
      )}
      {!sent && (
        <div className="bg-[#0d1117] rounded p-2 mb-3">
          <div className="text-[10px] text-[#8b949e] mb-1 uppercase tracking-wide">
            {item.draft_reply ? "Edit & send reply" : "Write a reply"}
          </div>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={3}
            className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1.5 text-xs text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] resize-y"
            placeholder="Type your reply..."
          />
        </div>
      )}
      {sent && (
        <div className="bg-[#238636]/20 border border-[#238636]/40 rounded p-2 mb-3">
          <p className="text-[10px] text-[#3fb950]">Reply queued -- will be sent within 2 minutes</p>
        </div>
      )}
      <div className="flex gap-2">
        {!sent && item.chat_id && (
          <button
            onClick={handleSend}
            disabled={isPending || !replyText.trim()}
            className="px-2 py-1 text-[10px] rounded bg-[#1f6feb] hover:bg-[#388bfd] text-white disabled:opacity-50"
          >
            {pendingAction === "send" ? "Queuing..." : "Send reply"}
          </button>
        )}
        <button
          onClick={() => handleAction(markItemDone, "done")}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#238636] hover:bg-[#2ea043] text-white disabled:opacity-50"
        >
          {pendingAction === "done" ? "..." : "Done"}
        </button>
        <button
          onClick={() => handleAction(snoozeItem, "snooze")}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#30363d] hover:bg-[#484f58] text-[#8b949e] disabled:opacity-50"
        >
          {pendingAction === "snooze" ? "..." : "Snooze"}
        </button>
      </div>
    </div>
  );
}
