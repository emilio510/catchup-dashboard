"use client";

import { useState, useEffect } from "react";

interface SearchInputProps {
  currentSearch?: string;
  onSearch: (value: string) => void;
}

export function SearchInput({ currentSearch, onSearch }: SearchInputProps) {
  const [value, setValue] = useState(currentSearch ?? "");

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (value !== (currentSearch ?? "")) {
        onSearch(value);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [value, currentSearch, onSearch]);

  return (
    <input
      type="text"
      placeholder="Search..."
      value={value}
      onChange={(e) => setValue(e.target.value)}
      className="bg-[#161b22] border border-[#30363d] rounded-full px-3 py-1 text-xs text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] w-48"
    />
  );
}
