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

export async function getTriageItems(filters?: {
  userStatus?: string;
  source?: string;
  chatType?: string;
  search?: string;
}): Promise<import("./types").TriageItem[]> {
  const sql = getDb();
  const userStatus = filters?.userStatus ?? "open";

  const escapedSearch = (filters?.search ?? "").replace(/[%_\\]/g, "\\$&");

  // Get the most recent triage item per chat (DISTINCT ON chat_id)
  // This works across scans -- dedup may skip re-classifying unchanged chats
  // but their items from previous scans are still valid and shown here
  const rows = await sql`
    SELECT * FROM (
      SELECT DISTINCT ON (chat_id) *
      FROM triage_items
      ORDER BY chat_id, scanned_at DESC
    ) latest
    WHERE user_status = ${userStatus}
      AND (${filters?.source ?? ""} = '' OR source = ${filters?.source ?? ""})
      AND (${filters?.chatType ?? ""} = '' OR chat_type = ${filters?.chatType ?? ""})
      AND (
        ${filters?.search ?? ""} = ''
        OR chat_name ILIKE ${"%" + escapedSearch + "%"}
        OR waiting_person ILIKE ${"%" + escapedSearch + "%"}
        OR preview ILIKE ${"%" + escapedSearch + "%"}
      )
  `;

  // Sort by priority then waiting_days (DISTINCT ON requires ORDER BY chat_id first)
  const priorityOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
  const sorted = [...rows].sort((a, b) => {
    const pa = priorityOrder[a.priority as string] ?? 99;
    const pb = priorityOrder[b.priority as string] ?? 99;
    if (pa !== pb) return pa - pb;
    return ((b.waiting_days as number) ?? 0) - ((a.waiting_days as number) ?? 0);
  });

  return sorted as unknown as import("./types").TriageItem[];
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

export async function queueReplyAndMarkDone(
  triageItemId: string,
  messageText: string
): Promise<void> {
  const sql = getDb();
  // Get the chat_id from the triage item (don't trust client)
  const items = await sql`
    SELECT chat_id FROM triage_items WHERE id = ${triageItemId}::uuid
  `;
  if (items.length === 0 || !items[0].chat_id) {
    throw new Error("Item not found or has no chat_id");
  }
  const chatId = items[0].chat_id;

  // Queue reply and mark done
  await sql`
    INSERT INTO pending_replies (triage_item_id, chat_id, message_text)
    VALUES (${triageItemId}::uuid, ${chatId}, ${messageText})
  `;
  await sql`
    UPDATE triage_items
    SET user_status = 'done', user_status_at = now()
    WHERE id = ${triageItemId}::uuid
  `;
}
