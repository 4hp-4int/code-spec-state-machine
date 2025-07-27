"""Migration 002: Add enhanced tracking fields to specifications and tasks tables."""

from .migration_manager import Migration


class Migration002(Migration):
    """Add enhanced tracking fields for workflow status, completion tracking, and timestamps."""

    version = "002"
    description = "Add enhanced tracking fields to specifications and tasks tables"

    async def up(self, connection) -> None:
        """Apply the migration - add new tracking fields."""
        # Add columns to specifications table
        spec_columns = [
            "ALTER TABLE specifications ADD COLUMN workflow_status TEXT DEFAULT 'created'",
            "ALTER TABLE specifications ADD COLUMN is_completed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE specifications ADD COLUMN completed_at TIMESTAMP",
            "ALTER TABLE specifications ADD COLUMN last_accessed TIMESTAMP",
            "ALTER TABLE specifications ADD COLUMN completion_percentage REAL DEFAULT 0.0",
            "ALTER TABLE specifications ADD COLUMN priority INTEGER DEFAULT 5",
            "ALTER TABLE specifications ADD COLUMN reviewed_at TIMESTAMP",
            "ALTER TABLE specifications ADD COLUMN approved_at TIMESTAMP",
            "ALTER TABLE specifications ADD COLUMN implemented_at TIMESTAMP",
            "ALTER TABLE specifications ADD COLUMN created_by TEXT DEFAULT 'system'",
            "ALTER TABLE specifications ADD COLUMN last_updated_by TEXT DEFAULT 'system'",
            "ALTER TABLE specifications ADD COLUMN tags TEXT DEFAULT '[]'",
        ]

        # Add columns to tasks table
        task_columns = [
            "ALTER TABLE tasks ADD COLUMN is_completed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE tasks ADD COLUMN assigned_to TEXT DEFAULT 'unassigned'",
            "ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 5",
            "ALTER TABLE tasks ADD COLUMN last_accessed TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN estimated_completion_date TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN actual_effort_minutes INTEGER",
            "ALTER TABLE tasks ADD COLUMN dependencies TEXT DEFAULT '[]'",
            "ALTER TABLE tasks ADD COLUMN blocked_at TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN unblocked_at TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN approved_at TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN rejected_at TIMESTAMP",
        ]

        # Execute all column additions
        for sql in spec_columns + task_columns:
            try:
                await connection.execute(sql)
            except Exception as e:
                # Column might already exist - this is OK for idempotent migrations
                if "duplicate column name" not in str(e).lower():
                    raise

        # Create new indexes for performance
        indexes = [
            # Specifications indexes
            "CREATE INDEX IF NOT EXISTS idx_specs_workflow_status ON specifications (workflow_status)",
            "CREATE INDEX IF NOT EXISTS idx_specs_is_completed ON specifications (is_completed)",
            "CREATE INDEX IF NOT EXISTS idx_specs_priority ON specifications (priority)",
            "CREATE INDEX IF NOT EXISTS idx_specs_completed_at ON specifications (completed_at)",
            "CREATE INDEX IF NOT EXISTS idx_specs_tags ON specifications (tags)",
            # Tasks indexes
            "CREATE INDEX IF NOT EXISTS idx_tasks_is_completed ON tasks (is_completed)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks (assigned_to)",
        ]

        for index_sql in indexes:
            await connection.execute(index_sql)

        await connection.commit()

        # Update existing records with sensible defaults
        await self._update_existing_records(connection)

    async def down(self, connection) -> None:
        """Rollback the migration - remove tracking fields."""
        # Note: SQLite doesn't support DROP COLUMN, so we can't easily rollback
        # In a production system, you'd create a new table without these columns
        # and copy data over, then rename tables
        print("Warning: SQLite doesn't support DROP COLUMN. Manual rollback required.")

    async def _update_existing_records(self, connection) -> None:
        """Update existing records with sensible defaults."""

        # Update specifications based on their current status
        status_mappings = {
            "draft": "created",
            "reviewed": "ready_for_review",
            "approved": "ready_for_implementation",
            "implemented": "completed",
            "archived": "completed",
        }

        for old_status, new_workflow_status in status_mappings.items():
            update_sql = """
            UPDATE specifications
            SET workflow_status = ?,
                is_completed = ?,
                completion_percentage = ?
            WHERE status = ? AND workflow_status = 'created'
            """

            is_completed = old_status in ["implemented", "archived"]
            completion_pct = 100.0 if is_completed else 0.0

            await connection.execute(
                update_sql,
                (new_workflow_status, is_completed, completion_pct, old_status),
            )

        # Update tasks based on their current status
        task_status_mappings = {
            "completed": True,
            "approved": True,
        }

        for status, is_completed in task_status_mappings.items():
            await connection.execute(
                "UPDATE tasks SET is_completed = ? WHERE status = ?",
                (is_completed, status),
            )

        await connection.commit()


# Register the migration
migration = Migration002()
