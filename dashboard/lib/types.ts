export type Priority = "P0" | "P1" | "P2" | "P3";
export type Status = "NEW" | "READ_NO_REPLY" | "REPLIED" | "MONITORING";
export type UserStatus = "open" | "done" | "snoozed";
export type Source = "telegram" | "notion" | "github" | "calendar";
export type ChatType = "dm" | "group";

export interface TriageItem {
  id: string;
  scan_id: string;
  source: Source;
  chat_name: string;
  chat_type: ChatType;
  waiting_person: string | null;
  preview: string;
  context_summary: string | null;
  draft_reply: string | null;
  priority: Priority;
  status: Status;
  tags: string[];
  last_message_at: string | null;
  waiting_since: string | null;
  waiting_days: number | null;
  scanned_at: string;
  chat_id: number | null;
  message_id: number | null;
  source_id: string | null;
  user_status: UserStatus;
  user_status_at: string | null;
}

export interface ScanInfo {
  id: string;
  scanned_at: string;
  sources: string[];
  dialogs_listed: number;
  dialogs_filtered: number;
  dialogs_classified: number;
  stats: {
    total: number;
    by_priority: { P0: number; P1: number; P2: number; P3: number };
    by_status: Record<string, number>;
  };
}

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string }> = {
  P0: { label: "Respond Today", color: "#f87171" },
  P1: { label: "This Week", color: "#fbbf24" },
  P2: { label: "Respond", color: "#4ade80" },
  P3: { label: "Monitor", color: "#94a3b8" },
};

export const SOURCE_CONFIG: Record<Source, { label: string; color: string }> = {
  telegram: { label: "TG", color: "#2AABEE" },
  notion: { label: "Notion", color: "#7c3aed" },
  github: { label: "GH", color: "#e2e8f0" },
  calendar: { label: "Cal", color: "#4ade80" },
};
