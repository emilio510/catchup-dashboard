import { neon } from "@neondatabase/serverless";

function getDb() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not set");
  }
  return neon(databaseUrl);
}

export async function getLatestScan(): Promise<{
  id: string;
  scanned_at: string;
  stats: { total: number; by_priority: { P0: number; P1: number; P2: number; P3: number }; by_status: Record<string, number> };
  dialogs_listed: number;
  dialogs_filtered: number;
  dialogs_classified: number;
} | null> {
  const sql = getDb();
  const rows = await sql`
    SELECT id, scanned_at, stats, dialogs_listed, dialogs_filtered, dialogs_classified
    FROM scans
    ORDER BY scanned_at DESC
    LIMIT 1
  `;
  if (rows.length === 0) return null;
  const row = rows[0];
  return {
    id: row.id as string,
    scanned_at: row.scanned_at as string,
    stats: typeof row.stats === "string" ? JSON.parse(row.stats) : row.stats as {
      total: number;
      by_priority: { P0: number; P1: number; P2: number; P3: number };
      by_status: Record<string, number>;
    },
    dialogs_listed: row.dialogs_listed as number,
    dialogs_filtered: row.dialogs_filtered as number,
    dialogs_classified: row.dialogs_classified as number,
  };
}

export async function getTriageItems(scanId: string, filters?: {
  userStatus?: string;
  source?: string;
  chatType?: string;
  search?: string;
}): Promise<import("./types").TriageItem[]> {
  const sql = getDb();
  const userStatus = filters?.userStatus ?? "open";

  const escapedSearch = (filters?.search ?? "").replace(/[%_\\]/g, "\\$&");

  const rows = await sql`
    SELECT *
    FROM triage_items
    WHERE scan_id = ${scanId}::uuid
      AND user_status = ${userStatus}
      AND (${filters?.source ?? ""} = '' OR source = ${filters?.source ?? ""})
      AND (${filters?.chatType ?? ""} = '' OR chat_type = ${filters?.chatType ?? ""})
      AND (
        ${filters?.search ?? ""} = ''
        OR chat_name ILIKE ${"%" + escapedSearch + "%"}
        OR waiting_person ILIKE ${"%" + escapedSearch + "%"}
        OR preview ILIKE ${"%" + escapedSearch + "%"}
      )
    ORDER BY
      CASE priority
        WHEN 'P0' THEN 0
        WHEN 'P1' THEN 1
        WHEN 'P2' THEN 2
        WHEN 'P3' THEN 3
      END,
      waiting_days DESC NULLS LAST
  `;

  return rows as unknown as import("./types").TriageItem[];
}

export async function updateItemStatus(
  itemId: string,
  userStatus: "open" | "done" | "snoozed"
): Promise<void> {
  const sql = getDb();
  await sql`
    UPDATE triage_items
    SET user_status = ${userStatus}, user_status_at = now()
    WHERE id = ${itemId}::uuid
  `;
}
