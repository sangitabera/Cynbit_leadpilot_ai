
from sqlalchemy import inspect, text

from app.database.connection import engine


def migrate_database(db_engine):
    """Add lifecycle columns to existing SQLite databases safely."""

    inspector = inspect(db_engine)

    if "leads" not in inspector.get_table_names():
        # First-time startup: create_all() will create the latest schema.
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("leads")
    }

    migrations = {
        "lifecycle_status": (
            "ALTER TABLE leads ADD COLUMN "
            "lifecycle_status VARCHAR(30) "
            "NOT NULL DEFAULT 'AI Analysed'"
        ),
        "assigned_to": (
            "ALTER TABLE leads ADD COLUMN "
            "assigned_to VARCHAR(200)"
        ),
        "review_notes": (
            "ALTER TABLE leads ADD COLUMN "
            "review_notes TEXT"
        ),
        "updated_at": (
            "ALTER TABLE leads ADD COLUMN "
            "updated_at DATETIME"
        ),
        "converted_at": (
            "ALTER TABLE leads ADD COLUMN "
            "converted_at DATETIME"
        ),
    }

    with db_engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))

        # Existing records have already been analysed.
        connection.execute(
            text("""
                UPDATE leads
                SET lifecycle_status = 'AI Analysed'
                WHERE lifecycle_status IS NULL
                   OR lifecycle_status = ''
            """)
        )

        connection.execute(
            text("""
                UPDATE leads
                SET updated_at = created_at
                WHERE updated_at IS NULL
            """)
        )
