"""Database CLI commands for agentic specification generator.

This module contains commands related to database operations, migrations,
and persistent storage management.
"""

import asyncio
import json
from pathlib import Path

import typer
from typer import Option
import yaml

from .core import SpecGenerator

# Create the database command group
db_app = typer.Typer(
    name="database",
    help="Database and migration management commands",
    no_args_is_help=True,
)


@db_app.command("migrate-bulk")
def migrate_bulk(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    dry_run: bool = Option(False, "--dry-run", help="Validate without migrating"),
    verbose: bool = Option(False, "--verbose", help="Show detailed progress"),
):
    """Migrate all specifications to database."""
    try:
        specs_path = Path(specs_dir)
        templates_path = Path(templates_dir)

        generator = SpecGenerator(templates_path, specs_path)
        print("🔄 Starting bulk migration of specifications...")

        def progress_callback(msg: str):
            if verbose or "Discovered" in msg or "completed" in msg:
                print(f"   {msg}")

        # Run async migration
        async def run_migration():
            return await generator.migrate_specifications(
                full_migration=True,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        results = asyncio.run(run_migration())

        # Display results
        action = "Validated" if dry_run else "Migrated"
        print(f"\n📊 {action} Specifications:")
        print(f"   Total files: {results['total_files']}")
        print(f"   Valid files: {results['valid_files']}")
        print(f"   {action.lower()} files: {results['migrated_files']}")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Warnings: {len(results['warnings'])}")

        success_rate = results["migrated_files"] / max(results["total_files"], 1) * 100
        print(f"   Success rate: {success_rate:.1f}%")

        if results["errors"]:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results["errors"][:5]:  # Show first 5
                file_name = Path(error["file"]).name
                print(f"   {file_name}: {error['error'][:80]}...")
            if len(results["errors"]) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")

        if results["warnings"] and verbose:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results["warnings"][:3]:  # Show first 3
                file_name = Path(warning["file"]).name
                print(f"   {file_name}: {warning['warning'][:80]}...")

        if results["errors"]:
            print("\n💡 Use --verbose for detailed output")
            if not dry_run:
                print("💡 Run with --dry-run first to validate before migrating")

        if results["migrated_files"] == results["total_files"]:
            print(f"\n✅ All specifications {action.lower()} successfully!")
        elif results["migrated_files"] > 0:
            print(
                f"\n⚠️  Partial success: {results['migrated_files']}/{results['total_files']} files {action.lower()}"
            )
        else:
            print(f"\n❌ No files were {action.lower()} successfully")
            raise typer.Exit(1)

    except Exception as e:
        print(f"❌ Error during bulk migration: {e}")
        raise typer.Exit(1)


@db_app.command("migrate-incremental")
def migrate_incremental(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    dry_run: bool = Option(False, "--dry-run", help="Validate without migrating"),
    verbose: bool = Option(False, "--verbose", help="Show detailed progress"),
):
    """Migrate only new or changed specifications to database."""
    try:
        specs_path = Path(specs_dir)
        templates_path = Path(templates_dir)

        generator = SpecGenerator(templates_path, specs_path)

        print("🔄 Starting incremental migration of specifications...")

        def progress_callback(msg: str):
            if verbose or "Discovered" in msg or "completed" in msg:
                print(f"   {msg}")

        # Run async migration
        async def run_migration():
            return await generator.migrate_specifications(
                full_migration=False,  # Incremental mode
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        results = asyncio.run(run_migration())

        # Display results
        action = "Validated" if dry_run else "Migrated"
        print(f"\n📊 {action} Specifications (Incremental):")
        print(f"   Total files checked: {results['total_files']}")
        print(f"   Valid files: {results['valid_files']}")
        print(f"   {action.lower()} files: {results['migrated_files']}")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Warnings: {len(results['warnings'])}")

        if results["total_files"] == 0:
            print("   🎉 No changes detected - all files up to date!")
        else:
            success_rate = (
                results["migrated_files"] / max(results["total_files"], 1) * 100
            )
            print(f"   Success rate: {success_rate:.1f}%")

        if results["errors"] and verbose:
            print("\n❌ Errors:")
            for error in results["errors"]:
                file_name = Path(error["file"]).name
                print(f"   {file_name}: {error['error'][:100]}...")

        if results["migrated_files"] > 0:
            print("\n✅ Incremental migration completed successfully!")
        elif results["total_files"] == 0:
            print("\n✅ No migration needed - all files up to date!")
        else:
            print(f"\n❌ No files were {action.lower()} successfully")
            raise typer.Exit(1)

    except Exception as e:
        print(f"❌ Error during incremental migration: {e}")
        raise typer.Exit(1)


@db_app.command("migration-status")
def migration_status(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
):
    """Show current migration status."""
    try:
        specs_path = Path(specs_dir)

        # Check for migration state file
        state_file = specs_path / ".migration_state.json"
        db_file = specs_path / "specifications.db"

        print("📊 Migration Status:")

        if not state_file.exists():
            print("   ❌ No migration state found")
            print(
                "   💡 Run 'migrate-bulk' or 'migrate-incremental' to start migration"
            )
            return

        # Load migration state
        try:
            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)

            print(f"   📁 Tracked files: {len(state)}")

            # Get latest migration time
            latest_time = None
            for file_info in state.values():
                modified = file_info.get("modified", 0)
                if latest_time is None or modified > latest_time:
                    latest_time = modified

            if latest_time:
                import datetime

                latest_dt = datetime.datetime.fromtimestamp(latest_time)
                print(
                    f"   🕐 Last migration check: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"   ❌ Error reading migration state: {e}")

        # Check database file
        if db_file.exists():
            print(f"   💾 Database file: {db_file}")
            print(f"   📊 Database size: {db_file.stat().st_size / 1024:.1f} KB")
        else:
            print("   ❌ No database file found")
            print("   💡 Use 'migrate-bulk' to create database")

        # Count YAML files
        yaml_files = list(specs_path.glob("*.yaml"))
        spec_count = 0
        for file_path in yaml_files:
            if file_path.name not in ["yaml-to-db-mapping.yaml", "migration-plan.yaml"]:
                spec_count += 1

        print(f"   📄 YAML specifications: {spec_count}")

        # Suggest actions
        if not db_file.exists():
            print("\n💡 Suggestions:")
            print("   • Run 'agentic-spec migrate-bulk --dry-run' to validate")
            print("   • Run 'agentic-spec migrate-bulk' to create database")
        else:
            print("\n💡 Suggestions:")
            print("   • Run 'agentic-spec migrate-incremental' to sync changes")
            print("   • Run 'agentic-spec migration-report' for detailed analysis")

    except Exception as e:
        print(f"❌ Error checking migration status: {e}")
        raise typer.Exit(1)


@db_app.command("migration-report")
def migration_report(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    output_format: str = Option(
        "table", "--format", help="Output format: table, yaml, json"
    ),
    save_file: str = Option(None, "--save", help="Save report to file"),
):
    """Generate detailed migration report."""
    try:
        specs_path = Path(specs_dir)

        # Basic file analysis
        yaml_files = list(specs_path.glob("*.yaml"))
        spec_files = []
        doc_files = []

        for file_path in yaml_files:
            if file_path.name in ["yaml-to-db-mapping.yaml", "migration-plan.yaml"]:
                doc_files.append(file_path)
            else:
                spec_files.append(file_path)

        # Load migration state if exists
        state_file = specs_path / ".migration_state.json"
        migration_state = {}
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    migration_state = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Generate report data
        from datetime import datetime

        report = {
            "generated_at": datetime.now().isoformat(),
            "specs_directory": str(specs_path),
            "summary": {
                "total_yaml_files": len(yaml_files),
                "specification_files": len(spec_files),
                "documentation_files": len(doc_files),
                "tracked_files": len(migration_state),
                "database_exists": (specs_path / "specifications.db").exists(),
            },
            "files": [],
        }

        # Analyze each spec file
        for file_path in spec_files:
            file_info = {
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "tracked": str(file_path) in migration_state,
            }

            # Try to get spec ID and title
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "metadata" in data:
                        file_info["spec_id"] = data["metadata"].get("id", "unknown")
                        file_info["title"] = data["metadata"].get("title", "unknown")
                        file_info["status"] = data["metadata"].get("status", "unknown")
            except:
                file_info["spec_id"] = "unknown"
                file_info["title"] = "parse_error"
                file_info["status"] = "error"

            report["files"].append(file_info)

        # Output report
        if output_format.lower() == "json":
            report_str = json.dumps(report, indent=2, default=str)
        elif output_format.lower() == "yaml":
            report_str = yaml.dump(report, default_flow_style=False, sort_keys=False)
        else:  # table format
            report_str = _format_migration_report_table(report)

        if save_file:
            save_path = Path(save_file)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(report_str)
            print(f"📄 Report saved to: {save_path}")
        else:
            print(report_str)

    except Exception as e:
        print(f"❌ Error generating migration report: {e}")
        raise typer.Exit(1)


def _format_migration_report_table(report: dict) -> str:
    """Format migration report as a table."""
    lines = []
    lines.append("📊 Migration Report")
    lines.append("=" * 50)

    summary = report["summary"]
    lines.append(f"📁 Specifications Directory: {report['specs_directory']}")
    lines.append(f"🕐 Generated: {report['generated_at']}")
    lines.append("")

    lines.append("📈 Summary:")
    lines.append(f"   Total YAML files: {summary['total_yaml_files']}")
    lines.append(f"   Specification files: {summary['specification_files']}")
    lines.append(f"   Documentation files: {summary['documentation_files']}")
    lines.append(f"   Tracked files: {summary['tracked_files']}")
    lines.append(f"   Database exists: {'✅' if summary['database_exists'] else '❌'}")
    lines.append("")

    lines.append("📋 Files:")
    lines.append(
        f"{'Name':<30} {'Spec ID':<12} {'Status':<12} {'Tracked':<8} {'Size':<8}"
    )
    lines.append("-" * 80)

    for file_info in report["files"]:
        name = file_info["name"][:28]
        spec_id = str(file_info["spec_id"])[:10]
        status = str(file_info["status"])[:10]
        tracked = "✅" if file_info["tracked"] else "❌"
        size = f"{file_info['size'] / 1024:.1f}KB"

        lines.append(f"{name:<30} {spec_id:<12} {status:<12} {tracked:<8} {size:<8}")

    return "\n".join(lines)
