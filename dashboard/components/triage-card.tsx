"use client";

import { useState } from "react";
import { SOURCE_CONFIG, type TriageItem } from "@/lib/types";
import { CardDetail } from "./card-detail";

interface TriageCardProps {
  item: TriageItem;
}

export function TriageCard({ item }: TriageCardProps) {
  const [expanded, setExpanded] = useState(false);
  const sourceConfig = SOURCE_CONFIG[item.source];
  const waitText = item.waiting_days != null
    ? item.waiting_days < 1 ? "<1d" : `${Math.round(item.waiting_days)}d`
    : null;

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-md p-3 text-xs">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left">
        <div className="font-semibold text-[13px] mb-1 text-[#e6edf3]">{item.chat_name}</div>
        {item.waiting_person && (
          <div className="text-[#8b949e] mb-2">
            {item.waiting_person}{waitText ? ` -- ${waitText}` : ""}
          </div>
        )}
        <div className="flex gap-1 flex-wrap">
          <span className={`px-1.5 py-0.5 rounded text-[10px] border ${sourceConfig.bgColor}`}>
            {sourceConfig.label}
          </span>
          {item.chat_type === "dm" && (
            <span className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] bg-[#30363d]/50">DM</span>
          )}
          {item.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] text-[#8b949e]">{tag}</span>
          ))}
          {waitText && (
            <span className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] text-[#d29922]">{waitText}</span>
          )}
        </div>
      </button>
      {expanded && <CardDetail item={item} />}
    </div>
  );
}
