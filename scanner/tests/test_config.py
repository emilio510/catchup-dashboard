import os
import tempfile
from pathlib import Path
from src.config import ScannerConfig


def test_load_config_from_yaml(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "99999")
    monkeypatch.setenv("TELEGRAM_API_HASH", "testhash")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    yaml_content = """
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5
telegram:
  session_name: testuser
  blacklist:
    - "Spam Group"
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: "Test context"
output:
  telegram_digest: false
  json_file: output.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.scan.window_days == 7
    assert config.scan.batch_size == 5
    assert config.telegram.session_name == "testuser"
    assert "Spam Group" in config.telegram.blacklist
    assert config.classification.model == "claude-sonnet-4-20250514"
    assert config.output.telegram_digest is False


def test_config_loads_env_vars(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    yaml_content = """
scan:
  window_days: 3
  messages_per_chat: 10
  batch_size: 3
telegram:
  session_name: test
  blacklist: []
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 2048
  rate_limit_rpm: 10
  user_context: "test"
output:
  telegram_digest: false
  json_file: test.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.telegram.api_id == 12345
    assert config.telegram.api_hash == "abc123"
    assert config.classification.api_key == "sk-test"


def test_blacklist_case_insensitive(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "99999")
    monkeypatch.setenv("TELEGRAM_API_HASH", "testhash")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    yaml_content = """
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5
telegram:
  session_name: test
  blacklist:
    - "Monitoring Alerts"
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: "test"
output:
  telegram_digest: false
  json_file: test.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.is_blacklisted("monitoring alerts")
    assert config.is_blacklisted("MONITORING ALERTS")
    assert config.is_blacklisted("Monitoring Alerts")
    assert not config.is_blacklisted("Real Group")


def test_escalation_config_defaults():
    from src.config import EscalationConfig
    config = EscalationConfig()
    assert config.P0 == 24
    assert config.P1 == 48
    assert config.P2 is None
    assert config.P3 is None


def test_escalation_config_from_yaml(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
escalation:
  P0: 12
  P1: 24
  P2: null
  P3: null
""")
    import os
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    config = ScannerConfig.from_yaml(config_file)
    assert config.escalation.P0 == 12
    assert config.escalation.P1 == 24


def test_notion_config_defaults():
    from src.config import NotionConfig
    config = NotionConfig()
    assert config.enabled is False
    assert config.user_id == ""
    assert config.databases == []
    assert config.monitor_pages == []


def test_notion_config_from_yaml(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
notion:
  enabled: true
  user_id: "user-uuid-123"
  databases:
    - id: "db-uuid-456"
      assignee_property: "Owner"
      status_property: "State"
      open_statuses: ["Todo", "Doing"]
  monitor_pages:
    - "page-uuid-789"
""")
    import os
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    config = ScannerConfig.from_yaml(config_file)
    assert config.notion.enabled is True
    assert config.notion.user_id == "user-uuid-123"
    assert len(config.notion.databases) == 1
    assert config.notion.databases[0].id == "db-uuid-456"
    assert config.notion.databases[0].assignee_property == "Owner"
    assert config.notion.databases[0].open_statuses == ["Todo", "Doing"]
    assert config.notion.monitor_pages == ["page-uuid-789"]


def test_notion_token_from_env(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
notion:
  enabled: true
  user_id: "user-uuid"
""")
    import os
    os.environ["NOTION_TOKEN"] = "ntn_test_token_123"
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    try:
        config = ScannerConfig.from_yaml(config_file)
        assert config.notion.token == "ntn_test_token_123"
    finally:
        del os.environ["NOTION_TOKEN"]
