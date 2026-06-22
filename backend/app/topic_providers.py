from __future__ import annotations

import json
import os
import subprocess  # nosec B404
import tempfile
from datetime import date
from pathlib import Path

from openai import OpenAI, OpenAIError

from .models import Topic
from .voice import clean_action_text, clean_editorial_text


class AIProviderConfigurationError(RuntimeError):
    """Raised when AI briefing generation is explicitly configured incorrectly."""


AI_PROVIDER_EXCEPTIONS = (
    AIProviderConfigurationError,
    OpenAIError,
    subprocess.SubprocessError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    json.JSONDecodeError,
)


def parse_ai_payload(raw_text: str, topic: Topic) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {
            "title": f"{topic.name}: attention check",
            "summary": clean_editorial_text(raw_text.strip())[:1200],
            "bullets": [],
            "action": "",
            "priority": topic.priority,
            "generated_by": "openai-web-search",
        }

    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        parsed = {}

    return {
        "title": clean_editorial_text(
            str(parsed.get("title") or f"{topic.name}: attention check")
        )[:240],
        "summary": clean_editorial_text(str(parsed.get("summary") or raw_text.strip()))[
            :2000
        ],
        "bullets": [
            clean_editorial_text(str(item))[:280] for item in parsed.get("bullets", [])
        ][:4],
        "action": clean_action_text(str(parsed.get("action") or ""))[:240],
        "priority": int(parsed.get("priority") or topic.priority),
        "generated_by": "openai-web-search",
    }


def briefing_prompt(topic: Topic) -> str:
    return (
        "You are generating Mike's FocusOS morning attention briefing. "
        "Use web search when available for current facts. "
        "Do not edit files. Do not run local commands unless needed to answer. "
        "Do not produce financial advice, trading decisions, order instructions, or autonomous actions. "
        "Return strict JSON with keys: title, summary, bullets, action, priority. "
        "Write like an editor, not an assistant. Never use phrases like 'Mike should care', 'why this matters', "
        "'review whether', 'consider whether', or 'decide whether'. "
        "The title must answer why the item is being shown before what happened. "
        "The summary should add concrete context only when useful. "
        "Some summaries can be one short sentence. Bullets must contain at most four short supporting facts. "
        "Set action to an empty string unless immediate action is genuinely warranted. "
        "Never expose source setup, API availability, or implementation details to Mike.\n\n"
        f"Today is {date.today().isoformat()}.\n"
        f"Topic: {topic.name}\n"
        f"Category: {topic.category}\n"
        f"Source type: {topic.source_type}\n"
        f"Priority baseline: {topic.priority}\n"
        f"Prompt: {topic.prompt}"
    )


def generate_openai_payload(topic: Topic) -> dict | None:
    if not os.getenv("OPENAI_API_KEY"):
        raise AIProviderConfigurationError(
            "OPENAI_API_KEY is required when AI_PROVIDER=openai."
        )

    timeout_seconds = float(os.getenv("OPENAI_REQUEST_TIMEOUT", "20"))
    client = OpenAI(timeout=timeout_seconds, max_retries=0)
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search", "search_context_size": "low"}],
        input=briefing_prompt(topic),
    )
    payload = parse_ai_payload(response.output_text, topic)
    return {**payload, "generated_by": "openai-web-search"}


def generate_codex_cli_payload(topic: Topic) -> dict | None:
    codex_path = os.getenv("CODEX_CLI_PATH", "codex")
    timeout_seconds = float(os.getenv("CODEX_CLI_TIMEOUT", "90"))
    workspace = os.getenv("CODEX_CLI_WORKDIR", str(Path(__file__).resolve().parents[2]))

    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=True) as output:
        command = [
            codex_path,
            "--search",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-C",
            workspace,
            "-o",
            output.name,
            briefing_prompt(topic),
        ]
        subprocess.run(  # nosec B603
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
        output.seek(0)
        raw_text = output.read()

    payload = parse_ai_payload(raw_text, topic)
    return {**payload, "generated_by": "codex-cli"}


def generate_ai_payload(topic: Topic) -> dict | None:
    provider = os.getenv(
        "AI_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "fallback"
    ).lower()

    if provider == "codex_cli":
        return generate_codex_cli_payload(topic)
    if provider == "openai":
        return generate_openai_payload(topic)
    if provider == "fallback":
        return None
    raise AIProviderConfigurationError(f"Unsupported AI_PROVIDER {provider!r}.")


def provider_error_message(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        output = (exc.stderr or exc.stdout or "").strip()
        message = f"Provider command exited with status {exc.returncode}."
        if output:
            message = f"{message} {output[-500:]}"
        return message
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"Provider command timed out after {exc.timeout} seconds."
    if isinstance(exc, FileNotFoundError):
        executable = exc.filename or "configured executable"
        return f"Provider executable not found: {executable}."
    return str(exc)
