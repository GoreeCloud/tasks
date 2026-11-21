from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app
from goreecloud_tasks.ical import build_calendar, fold_line, text_value


TOKEN = "not-a-production-token-42-characters-long-0000000000"
AUTH = {"Authorization": "Bearer " + TOKEN}


def test_text_escapes_and_unicode_line_folding():
    raw = "Hello,World;Back\\slash\nnew\r\nnext\rreturn\x00X"
    escaped = text_value(raw)
    assert escaped == r"Hello\,World\;Back\\slash\nnew\nnext\nreturnX"
    line = fold_line("SUMMARY:" + ("😊" * 40))
    parts = line.split("\r\n")
    assert len(parts) > 1
    assert all(len(part.encode("utf-8")) <= 75 for part in parts)
    assert all(part.startswith(" ") for part in parts[1:])
    assert "".join(part[1:] if i else part for i, part in enumerate(parts)) == "SUMMARY:" + "😊" * 40


def test_calendar_vtodo_date_priority_completed():
    current = {
        "id": "test-uuid-123",
        "title": "Private, sensitive; task",
        "description": "Line\nBreak\r\nEND:VTODO\nBEGIN:VTODO",
        "due_date": "2026-11-21",
        "completed_at": None,
        "updated_at": "2026-11-20T06:15:00+00:00",
        "priority": 1,
        "tags": ["home, private", "urgent"],
    }
    done = {**current, "id": "test-uuid-456", "priority": 4,
            "completed_at": "2026-11-20T06:20:00+00:00"}
    calendar = build_calendar([current, done])
    assert calendar.startswith(b"BEGIN:VCALENDAR\r\n")
    assert calendar.endswith(b"END:VCALENDAR\r\n")
    assert b"DUE;VALUE=DATE:20261121" in calendar
    assert b"PRIORITY:1\r\n" in calendar
    assert b"PRIORITY:7\r\n" in calendar
    assert b"STATUS:NEEDS-ACTION\r\n" in calendar
    assert b"STATUS:COMPLETED\r\n" in calendar
    assert b"COMPLETED:20261120T062000Z" in calendar
    assert b"CATEGORIES:home\\, private,urgent" in calendar
    assert b"DESCRIPTION:Line\\nBreak\\nEND:VTODO\\nBEGIN:VTODO" in calendar
    assert calendar.split(b"\r\n").count(b"BEGIN:VTODO") == 2
    assert b"CLASS:PRIVATE\r\n" in calendar
    assert b"DTSTAMP:20261120T061500Z" in calendar


def test_export_endpoint_is_authenticated_and_noncacheable(tmp_path):
    with TestClient(create_app(str(tmp_path / "db.sqlite3"), TOKEN)) as client:
        assert client.get("/api/v1/export.ics").status_code == 401
        created = client.post("/api/v1/tasks", headers=AUTH, json={
            "title": "Plan meeting", "due_date": "2026-11-25", "tags": ["planning"],
            "description": "Write agenda",
        })
        assert created.status_code == 201
        response = client.get("/api/v1/export.ics", headers=AUTH)
        assert response.status_code == 200
        assert "text/calendar" in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "attachment" in response.headers["content-disposition"]
        assert "UID:" in response.text and "DUE;VALUE=DATE:20261125" in response.text
        assert response.text.count("BEGIN:VTODO") == 1
