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

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; dotColor: string }> = {
  P0: { label: "Respond Today", color: "#f85149", dotColor: "bg-red-500" },
  P1: { label: "This Week", color: "#d29922", dotColor: "bg-amber-500" },
  P2: { label: "Respond", color: "#3fb950", dotColor: "bg-green-500" },
  P3: { label: "Monitor", color: "#8b949e", dotColor: "bg-gray-500" },
};

export const SOURCE_CONFIG: Record<Source, { label: string; color: string; bgColor: string }> = {
  telegram: { label: "TG", color: "#1f6feb", bgColor: "bg-blue-500/20 border-blue-500" },
  notion: { label: "Notion", color: "#7c3aed", bgColor: "bg-purple-500/20 border-purple-500" },
  github: { label: "GH", color: "#e6edf3", bgColor: "bg-gray-500/20 border-gray-500" },
  calendar: { label: "Cal", color: "#3fb950", bgColor: "bg-green-500/20 border-green-500" },
};
