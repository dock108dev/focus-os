from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base


def test_api_responses_include_browser_security_headers():
    client = TestClient(main.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_unsafe_requests_reject_untrusted_browser_origins():
    client = TestClient(main.app)

    response = client.post(
        "/api/jobs/morning-briefing",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403


def test_internal_routes_require_key_when_configured(monkeypatch):
    monkeypatch.setenv("FOCUSOS_INTERNAL_API_KEY", "test-secret")
    client = TestClient(main.app)

    missing = client.post("/api/jobs/morning-briefing")
    wrong = client.post(
        "/api/jobs/morning-briefing", headers={"X-FocusOS-Key": "wrong"}
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_import_rejects_oversized_csv_before_parsing(monkeypatch):
    monkeypatch.setenv("FOCUSOS_MAX_IMPORT_BYTES", "16")
    client = TestClient(main.app)

    response = client.post(
        "/api/import/holdings?source=Manual&replace=true",
        files={"file": ("holdings.csv", b"symbol,name\nMSFT,Microsoft\n", "text/csv")},
    )

    assert response.status_code == 413


def test_import_rejects_non_csv_upload():
    client = TestClient(main.app)

    response = client.post(
        "/api/import/holdings?source=Manual&replace=true",
        files={
            "file": ("holdings.txt", b"symbol,name\nMSFT,Microsoft\n", "text/plain")
        },
    )

    assert response.status_code == 415


def test_import_accepts_csv_with_local_origin(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.delenv("FOCUSOS_MAX_IMPORT_BYTES", raising=False)
    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        response = client.post(
            "/api/import/holdings?source=Manual&replace=true",
            headers={"Origin": "http://localhost:5173"},
            files={
                "file": (
                    "holdings.csv",
                    b"symbol,name,quantity,price,market value,cost basis\nMSFT,Microsoft,1,430,430,400\n",
                    "text/csv",
                )
            },
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["imported"] == 1


def test_briefing_payload_uses_attention_as_homepage_ssot(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            main.seed_if_empty(db)
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        response = client.get("/api/briefing")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "attention" in payload
    assert "financial_attention" not in payload
    assert "portfolio_intelligence" not in payload
    assert payload["attention"][0]["domain"] == "Portfolio"
    assert payload["attention"][0]["attention_bucket"] == "Today"
    assert payload["attention"][0]["suggested_posture"] == "Review"
    metadata = payload["attention"][0]["generation_metadata"]
    assert set(metadata) == {
        "why_generated",
        "what_changed",
        "why_user_should_care",
        "expiration_date",
    }
