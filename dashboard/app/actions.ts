"use server";

import { updateItemStatus } from "@/lib/db";

export async function markItemDone(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "done");
}

export async function snoozeItem(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "snoozed");
}

export async function reopenItem(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "open");
}
