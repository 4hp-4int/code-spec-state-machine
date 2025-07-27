# Schema Migrations

This directory contains schema migrations for evolving the specification data model over time.

## Creating a New Migration

1. Use the migration manager to create a template:
   ```python
   from agentic_spec.migrations import MigrationManager

   manager = MigrationManager("agentic_spec/migrations")
   filepath = manager.create_migration_template("add_new_field")
   ```

2. Edit the generated file to implement `upgrade()` and `downgrade()` functions

3. Register the migration in your application startup

## Applying Migrations

Migrations are automatically applied when loading specifications:

```python
from agentic_spec.migrations import MigrationManager
import yaml

manager = MigrationManager("agentic_spec/migrations")

# Load and migrate a specification
with open("spec.yaml", "r") as f:
    data = yaml.safe_load(f)

migrated_data = manager.apply_migrations(data)
```

## Rolling Back Migrations

To rollback to a previous version:

```python
rolled_back = manager.rollback_migration(data, target_version="20250101_120000")
```

## Migration History

Migration history is tracked in `migration_history.json` and includes:
- Applied migration versions
- Current schema version
- Timestamps of application

## Best Practices

1. Always implement both `upgrade()` and `downgrade()` functions
2. Test migrations with sample data before applying to production specs
3. Keep migrations small and focused on a single change
4. Document the purpose and changes in the migration docstring
5. Use semantic versioning for tracking major schema changes
