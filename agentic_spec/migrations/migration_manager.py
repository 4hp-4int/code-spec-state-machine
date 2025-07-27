"""Migration manager for schema evolution tracking."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import yaml


class Migration:
    """Base class for schema migrations."""

    def __init__(
        self,
        version: str,
        description: str,
        upgrade_fn: Callable[[dict[str, Any]], dict[str, Any]],
        downgrade_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.version = version
        self.description = description
        self.upgrade_fn = upgrade_fn
        self.downgrade_fn = downgrade_fn
        self.applied_at: datetime | None = None

    def upgrade(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply the migration upgrade."""
        return self.upgrade_fn(data)

    def downgrade(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply the migration downgrade."""
        if not self.downgrade_fn:
            raise NotImplementedError(
                f"Downgrade not implemented for migration {self.version}"
            )
        return self.downgrade_fn(data)


class MigrationManager:
    """Manages schema migrations for specifications."""

    def __init__(self, migrations_dir: Path | str):
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self.migrations: list[Migration] = []
        self.history_file = self.migrations_dir / "migration_history.json"

    def register_migration(self, migration: Migration) -> None:
        """Register a new migration."""
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    def get_migration_history(self) -> dict[str, Any]:
        """Load migration history from file."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return {"applied_migrations": [], "schema_version": "1.0"}

    def save_migration_history(self, history: dict[str, Any]) -> None:
        """Save migration history to file."""
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2, default=str)

    def apply_migrations(self, spec_data: dict[str, Any]) -> dict[str, Any]:
        """Apply all pending migrations to specification data."""
        history = self.get_migration_history()
        applied = set(history["applied_migrations"])

        for migration in self.migrations:
            if migration.version not in applied:
                spec_data = migration.upgrade(spec_data)
                migration.applied_at = datetime.now()
                history["applied_migrations"].append(migration.version)
                history["schema_version"] = migration.version

        self.save_migration_history(history)
        return spec_data

    def rollback_migration(
        self, spec_data: dict[str, Any], target_version: str
    ) -> dict[str, Any]:
        """Rollback migrations to target version."""
        history = self.get_migration_history()
        applied = history["applied_migrations"]

        # Find migrations to rollback
        to_rollback = []
        for migration in reversed(self.migrations):
            if migration.version in applied and migration.version > target_version:
                to_rollback.append(migration)

        # Apply rollbacks
        for migration in to_rollback:
            spec_data = migration.downgrade(spec_data)
            applied.remove(migration.version)

        history["schema_version"] = target_version
        self.save_migration_history(history)
        return spec_data

    def migrate_yaml_file(self, yaml_path: Path) -> None:
        """Migrate a YAML specification file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Apply migrations
        migrated_data = self.apply_migrations(data)

        # Save migrated data
        with open(yaml_path, "w") as f:
            yaml.dump(migrated_data, f, default_flow_style=False, sort_keys=False)

    def create_migration_template(self, name: str) -> Path:
        """Create a new migration template file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.py"
        filepath = self.migrations_dir / filename

        template = f'''"""Migration: {name}
Created: {datetime.now().isoformat()}
"""

from ..migration_manager import Migration


def upgrade(data: dict) -> dict:
    """Apply the migration upgrade.

    This function should modify the specification data structure
    to match the new schema version.
    """
    # TODO: Implement upgrade logic
    return data


def downgrade(data: dict) -> dict:
    """Apply the migration downgrade.

    This function should revert the changes made by upgrade()
    to restore the previous schema version.
    """
    # TODO: Implement downgrade logic
    return data


# Register the migration
migration = Migration(
    version="{timestamp}",
    description="{name}",
    upgrade_fn=upgrade,
    downgrade_fn=downgrade,
)
'''

        with open(filepath, "w") as f:
            f.write(template)

        return filepath
