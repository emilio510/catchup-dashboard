DROP INDEX IF EXISTS idx_triage_dedup;
CREATE INDEX idx_triage_dedup ON triage_items (COALESCE(chat_id::text, source_id, id::text), scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_triage_source_id ON triage_items (source_id, scanned_at DESC) WHERE source_id IS NOT NULL;
