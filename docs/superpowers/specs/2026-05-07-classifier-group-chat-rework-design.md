# Classifier Group-Chat Rework — Design Spec

**Date:** 2026-05-07
**Status:** Approved (Approach A)
**Author:** akgemilio (Emile)

## Problem

The Telegram scanner over-fires in group chats. Conversations where the user is not addressed get classified as P0/P1 and surface on the dashboard. The `@akgbaambot` escalation reminders then re-ping the user on these false positives at 24h (P0) and 48h (P1), compounding the noise.

**Diagnosis from current code (`scanner/src/classifier.py`, `scanner/src/telegram_reader.py`, `scanner/config.yaml`):**

1. The system prompt is identical for DMs and group chats. `chat_type` (`"dm"` vs `"group"`) is passed in the prompt header but no group-specific rules apply.
2. The system prompt instructs the model: *"When in doubt between two priority levels, ALWAYS choose the HIGHER one."* In groups where most messages are not addressed to the user, this manufactures false-positive P0/P1s.
3. The prompt asks for urgency without first asking whether the message requires a response from the user. In groups that gating question is load-bearing.
4. Only `my_display_name` (first name) is passed to the classifier. Mentions like "Emile", "Em", "Akg", "@AkgEmilio" are not detectable beyond the first form.
5. `should_filter_dialog` keeps any chat where the user did not send the last message. In groups someone always speaks after the user, so groups never get filtered out at the dialog layer.
6. `ChatMessage` does not capture `reply_to_message_id`. Telegram's native reply chains are invisible to the classifier.
7. `EscalationConfig` re-pings any P0 >24h and P1 >48h regardless of address-quality, so false-positive priorities turn into recurring nags.

## Goal

In group chats, default to silence. Only surface a group conversation as actionable when there is positive evidence the user is being addressed. Keep DM behavior unchanged.

**Success criterion:** after one scan cycle, the dashboard's P0/P1 group-chat items drop substantially. Escalation reminders for false-positive group items disappear within 48 hours.

## Approach

Approach A from the brainstorm: **prompt redesign + richer context.** No new architecture, no new services, no DB migration. Same single LLM call per batch. Effort estimated at half a day.

The redesign has two halves: (1) feed the model the missing signals it needs to detect address (aliases, reply chains, last-message anchor, owned topics), (2) rewrite the system prompt to ask the address question first and adopt a strict-default for groups.

Rejected alternatives: two-stage classifier (B, doubles LLM cost), rule-based pre-filter (C, brittle keyword matching). Both remain available as later layers if A alone is insufficient after one week of real use.

## Section 1 — Config inputs

Add to `scanner/config.yaml` under `classification:`:

```yaml
classification:
  user_aliases:
    - Emile
    - Em
    - Emilio
    - Akgemilio
    - "@AkgEmilio"
    - Akg
  topics_owned:
    - Aave
    - GHO
    - sGHO
    - Logic Protocol
    - USDT0
    - vault
    - Pendle
    - looper
    - treasury
    - Mantle
    - incentives
```

Extend `ClassificationConfig` in `scanner/src/config.py`:

```python
class ClassificationConfig(BaseModel):
    # existing fields preserved
    user_aliases: list[str] = Field(default_factory=list)
    topics_owned: list[str] = Field(default_factory=list)
```

Both lists are user-editable in YAML without code changes.

## Section 2 — Signal capture

### A. Telegram reply chains

Extend `ChatMessage` in `scanner/src/telegram_reader.py`:

```python
@dataclass(frozen=True)
class ChatMessage:
    sender_name: str
    sender_id: int
    text: str
    date: datetime
    message_id: int
    is_me: bool
    reply_to_message_id: int | None = None  # NEW

    def format(self, replied_text: str | None = None, replied_is_me: bool = False) -> str:
        tag = " (me)" if self.is_me else ""
        ts = self.date.strftime("%Y-%m-%d %H:%M")
        prefix = f"[{ts}] {self.sender_name}{tag}"
        if replied_text:
            snippet = replied_text[:60].replace("\n", " ")
            if replied_is_me:
                prefix += f' (↩ to YOU: "{snippet}")'
            else:
                prefix += f' (↩ to "{snippet}")'
        return f"{prefix}: {self.text}"
```

`deep_read` captures `msg.reply_to and msg.reply_to.reply_to_msg_id` from Telethon. When formatting messages for the prompt (in `build_classification_prompt`), look up the replied-to message in the same conversation by `message_id`. If found, pass its first 60 chars as `replied_text` and pass `replied_is_me=True` when that replied-to message has `is_me=True`. If not found (older than scan window), pass `replied_text="msg outside window"` and `replied_is_me=False`.

The `(↩ to YOU: "...")` distinction is load-bearing: rule (b) of the system prompt requires the classifier to detect replies pointing to the user, which is impossible if the rendered format treats all replies identically.

### B. "Your last message" anchor

In `build_classification_prompt`, find the most recent `ChatMessage` where `is_me=True`. Render messages up to and including it, then insert the literal separator line, then render messages after:

```
[2026-05-06 14:32] Bob: …
[2026-05-06 14:35] Alice: …
[2026-05-06 15:01] Emile (me): …
--- YOUR LAST MESSAGE ABOVE ---
[2026-05-06 16:22] Bob: any thoughts on this?
[2026-05-06 16:30] Alice: yeah I'd push back
```

If the user has no message in the window, omit the separator entirely (the conversation predates the user's involvement, treat as ambient).

### C. Aliases and topics injection

Both lists are rendered into the user prompt by `build_classification_prompt`, before the conversations block:

```
User aliases (any case-insensitive substring match counts as a mention):
  - Emile
  - Em
  - Emilio
  - Akgemilio
  - @AkgEmilio
  - Akg

Topics the user owns (decisions/actions on these topics likely require the user):
  - Aave
  - GHO
  - …
```

## Section 3 — System prompt + output schema

Replace `SYSTEM_PROMPT` in `scanner/src/classifier.py` with:

```
You are a personal communication triage assistant.

DECIDE IN THIS ORDER:
1. Is the user being addressed by this conversation? (Most important in groups.)
2. If yes, what is the urgency?

GROUP CHATS (chat_type == "group") — STRICT DEFAULT:
The default is addressed_to_user=false, priority=P3, status=MONITORING.
Set addressed_to_user=true ONLY if at least one is true:
  (a) A message uses one of the user's aliases (case-insensitive substring match).
  (b) A message is a Telegram reply (↩) pointing to a message the user sent.
  (c) A direct question appears AFTER "--- YOUR LAST MESSAGE ABOVE ---" and
      either names a topic the user owns or follows naturally from what the
      user just said.
  (d) The conversation is asking for an action/decision on a topic the user
      owns (from the topics list provided).

DMs (chat_type == "dm"):
addressed_to_user=true by default, unless the conversation is clearly closed
(last message is "thanks", an emoji-only reply, or an acknowledgment).

PRIORITY (only when addressed_to_user=true):
- P0 Respond Today: actively blocked, deal-critical, multiple pings.
- P1 This Week: important deliverable, meeting prep, time-sensitive.
- P2 Respond: question or request, not urgent.
- P3 Monitor: FYI, no action needed.

WHEN UNCERTAIN, CHOOSE THE LOWER PRIORITY.
Better to miss a ping than spam the user.

STABILITY: don't downgrade a previous priority unless new messages clearly
resolve the conversation. Don't reopen "done" items on reactions/thanks/acks.

OUTPUT (JSON array, one entry per chat). Output ONLY the array.
{
  "chat_name": "...",
  "addressed_to_user": true|false,
  "address_reason": "alias_mention"|"reply_to_user"|"question_after_user"|"topic_owned"|"dm_default"|"not_addressed",
  "priority": "P0"|"P1"|"P2"|"P3",
  "status": "READ_NO_REPLY"|"NEW"|"MONITORING",
  "waiting_person": "..."|null,
  "waiting_since": "ISO 8601"|null,
  "waiting_days": int|null,
  "tags": [...],
  "context_summary": "1-2 sentences",
  "draft_reply": "..."|null,
  "preview": "200 chars"
}
```

Key changes versus current prompt:

- Two-step decision (address → urgency) replaces the old single-step urgency call.
- Group-strict default replaces "always choose higher."
- "When uncertain, choose the LOWER priority" replaces the old recall-maximizing rule.
- New `addressed_to_user` and `address_reason` output fields enable belt-and-suspenders enforcement and dashboard debugging.

### Belt-and-suspenders enforcement

After JSON parsing in `Classifier.classify_batch`, before constructing `TriageItem`:

```python
if chat_type == "group" and not entry.get("addressed_to_user", False):
    entry["priority"] = "P3"
    entry["status"] = "MONITORING"
```

The deterministic rule is what gives confidence that a model slip cannot reintroduce false positives. `addressed_to_user` and `address_reason` are consumed in `classify_batch` for the post-processing decision and then discarded (the existing `TriageItem` dataclass does not carry them). To debug a specific decision, log them at INFO level alongside the chat name. Persisting these fields to the DB is deferred — see Out of Scope.

## Section 4 — Files, tests, rollout

### Files changed (5 source + 2 test files)

- `scanner/src/config.py` — extend `ClassificationConfig`
- `scanner/config.yaml` — populate `user_aliases` and `topics_owned`
- `scanner/src/telegram_reader.py` — add `reply_to_message_id` to `ChatMessage`, capture in `deep_read`, update `format()` signature
- `scanner/src/classifier.py` — replace `SYSTEM_PROMPT`, update `build_classification_prompt` (alias + topic injection, last-message separator, reply chain rendering), add post-processing enforcement in `classify_batch`
- `scanner/tests/test_classifier.py` — new tests
- `scanner/tests/test_telegram_reader.py` — new reply chain test

### Tests (TDD — write first)

1. `build_classification_prompt` includes the alias list verbatim in output
2. `build_classification_prompt` includes the topics list verbatim in output
3. `build_classification_prompt` inserts `--- YOUR LAST MESSAGE ABOVE ---` immediately after the most recent message with `is_me=True`, with all later messages rendered after the separator
4. `build_classification_prompt` omits the separator entirely when no `is_me=True` message exists in the conversation, and still renders all messages in chronological order
5. `ChatMessage.format` renders `(↩ to YOU: "first 60 chars")` when `replied_text` is provided and `replied_is_me=True`
6. `ChatMessage.format` renders `(↩ to "first 60 chars")` when `replied_text` is provided and `replied_is_me=False`
7. `ChatMessage.format` renders no reply marker when `replied_text=None`
8. `Classifier.classify_batch` post-processor forces `priority=P3, status=MONITORING` when `chat_type="group"` and the model returns `addressed_to_user=false`
9. `Classifier.classify_batch` does NOT override priority when `chat_type="dm"`, regardless of `addressed_to_user`
10. `Classifier.classify_batch` does NOT override priority when `addressed_to_user=true`, regardless of `chat_type`
11. `telegram_reader.deep_read` populates `reply_to_message_id` from `msg.reply_to.reply_to_msg_id` when present and leaves it `None` otherwise

### Rollout

1. Implement on a feature branch with all tests green locally
2. Commit, push, deploy to VPS by `git pull` in `~/catchup-dashboard/scanner` (or `scp` if VPS is on a different remote)
3. Trigger one manual scan via `/scan` to `@akgbaambot`
4. Compare digest output before/after — expect group-chat items to mostly land in P3
5. Observe for 48h; verify escalation reminders drop

### Reversibility

If the rework is wrong, revert the commit. No DB schema changes, no data migration. The next scan cycle naturally overwrites the previous classification because dedup operates on `chat_id` not on classification content.

## Out of scope (YAGNI)

- Persisting `addressed_to_user` and `address_reason` to the `triage_items` table. Deferred: add columns and a dashboard tooltip later if the in-process debugging trail proves insufficient.
- Dashboard UI changes. Existing P0–P3 columns naturally fill less; no layout change required.
- Retroactive reclassification of existing items. Next scan overwrites anyway.
- Two-stage classifier (Approach B from brainstorm) and rule-based pre-filter (Approach C). Available as future layers if Approach A alone is insufficient after one week of real use.
