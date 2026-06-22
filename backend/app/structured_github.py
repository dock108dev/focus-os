from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .source_status import record_source_status
from .structured_common import SOURCE_REFRESH_EXCEPTIONS, load_json


logger = logging.getLogger(__name__)


def github_api(path: str) -> dict | list:
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FocusOS/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return load_json(f"https://api.github.com{path}", headers=headers)


def refresh_github_repo_health(db: Session) -> dict:
    owner = os.getenv("FOCUSOS_GITHUB_OWNER", "dock108dev")
    now = datetime.now(timezone.utc)
    errors: list[str] = []
    facts: list[dict] = []
    missing_requirements: list[str] = []
    active_repo_ages: list[dict] = []
    failed_workflows: list[dict] = []
    open_prs_found = 0
    archived_repos_ignored = 0
    try:
        repos_payload = github_api(
            f"/users/{urllib.parse.quote(owner)}/repos?type=owner&sort=updated&per_page=100"
        )
        all_repos = [repo for repo in repos_payload if isinstance(repo, dict)]
        archived_repos_ignored = sum(1 for repo in all_repos if repo.get("archived"))
        repos = [
            repo
            for repo in all_repos
            if not repo.get("archived")
        ][:20]
        for repo in repos:
            name = repo.get("name", "")
            pushed_at = repo.get("pushed_at")
            stale = False
            days_since_push = None
            if pushed_at:
                pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                days_since_push = (now - pushed).days
                stale = now - pushed > timedelta(days=14)
            active_repo_ages.append(
                {
                    "repo": name,
                    "pushed_at": pushed_at,
                    "days_since_push": days_since_push,
                    "url": repo.get("html_url"),
                }
            )
            if stale:
                facts.append(
                    {
                        "kind": "stale_repo",
                        "repo": name,
                        "summary": "Active public repo has no commits for about 2 weeks.",
                        "pushed_at": pushed_at,
                        "url": repo.get("html_url"),
                    }
                )
            try:
                pulls = github_api(
                    f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/pulls?state=open&per_page=10"
                )
                for pull in pulls:
                    open_prs_found += 1
                    author = ((pull.get("user") or {}).get("login") or "").lower()
                    automated = any(
                        token in author
                        for token in ("dependabot", "renovate", "copilot", "github-actions")
                    )
                    facts.append(
                        {
                            "kind": "automated_pr" if automated else "open_pr",
                            "repo": name,
                            "summary": "Open automated PR." if automated else "Open PR needs review.",
                            "title": pull.get("title"),
                            "url": pull.get("html_url"),
                            "author": author,
                        }
                    )
            except SOURCE_REFRESH_EXCEPTIONS as exc:
                errors.append(f"{name} pulls: {type(exc).__name__}: {exc}")
            try:
                workflow_runs_payload = github_api(
                    f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/actions/runs?status=failure&per_page=5"
                )
                workflow_runs = workflow_runs_payload.get("workflow_runs", [])
                for run in workflow_runs:
                    if not isinstance(run, dict):
                        continue
                    failed = {
                        "repo": name,
                        "workflow": run.get("name"),
                        "title": run.get("display_title"),
                        "conclusion": run.get("conclusion"),
                        "status": run.get("status"),
                        "updated_at": run.get("updated_at"),
                        "url": run.get("html_url"),
                    }
                    failed_workflows.append(failed)
                    facts.append(
                        {
                            "kind": "failed_workflow",
                            "repo": name,
                            "summary": "Recent GitHub Actions workflow failure.",
                            "title": run.get("display_title") or run.get("name"),
                            "url": run.get("html_url"),
                            "updated_at": run.get("updated_at"),
                        }
                    )
            except SOURCE_REFRESH_EXCEPTIONS as exc:
                errors.append(f"{name} workflows: {type(exc).__name__}: {exc}")
        missing_requirements.append(
            "Security alerts require authenticated API scope and are not checked in the public MVP."
        )
    except SOURCE_REFRESH_EXCEPTIONS as exc:
        logger.warning("github_repo_health_refresh_failed", exc_info=True)
        record_source_status(
            db,
            "GitHub API",
            "error",
            "GitHub repo health refresh failed.",
            {"error": str(exc)},
        )
        return {
            "status": "error",
            "facts": [],
            "errors": [str(exc)],
            "missing_requirements": missing_requirements,
        }

    status = "ok" if not errors else "partial"
    result = {
        "source_id": "GitHub API",
        "status": status,
        "checked_at": now.isoformat(),
        "facts": facts,
        "errors": errors[:10],
        "missing_requirements": missing_requirements,
        "owner": owner,
        "repos_scanned": len(repos),
        "archived_repos_ignored": archived_repos_ignored,
        "open_prs_found": open_prs_found,
        "failed_workflows_found": len(failed_workflows),
        "failed_workflows": failed_workflows[:10],
        "security_alerts": "unavailable_without_authenticated_security_scope",
        "active_repo_ages": active_repo_ages,
    }
    record_source_status(
        db,
        "GitHub API",
        status,
        f"Checked {len(repos)} public non-archived repos.",
        result,
    )
    return result


def github_attention_items(db: Session) -> list[dict]:
    from .models import SourceStatus

    status = db.scalar(select(SourceStatus).where(SourceStatus.name == "GitHub API"))
    details = status.details if status else {}
    facts = details.get("facts") if isinstance(details, dict) else []
    if not isinstance(facts, list):
        facts = []
    items = []
    for fact in facts[:5]:
        kind = fact.get("kind")
        if kind not in {"automated_pr", "open_pr", "stale_repo", "failed_workflow"}:
            continue
        category = "action" if kind in {"automated_pr", "open_pr", "failed_workflow"} else "awareness"
        title = (
            f"{fact.get('repo')} has an automated PR"
            if kind == "automated_pr"
            else f"{fact.get('repo')} has an open PR"
            if kind == "open_pr"
            else f"{fact.get('repo')} has a failing workflow"
            if kind == "failed_workflow"
            else f"{fact.get('repo')} has been quiet for about 2 weeks"
        )
        items.append(
            enrich_attention_item(
                {
                    "title": title,
                    "why_now": fact.get("summary", "GitHub repo health changed."),
                    "action": "",
                    "priority": 8 if category == "action" else 5,
                    "source": "github",
                    "topic": "github",
                    "detail_id": f"github:{fact.get('repo')}:{kind}",
                    "source_watch_ids": ["watch:personal-github-repo-health"],
                    "triggered_surface_rule": fact.get("summary", "GitHub repo health rule triggered."),
                    "why_today": fact.get("summary", "GitHub repo health changed."),
                },
                category=category,
                importance_score=82 if category == "action" else 58,
                actionability_score=72 if category == "action" else 12,
                expiration_hours=72,
                why_user_cares="Public repo health can create a quick action queue.",
            )
        )
    return items
