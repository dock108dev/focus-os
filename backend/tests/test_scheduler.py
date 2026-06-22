from datetime import datetime, timezone

from app import scheduler
from app.scheduler import next_run, trigger_job


def test_next_run_uses_today_when_target_is_later():
    now = datetime(2026, 6, 20, 5, 30, tzinfo=timezone.utc)

    assert next_run(now, "06:00") == datetime(2026, 6, 20, 6, 0, tzinfo=timezone.utc)


def test_next_run_rolls_to_tomorrow_when_target_has_passed():
    now = datetime(2026, 6, 20, 6, 30, tzinfo=timezone.utc)

    assert next_run(now, "06:00") == datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)


def test_trigger_job_posts_to_internal_job_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            captured["read"] = True
            return b"ok"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["key"] = request.get_header("X-focusos-key")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("FOCUSOS_INTERNAL_API_KEY", "local-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    trigger_job("http://api:8000/")

    assert captured == {
        "url": "http://api:8000/api/jobs/morning-briefing",
        "method": "POST",
        "key": "local-key",
        "timeout": 120,
        "read": True,
    }


def test_trigger_job_rejects_non_http_api_url():
    try:
        trigger_job("file:///tmp/focusos.sock")
    except ValueError as exc:
        assert "http or https" in str(exc)
    else:
        raise AssertionError("trigger_job should reject non-http API URLs")


def test_scheduler_main_registers_and_runs_job(monkeypatch):
    captured = {}

    class FakeBlockingScheduler:
        def __init__(self, timezone):
            captured["timezone"] = timezone

        def add_job(self, func, trigger, id, replace_existing, max_instances):
            captured["job"] = func
            captured["job_id"] = id
            captured["replace_existing"] = replace_existing
            captured["max_instances"] = max_instances
            captured["trigger"] = trigger

        def start(self):
            captured["started"] = True
            captured["job"]()

    monkeypatch.setenv("FOCUSOS_API_URL", "http://internal-api:9000")
    monkeypatch.setenv("MORNING_JOB_TIME", "07:15")
    monkeypatch.setenv("TZ", "America/New_York")
    monkeypatch.setattr(scheduler, "BlockingScheduler", FakeBlockingScheduler)
    monkeypatch.setattr(scheduler, "trigger_job", lambda api_url: captured.setdefault("api_url", api_url))

    scheduler.main()

    assert captured["timezone"] == "America/New_York"
    assert captured["job_id"] == "morning-briefing"
    assert captured["replace_existing"] is True
    assert captured["max_instances"] == 1
    assert captured["started"] is True
    assert captured["api_url"] == "http://internal-api:9000"


def test_scheduler_main_logs_trigger_failures(monkeypatch, caplog):
    captured = {}

    class FakeBlockingScheduler:
        def __init__(self, timezone):
            captured["timezone"] = timezone

        def add_job(self, func, trigger, **kwargs):
            captured["job"] = func

        def start(self):
            captured["job"]()

    def failing_trigger(api_url):
        raise RuntimeError(f"cannot reach {api_url}")

    monkeypatch.setattr(scheduler, "BlockingScheduler", FakeBlockingScheduler)
    monkeypatch.setattr(scheduler, "trigger_job", failing_trigger)

    scheduler.main()

    assert "morning_briefing_scheduler_trigger_failed" in caplog.text
