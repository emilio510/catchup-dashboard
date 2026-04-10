"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, Suspense } from "react";
import { SearchInput } from "./search-input";

interface FilterBarProps {
  currentStatus?: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
}

export function FilterBar(props: FilterBarProps) {
  return (
    <Suspense fallback={<div className="h-8" />}>
      <FilterBarInner {...props} />
    </Suspense>
  );
}

function FilterBarInner({ currentStatus, currentSource, currentChatType, currentSearch }: FilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const setFilter = useCallback((key: string, value: string | undefined) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  const handleSearch = useCallback((v: string) => setFilter("search", v || undefined), [setFilter]);

  const statusFilters = [
    { value: "open", label: "To respond" },
    { value: "done", label: "Done" },
    { value: "snoozed", label: "Snoozed" },
  ];

  const sourceFilters = [
    { value: undefined as string | undefined, label: "All sources" },
    { value: "telegram", label: "Telegram" },
    { value: "notion", label: "Notion" },
    { value: "github", label: "GitHub" },
  ];

  const typeFilters = [
    { value: undefined as string | undefined, label: "All types" },
    { value: "dm", label: "DMs only" },
    { value: "group", label: "Groups only" },
  ];

  return (
    <div className="flex gap-2 flex-wrap items-center">
      {statusFilters.map((f) => (
        <FilterChip key={f.value} label={f.label} active={currentStatus === f.value} onClick={() => setFilter("status", f.value)} />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      {sourceFilters.map((f) => (
        <FilterChip key={f.label} label={f.label} active={currentSource === f.value} onClick={() => setFilter("source", f.value)} />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      {typeFilters.map((f) => (
        <FilterChip key={f.label} label={f.label} active={currentChatType === f.value} onClick={() => setFilter("chatType", f.value)} />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      <SearchInput currentSearch={currentSearch} onSearch={handleSearch} />
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs border transition-colors ${
        active
          ? "bg-[#388bfd22] border-[#388bfd] text-[#388bfd]"
          : "bg-[#161b22] border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
      }`}
    >
      {label}
    </button>
  );
}
