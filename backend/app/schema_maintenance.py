from __future__ import annotations

from sqlalchemy import inspect, text

from .database import Base, engine


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_watch_item_schema()


def ensure_watch_item_schema() -> None:
    dialect = engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        return

    with engine.begin() as connection:
        if dialect == "sqlite":
            columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(watch_items)")
            }
        else:
            inspector = inspect(connection)
            if "watch_items" not in inspector.get_table_names():
                return
            columns = {
                column["name"] for column in inspector.get_columns("watch_items")
            }
        if "watch_kind" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE watch_items "
                    "ADD COLUMN watch_kind VARCHAR(40) DEFAULT 'personal_tracker'"
                )
            )
        if "priority" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE watch_items "
                    "ADD COLUMN priority VARCHAR(40) DEFAULT 'watch_only'"
                )
            )
        if "enabled" not in columns:
            enabled_default = (
                "BOOLEAN DEFAULT TRUE" if dialect == "postgresql" else "BOOLEAN DEFAULT 1"
            )
            connection.execute(
                text(f"ALTER TABLE watch_items ADD COLUMN enabled {enabled_default}")
            )
        if "personal_state" not in columns:
            json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
            connection.execute(
                text(f"ALTER TABLE watch_items ADD COLUMN personal_state {json_default}")
            )
            connection.execute(
                text(
                    "UPDATE watch_items SET personal_state = '{}' "
                    "WHERE personal_state IS NULL"
                )
            )
        if "external_state" not in columns:
            json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
            connection.execute(
                text(f"ALTER TABLE watch_items ADD COLUMN external_state {json_default}")
            )
            connection.execute(
                text(
                    "UPDATE watch_items SET external_state = '{}' "
                    "WHERE external_state IS NULL"
                )
            )
        for column_name in (
            "personal_context",
            "source_config",
            "evaluation_rules",
            "prompt_config",
        ):
            if column_name not in columns:
                json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
                connection.execute(
                    text(f"ALTER TABLE watch_items ADD COLUMN {column_name} {json_default}")
                )
                reset_statements = {
                    "personal_context": (
                        "UPDATE watch_items SET personal_context = '{}' "
                        "WHERE personal_context IS NULL"
                    ),
                    "source_config": (
                        "UPDATE watch_items SET source_config = '{}' "
                        "WHERE source_config IS NULL"
                    ),
                    "evaluation_rules": (
                        "UPDATE watch_items SET evaluation_rules = '{}' "
                        "WHERE evaluation_rules IS NULL"
                    ),
                    "prompt_config": (
                        "UPDATE watch_items SET prompt_config = '{}' "
                        "WHERE prompt_config IS NULL"
                    ),
                }
                connection.execute(text(reset_statements[column_name]))
