from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import DisplayedStory
from app.novelty import apply_novelty, record_displayed_stories


def test_novelty_marks_new_changed_and_repeated_stories():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yesterday = date.today() - timedelta(days=1)
    try:
        story = {
            "title": "Review portfolio positioning",
            "why_now": "7 portfolio signals crossed review thresholds.",
            "category": "action",
            "vertical": "Portfolio",
            "detail_id": "portfolio:review",
            "importance_score": 90,
        }

        first = apply_novelty(db, [story], today=yesterday)
        assert first[0]["novelty_status"] == "new"
        record_displayed_stories(db, first, today=yesterday)

        repeated = apply_novelty(db, [story])
        assert repeated[0]["novelty_status"] == "repeated"

        changed_story = {
            **story,
            "why_now": "8 portfolio signals crossed review thresholds.",
        }
        changed = apply_novelty(db, [changed_story])
        assert changed[0]["novelty_status"] == "changed"

        rows = db.query(DisplayedStory).all()
        assert len(rows) == 1
    finally:
        db.close()
