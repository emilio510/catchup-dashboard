"use server";

import { revalidatePath } from "next/cache";
import { updateItemStatus, queueReply } from "@/lib/db";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function validateItemId(itemId: string): void {
  if (!UUID_RE.test(itemId)) {
    throw new Error("Invalid item ID");
  }
}

export async function markItemDone(itemId: string): Promise<void> {
  validateItemId(itemId);
  await updateItemStatus(itemId, "done");
  revalidatePath("/");
}

export async function snoozeItem(itemId: string): Promise<void> {
  validateItemId(itemId);
  await updateItemStatus(itemId, "snoozed");
  revalidatePath("/");
}

export async function reopenItem(itemId: string): Promise<void> {
  validateItemId(itemId);
  await updateItemStatus(itemId, "open");
  revalidatePath("/");
}

export async function sendReply(itemId: string, chatId: number, messageText: string): Promise<void> {
  validateItemId(itemId);
  if (!messageText.trim()) {
    throw new Error("Message cannot be empty");
  }
  await queueReply(itemId, chatId, messageText);
  await updateItemStatus(itemId, "done");
  revalidatePath("/");
}
