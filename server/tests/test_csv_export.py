"""Private, explicit, bounded flat task CSV export acceptance tests."""
import csv
import io

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app
from goreecloud_tasks.csv_export import (
    COLUMNS, MAX_EXPORT_ROWS, build_task_csv, spreadsheet_text,
)

TOKEN = "only-synthetic-fixture-token-not-real-user-123456"
AUTH = {"Authorization": "Bearer " + TOKEN}


def test_authenticated_csv_export_escapes_formulas_and_preserves_csv_fields(tmp_path):
    api = TestClient(create_app(str(tmp_path / "synthetic-tasks.sqlite3"), TOKEN))
    assert api.get("/api/v1/export.csv").status_code == 401
    project = api.post("/api/v1/projects", headers=AUTH,
                       json={"name": "=HYPERLINK(\"https://bad.invalid\")"}).json()
    created = api.post("/api/v1/tasks", headers=AUTH, json={
        "title": "=2+2", "description": "  \t=private formula, \"quote\"\r\nsecond line",
        "project_id": project["id"], "priority": 3,
        "tags": ["=important", "test"], "due_date": "2026-12-01",
        "recurrence": "weekly"
    })
    assert created.status_code == 201, created.text
    result = api.get("/api/v1/export.csv", headers=AUTH)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["content-disposition"] == 'attachment; filename="goreecloud-tasks.csv"'
    assert result.headers["content-type"].startswith("text/csv; charset=utf-8")
    assert "\r\n" in result.text
    reader = csv.DictReader(io.StringIO(result.text, newline=""))
    rows = list(reader)
    assert tuple(reader.fieldnames) == COLUMNS
    assert len(rows) == 1
    task = rows[0]
    assert task["id"] == created.json()["id"]
    assert task["title"] == "'=2+2"
    assert task["description"] == "'  \t=private formula, \"quote\"\r\nsecond line"
    assert task["project_name"].startswith("'=HYPERLINK")
    assert task["tags"] == "'=important|test"
    assert task["priority"] == "3"
    assert task["recurrence"] == "weekly"
    assert task["due_date"] == "2026-12-01"


def test_export_formula_guard_handles_whitespace_and_special_characters():
    for unsafe in ["=1+2", "+cmd", "-2", "@evil", "\t=1+2",
                   "\r=1+2", "\n=1+2", "  =1+2",
                   "\ufeff=1+2", "\u200b=1+2", "\u2060=1+2",
                   " \ufeff=1+2"]:
        assert spreadsheet_text(unsafe) == "'" + unsafe
    for safe in ["Regular", "hello =2", "42", "", None]:
        expected = "" if safe is None else safe
        assert spreadsheet_text(safe) == expected


def test_export_refuses_excessive_rows_and_utf8_bytes():
    with pytest.raises(HTTPException) as too_many:
        build_task_csv([{"title": "synthetic", "tags": []}] * (MAX_EXPORT_ROWS + 1))
    assert too_many.value.status_code == 413
    assert "5000" in too_many.value.detail
    huge = [{"title": "safe", "description": "🧪" * 10000, "tags": []}] * 300
    with pytest.raises(HTTPException) as oversized:
        build_task_csv(huge)
    assert oversized.value.status_code == 413
    assert "10 MB" in oversized.value.detail


def test_csv_export_empty_database_is_header_only(tmp_path):
    api = TestClient(create_app(str(tmp_path / "empty.sqlite3"), TOKEN))
    response = api.get("/api/v1/export.csv", headers=AUTH)
    assert response.status_code == 200
    assert response.text == ",".join(COLUMNS) + "\r\n"
