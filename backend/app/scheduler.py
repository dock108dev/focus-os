from __future__ import annotations

import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


logger = logging.getLogger(__name__)


def next_run(now: datetime, target: str) -> datetime:
    hour_text, minute_text = target.split(":", 1)
    scheduled = now.replace(hour=int(hour_text), minute=int(minute_text), second=0, microsecond=0)
    if scheduled <= now:
        scheduled += timedelta(days=1)
    return scheduled


def trigger_job(api_url: str) -> None:
    parsed = urllib.parse.urlparse(api_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("FOCUSOS_API_URL must use http or https")
    headers = {}
    internal_key = os.getenv("FOCUSOS_INTERNAL_API_KEY")
    if internal_key:
        headers["X-FocusOS-Key"] = internal_key
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/jobs/morning-briefing",
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310
        response.read()


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    api_url = os.getenv("FOCUSOS_API_URL", "http://api:8000")
    run_time = os.getenv("MORNING_JOB_TIME", "06:00")
    timezone_name = os.getenv("TZ", "America/New_York")
    hour_text, minute_text = run_time.split(":", 1)

    scheduler = BlockingScheduler(timezone=timezone_name)

    def run() -> None:
        try:
            trigger_job(api_url)
        except Exception:
            logger.exception("morning_briefing_scheduler_trigger_failed", extra={"api_url": api_url})

    scheduler.add_job(
        run,
        CronTrigger(hour=int(hour_text), minute=int(minute_text), timezone=timezone_name),
        id="morning-briefing",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("scheduled morning briefing at %s %s", run_time, timezone_name)
    scheduler.start()


if __name__ == "__main__":
    main()
