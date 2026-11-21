"""Daily habit tracking with local-date semantics and revision-safe checkins.

Not a notification scheduler or a device-side sync queue. GoreeCloud Tasks
remains single-user development software; routes inherit the app bearer auth.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=16000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Habit name must not be blank")
        return value


class HabitPatch(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=16000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return HabitCreate.clean_name(value) if value is not None else None


class HabitCheckin(BaseModel):
    day: date
    expected_version: int = Field(ge=1)


def install_habit_routes(router: APIRouter, store) -> None:
    def existing(conn, habit_id: str) -> dict:
        habit = conn.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
        if habit is None:
            raise HTTPException(status_code=404, detail="Habit not found")
        return dict(habit)

    def check_version(habit: dict, expected: int) -> None:
        if habit["version"] != expected:
            raise HTTPException(status_code=409, detail="Habit changed; reload before retrying")

    def overview(conn, habit: dict, as_of: date) -> dict:
        # Includes only past-or-current checkins for streak semantics. One habit's
        # history is limited for bounded resource use. Exact total is counted.
        rows = conn.execute("""
            SELECT day FROM habit_checkins WHERE habit_id=? AND day<=?
            ORDER BY day DESC LIMIT 3652
        """, (habit["id"], as_of.isoformat())).fetchall()
        days = {row["day"] for row in rows}
        count = conn.execute(
            "SELECT COUNT(*) FROM habit_checkins WHERE habit_id=?", (habit["id"],)
        ).fetchone()[0]
        checked_today = as_of.isoformat() in days
        current = as_of if checked_today else as_of - timedelta(days=1)
        streak = 0
        while streak < 3650 and current.isoformat() in days:
            streak += 1
            current -= timedelta(days=1)
        return {**habit, "checked_in_today": checked_today,
                "current_streak": streak, "total_checkins": count, "as_of": as_of.isoformat()}

    def require_real_day(day: date) -> None:
        # Clients may be ahead of UTC by one calendar day; never accept
        # speculative check-ins beyond that calendar window.
        if day > datetime.now(timezone.utc).date() + timedelta(days=1):
            raise HTTPException(status_code=422, detail="Cannot check in far-future dates")

    @router.get("/habits")
    def list_habits(
        as_of: date | None = None,
        limit: int = Query(default=100, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1_000_000)
    ):
        selected = as_of or datetime.now(timezone.utc).date()
        with store.open() as conn:
            rows = conn.execute(
                "SELECT * FROM habits ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [overview(conn, dict(row), selected) for row in rows]

    @router.post("/habits", status_code=201)
    def create_habit(data: HabitCreate):
        stamp = now()
        habit = {"id": str(uuid4()), **data.model_dump(),
                 "version": 1, "created_at": stamp, "updated_at": stamp}
        with store.transaction() as conn:
            conn.execute(
                """INSERT INTO habits(id,name,description,version,created_at,updated_at)
                   VALUES (:id,:name,:description,:version,:created_at,:updated_at)""", habit
            )
            return overview(conn, habit, datetime.now(timezone.utc).date())

    @router.patch("/habits/{habit_id}")
    def edit_habit(habit_id: str, data: HabitPatch):
        with store.transaction() as conn:
            habit = existing(conn, habit_id)
            check_version(habit, data.expected_version)
            updates = data.model_dump(exclude_unset=True, exclude={"expected_version"})
            if updates.get("name") is None:
                updates.pop("name", None)
            if updates.get("description") is None:
                updates.pop("description", None)
            if not updates:
                return overview(conn, habit, datetime.now(timezone.utc).date())
            candidate = HabitCreate.model_validate({**habit, **updates})
            stamp = now()
            conn.execute(
                """UPDATE habits SET name=?,description=?,updated_at=?,version=version+1
                   WHERE id=?""",
                (candidate.name, candidate.description, stamp, habit_id)
            )
            return overview(conn, existing(conn, habit_id), datetime.now(timezone.utc).date())

    @router.delete("/habits/{habit_id}", status_code=204)
    def delete_habit(habit_id: str, expected_version: int = Query(ge=1)):
        with store.transaction() as conn:
            habit = existing(conn, habit_id)
            check_version(habit, expected_version)
            # FK ON DELETE CASCADE removes every private check-in in the same txn.
            conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))

    @router.get("/habits/{habit_id}/checkins")
    def habit_checkins(
        habit_id: str,
        limit: int = Query(default=365, ge=1, le=1000),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ):
        with store.open() as conn:
            existing(conn, habit_id)
            return [row["day"] for row in conn.execute(
                """SELECT day FROM habit_checkins WHERE habit_id=?
                   ORDER BY day DESC LIMIT ? OFFSET ?""",
                (habit_id, limit, offset)
            )]

    @router.post("/habits/{habit_id}/checkins", status_code=201)
    def check_in(habit_id: str, data: HabitCheckin):
        require_real_day(data.day)
        with store.transaction() as conn:
            habit = existing(conn, habit_id)
            check_version(habit, data.expected_version)
            stamp = now()
            key = data.day.isoformat()
            if conn.execute(
                "SELECT 1 FROM habit_checkins WHERE habit_id=? AND day=?", (habit_id, key)
            ).fetchone():
                raise HTTPException(status_code=409, detail="Date is already checked in")
            conn.execute(
                "INSERT INTO habit_checkins(habit_id,day,created_at) VALUES (?,?,?)",
                (habit_id, key, stamp)
            )
            conn.execute(
                "UPDATE habits SET version=version+1,updated_at=? WHERE id=?",
                (stamp, habit_id)
            )
            return overview(conn, existing(conn, habit_id), data.day)

    @router.delete("/habits/{habit_id}/checkins/{day}", status_code=200)
    def undo_checkin(habit_id: str, day: date, expected_version: int = Query(ge=1)):
        with store.transaction() as conn:
            habit = existing(conn, habit_id)
            check_version(habit, expected_version)
            key = day.isoformat()
            removed = conn.execute(
                "DELETE FROM habit_checkins WHERE habit_id=? AND day=?", (habit_id, key)
            )
            if removed.rowcount != 1:
                raise HTTPException(status_code=404, detail="No check-in for this date")
            conn.execute(
                "UPDATE habits SET version=version+1,updated_at=? WHERE id=?",
                (now(), habit_id)
            )
            return overview(conn, existing(conn, habit_id), day)
