from datetime import datetime, timezone

from app.scheduler import next_run


def test_next_run_uses_today_when_target_is_later():
    now = datetime(2026, 6, 20, 5, 30, tzinfo=timezone.utc)

    assert next_run(now, "06:00") == datetime(2026, 6, 20, 6, 0, tzinfo=timezone.utc)


def test_next_run_rolls_to_tomorrow_when_target_has_passed():
    now = datetime(2026, 6, 20, 6, 30, tzinfo=timezone.utc)

    assert next_run(now, "06:00") == datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
