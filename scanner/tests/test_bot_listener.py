from src.bot_listener import parse_command, is_authorized

AUTHORIZED_USER_ID = 1744950707


def test_parse_scan_command():
    update = {
        "update_id": 123,
        "message": {
            "message_id": 1,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/scan",
        },
    }
    cmd = parse_command(update)
    assert cmd == "scan"


def test_parse_scan_with_bot_suffix():
    update = {
        "update_id": 124,
        "message": {
            "message_id": 2,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/scan@akgbaambot",
        },
    }
    cmd = parse_command(update)
    assert cmd == "scan"


def test_parse_unknown_command():
    update = {
        "update_id": 125,
        "message": {
            "message_id": 3,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/unknown",
        },
    }
    cmd = parse_command(update)
    assert cmd is None


def test_parse_no_message():
    update = {"update_id": 126}
    cmd = parse_command(update)
    assert cmd is None


def test_is_authorized_valid():
    assert is_authorized(AUTHORIZED_USER_ID) is True


def test_is_authorized_invalid():
    assert is_authorized(9999999) is False
