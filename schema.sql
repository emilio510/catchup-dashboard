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
  user_status      TEXT DEFAULT 'open',
  user_status_at   TIMESTAMPTZ
);

CREATE INDEX idx_triage_scan ON triage_items(scan_id);
CREATE INDEX idx_triage_priority ON triage_items(priority);
CREATE INDEX idx_triage_user_status ON triage_items(user_status);
