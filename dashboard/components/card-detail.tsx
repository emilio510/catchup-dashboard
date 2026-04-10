"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import type { TriageItem } from "@/lib/types";
import { markItemDone, snoozeItem } from "@/app/actions";

interface CardDetailProps {
  item: TriageItem;
}

export function CardDetail({ item }: CardDetailProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleAction(action: (id: string) => Promise<void>) {
    startTransition(async () => {
      await action(item.id);
      router.refresh();
    });
  }

  return (
    <div className="mt-3 pt-3 border-t border-[#30363d]">
      {item.context_summary && (
        <p className="text-[#8b949e] text-xs mb-2">{item.context_summary}</p>
      )}
      {item.draft_reply && (
        <div className="bg-[#0d1117] rounded p-2 mb-3">
          <div className="text-[10px] text-[#8b949e] mb-1 uppercase tracking-wide">Draft reply</div>
          <p className="text-xs text-[#e6edf3]">{item.draft_reply}</p>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => handleAction(markItemDone)}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#238636] hover:bg-[#2ea043] text-white disabled:opacity-50"
        >
          {isPending ? "..." : "Done"}
        </button>
        <button
          onClick={() => handleAction(snoozeItem)}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#30363d] hover:bg-[#484f58] text-[#8b949e] disabled:opacity-50"
        >
          {isPending ? "..." : "Snooze"}
        </button>
      </div>
    </div>
  );
}
