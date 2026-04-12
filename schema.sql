CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE scans (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scanned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  sources       TEXT[] NOT NULL,
  dialogs_listed     INT NOT NULL,
  dialogs_filtered   INT NOT NULL,
  dialogs_classified INT NOT NULL,
  stats         JSONB NOT NULL
);

CREATE TABLE triage_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  source          TEXT NOT NULL,
  chat_name       TEXT NOT NULL,
  chat_type       TEXT NOT NULL,
  waiting_person  TEXT,
  preview         TEXT NOT NULL,
  context_summary TEXT,
  draft_reply     TEXT,
  priority        TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'READ_NO_REPLY',
  tags            TEXT[] DEFAULT '{}',
  last_message_at  TIMESTAMPTZ,
  waiting_since    TIMESTAMPTZ,
  waiting_days     REAL,
  scanned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  chat_id          BIGINT,
  message_id       BIGINT,
  source_id        TEXT,
  user_status      TEXT DEFAULT 'open',
  user_status_at   TIMESTAMPTZ,
  last_reminded_at TIMESTAMPTZ
);

CREATE INDEX idx_triage_scan ON triage_items(scan_id);
CREATE INDEX idx_triage_priority ON triage_items(priority);
CREATE INDEX idx_triage_user_status ON triage_items(user_status);

CREATE TABLE pending_replies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  triage_item_id  UUID NOT NULL REFERENCES triage_items(id) ON DELETE CASCADE,
  chat_id         BIGINT NOT NULL,
  message_text    TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at         TIMESTAMPTZ,
  error           TEXT,
  retry_count     INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_pending_replies_status ON pending_replies(status);

CREATE INDEX idx_triage_dedup ON triage_items (COALESCE(chat_id::text, id::text), scanned_at DESC);
CREATE INDEX idx_triage_chat_id_scanned ON triage_items (chat_id, scanned_at DESC);
