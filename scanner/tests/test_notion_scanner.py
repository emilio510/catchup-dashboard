from __future__ import annotations

from src.notion_scanner import (
    parse_comments_response,
    parse_database_query_response,
    filter_mentions,
    format_notion_items_for_classifier,
    comments_to_triage_items,
    assignments_to_triage_items,
)


MOCK_COMMENTS_RESPONSE = {
    "results": [
        {
            "id": "comment-1",
            "created_time": "2026-04-12T10:00:00.000Z",
            "created_by": {"id": "boss-user-id"},
            "rich_text": [
                {"type": "text", "text": {"content": "Hey "}},
                {"type": "mention", "mention": {"type": "user", "user": {"id": "my-user-id"}}},
                {"type": "text", "text": {"content": " can you fill in the Mantle section?"}},
            ],
            "parent": {"type": "page_id", "page_id": "page-abc"},
        },
        {
            "id": "comment-2",
            "created_time": "2026-04-12T08:00:00.000Z",
            "created_by": {"id": "other-user-id"},
            "rich_text": [
                {"type": "text", "text": {"content": "Looks good to me"}},
            ],
            "parent": {"type": "page_id", "page_id": "page-abc"},
        },
    ],
    "has_more": False,
}


def test_parse_comments_response():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    assert len(comments) == 2
    assert comments[0]["id"] == "comment-1"
    assert comments[0]["created_by_id"] == "boss-user-id"
    assert "Mantle section" in comments[0]["text"]


def test_filter_mentions():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    mentioned = filter_mentions(comments, "my-user-id")
    assert len(mentioned) == 1
    assert mentioned[0]["id"] == "comment-1"


def test_filter_mentions_no_match():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    mentioned = filter_mentions(comments, "nobody-id")
    assert len(mentioned) == 0


MOCK_DB_QUERY_RESPONSE = {
    "results": [
        {
            "id": "page-xyz",
            "url": "https://notion.so/page-xyz",
            "properties": {
                "Name": {"title": [{"text": {"content": "Write Q2 report"}}]},
                "Assignee": {"people": [{"id": "my-user-id"}]},
                "Status": {"status": {"name": "In progress"}},
            },
            "last_edited_time": "2026-04-11T14:00:00.000Z",
        },
    ],
    "has_more": False,
}


def test_parse_database_query_response():
    items = parse_database_query_response(
        MOCK_DB_QUERY_RESPONSE,
        title_property="Name",
        assignee_property="Assignee",
        status_property="Status",
    )
    assert len(items) == 1
    assert items[0]["page_id"] == "page-xyz"
    assert items[0]["title"] == "Write Q2 report"
    assert items[0]["status"] == "In progress"


def test_assignments_to_triage_items():
    assignments = [{
        "page_id": "page-xyz",
        "title": "Write Q2 report",
        "status": "In progress",
        "last_edited": "2026-04-11T14:00:00.000Z",
        "url": "https://notion.so/page-xyz",
    }]
    items = assignments_to_triage_items(assignments)
    assert len(items) == 1
    assert items[0].source == "notion"
    assert items[0].priority == "P2"
    assert items[0].source_id == "page-xyz"
    assert items[0].chat_name == "Write Q2 report"


def test_format_notion_items_for_classifier():
    mention_groups = {
        "Q2 Budget Review": {
            "page_id": "page-abc",
            "comments": [
                {
                    "created_by_name": "Matthew Graham",
                    "text": "can you fill in the Mantle section?",
                    "created_time": "2026-04-12T10:00:00.000Z",
                },
            ],
        },
    }
    text = format_notion_items_for_classifier(mention_groups)
    assert "NOTION PAGE" in text
    assert "Q2 Budget Review" in text
    assert "Matthew Graham" in text
    assert "Mantle section" in text


def test_comments_to_triage_items():
    mention_groups = {
        "Q2 Budget Review": {
            "page_id": "page-abc",
            "comments": [
                {
                    "created_by_name": "Matthew Graham",
                    "text": "can you fill in the Mantle section?",
                    "created_time": "2026-04-12T10:00:00.000Z",
                },
            ],
        },
    }
    items = comments_to_triage_items(mention_groups)
    assert len(items) == 1
    assert items[0].source == "notion"
    assert items[0].source_id == "page-abc"
    assert items[0].chat_name == "Q2 Budget Review"
    assert items[0].priority == "P1"
    assert "Matthew Graham" in items[0].preview
