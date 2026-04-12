CREATE INDEX IF NOT EXISTS idx_triage_chat_id_scanned ON triage_items (chat_id, scanned_at DESC);
