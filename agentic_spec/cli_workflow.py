"""Workflow CLI commands for agentic specification generator.

This module contains commands related to workflow management, task tracking,
and specification lifecycle operations.
"""

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import uuid

import typer
from typer import Argument, Option

from .async_db import AsyncSpecManager, SQLiteBackend
from .cli_core import initialize_generator
from .exceptions import (
    AgenticSpecError,
    SpecificationError,
    SyncFoundationConfigError,
)
from .graph_visualization import print_spec_graph
from .models import (
    ApprovalDB,
    ApprovalLevel,
    SpecStatus,
    TaskStatus,
    WorkflowStatus,
)

# Create the workflow command group
workflow_app = typer.Typer(
    name="workflow",
    help="Workflow management and task tracking commands",
    no_args_is_help=True,
)


@workflow_app.command("task-start")
def start_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    started_by: str = Option("user", "--by", help="Who is starting the task"),
    notes: str | None = Option(
        None, "--notes", help="Optional notes for starting the task"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    strict_mode: bool = Option(
        True, "--strict/--no-strict", help="Enable strict mode enforcement"
    ),
):
    """Start working on a task."""

    async def start_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)

                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break

                if not target_task:
                    print(
                        f"❌ Task at step {step_index} not found for specification {spec_id}"
                    )
                    raise typer.Exit(1)

                # Check if task can be started
                if target_task.status not in [TaskStatus.PENDING, TaskStatus.BLOCKED]:
                    print(f"❌ Task {step_id} is already {target_task.status.value}")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.IN_PROGRESS:
                        print(f"   Started at: {target_task.started_at}")
                    elif target_task.status == TaskStatus.COMPLETED:
                        print(f"   Completed at: {target_task.completed_at}")
                    raise typer.Exit(1)

                # Strict mode enforcement - check if previous tasks are completed
                if strict_mode and step_index > 0:
                    for task in tasks:
                        if task.step_index < step_index and task.status not in [
                            TaskStatus.COMPLETED,
                            TaskStatus.APPROVED,
                        ]:
                            print(
                                f"❌ Strict mode violation: Task {task.step_index} must be completed before starting task {step_index}"
                            )
                            print(f"   Blocking task status: {task.status.value}")
                            print(
                                f"   Use --no-strict to override, or complete task {spec_id}:{task.step_index} first"
                            )
                            raise typer.Exit(1)

                # Update task to in_progress
                target_task.status = TaskStatus.IN_PROGRESS
                target_task.started_at = datetime.now()
                if notes:
                    target_task.completion_notes = notes

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} started by {started_by}")
                print(f"📋 Task: {target_task.task}")

                if notes:
                    print(f"📝 Notes: {notes}")

                print(
                    f"⏰ Started at: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error starting task: {e}")
            raise typer.Exit(1)

    asyncio.run(start_task_async())


@workflow_app.command("task-complete")
def complete_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    completed_by: str = Option("user", "--by", help="Who completed the task"),
    notes: str | None = Option(None, "--notes", help="Completion notes"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Mark a task as completed."""

    async def complete_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)

                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break

                if not target_task:
                    print(
                        f"❌ Task at step {step_index} not found for specification {spec_id}"
                    )
                    raise typer.Exit(1)

                # Check if task can be completed
                if target_task.status != TaskStatus.IN_PROGRESS:
                    print(f"❌ Task {step_id} is not in progress")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.COMPLETED:
                        print(f"   Already completed at: {target_task.completed_at}")
                    elif target_task.status == TaskStatus.PENDING:
                        print(
                            f"   Task must be started first: agentic-spec task-start {step_id}"
                        )
                    raise typer.Exit(1)

                # Update task to completed
                target_task.status = TaskStatus.COMPLETED
                target_task.completed_at = datetime.now()
                if notes:
                    if target_task.completion_notes:
                        target_task.completion_notes += (
                            f"\n\nCompletion notes by {completed_by}: {notes}"
                        )
                    else:
                        target_task.completion_notes = (
                            f"Completion notes by {completed_by}: {notes}"
                        )

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} completed by {completed_by}")
                print(f"📋 Task: {target_task.task}")

                if notes:
                    print(f"📝 Completion notes: {notes}")

                print(
                    f"⏰ Completed at: {target_task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Calculate duration if we have start time
                if target_task.started_at:
                    duration = target_task.completed_at - target_task.started_at
                    hours = duration.total_seconds() / 3600
                    print(f"⌛ Duration: {hours:.1f} hours")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error completing task: {e}")
            raise typer.Exit(1)

    asyncio.run(complete_task_async())


@workflow_app.command("workflow-status")
def show_workflow_status(
    spec_id: str = Argument(..., help="Specification ID"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    strict_mode: bool = Option(
        True, "--strict/--no-strict", help="Show status with strict mode context"
    ),
):
    """Show comprehensive workflow status for a specification."""

    async def get_workflow_status_async():
        db_path = Path(specs_dir) / "specifications.db"
        backend = SQLiteBackend(str(db_path))

        async with AsyncSpecManager(backend) as manager:
            # Get specification
            spec = await manager.get_specification(spec_id)
            if not spec:
                raise ValueError(f"Specification {spec_id} not found")

            # Get tasks
            tasks = await manager.backend.get_tasks_for_spec(spec_id)

            # Calculate status
            total_tasks = len(tasks)
            completed_tasks = sum(
                1
                for task in tasks
                if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED]
            )
            completion_percentage = (
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            )

            # Count tasks by status
            status_counts = {}
            for task in tasks:
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            # Find next available task
            next_available_task = None
            for task in tasks:
                if task.status.value == "pending":
                    next_available_task = f"{task.id}: {task.task}"
                    break

            return {
                "spec_title": spec.title,
                "spec_author": getattr(spec, "created_by", None),
                "spec_created": spec.created,
                "spec_updated": spec.updated,
                "spec_parent_id": spec.parent_spec_id,
                "spec_child_ids": spec.child_spec_ids,
                "workflow_status": spec.workflow_status.value,
                "is_completed": spec.is_completed,
                "completion_percentage": completion_percentage,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks,
                "strict_mode": strict_mode,
                "status_counts": status_counts,
                "next_available_task": next_available_task,
                "required_approval_levels": [],  # Empty for now
                "tasks": [
                    {
                        "id": task.id,
                        "step_id": task.id,  # Use task.id as step_id
                        "task": task.task,
                        "status": task.status.value,
                        "is_completed": task.is_completed,
                        "estimated_effort": task.estimated_effort,
                        "can_start": task.status.value
                        == "pending",  # Simple logic for now
                        "required_approval_levels": [],  # Empty for now
                    }
                    for task in tasks
                ],
            }

    try:
        status = asyncio.run(get_workflow_status_async())

        print(f"📊 Workflow Status: {spec_id}")
        print(f"   Title: {status['spec_title']}")
        print(f"   Author: {status.get('spec_author', 'N/A')}")
        print(f"   Created: {status['spec_created'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(
            f"   Last Updated: {status['spec_updated'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if status.get("spec_parent_id"):
            print(f"   Parent Spec: {status['spec_parent_id']}")
        if status.get("spec_child_ids"):
            print(f"   Child Specs: {', '.join(status['spec_child_ids'])}")
        print(f"   Total Tasks: {status['total_tasks']}")
        print(f"   Completion: {status['completion_percentage']}%")
        print(
            f"   Strict Mode: {'✅ Enabled' if status['strict_mode'] else '❌ Disabled'}"
        )

        print("\n📈 Task Breakdown:")
        for status_name, count in status["status_counts"].items():
            if count > 0:
                emoji = {
                    "pending": "⏳",
                    "in_progress": "🚀",
                    "completed": "✅",
                    "approved": "🎉",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status_name, "📋")
                print(f"   {emoji} {status_name.replace('_', ' ').title()}: {count}")

        if status["next_available_task"]:
            print(f"\n🎯 Next Available Task: {status['next_available_task']}")

        print("\n📋 All Tasks:")
        for task in status["tasks"]:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🚀",
                "completed": "✅",
                "approved": "🎉",
                "rejected": "❌",
                "blocked": "🚫",
            }.get(task["status"], "📋")

            availability = "🟢" if task["can_start"] else "🔴"
            print(f"   {status_emoji} {availability} {task['step_id']}: {task['task']}")

            if task.get("time_spent_minutes"):
                print(f"     ⏱️  {task['time_spent_minutes']} minutes")
            if task.get("blockers"):
                print(f"     🚫 Blocked by: {', '.join(task['blockers'])}")

        print(
            f"\n📝 Required Approvals: {', '.join(status['required_approval_levels'])}"
        )

    except Exception as e:
        print(f"❌ Error getting workflow status: {e}")
        raise typer.Exit(1)


@workflow_app.command("publish")
def publish_spec(
    spec_id: str = Argument(..., help="Specification ID to mark as implemented"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Mark a specification as implemented and update its status.

    Changes the specification status from 'draft' to 'implemented' and
    updates the specification graph.
    """

    async def _publish():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                Path("templates"),
                Path(specs_dir),
                Path(config) if config else None,
                None,
                set_options,
            )

            # Find the specification
            target_spec = generator.find_spec_by_id(spec_id)
            if not target_spec:
                print(f"❌ Specification {spec_id} not found")
                return

            # Update status to implemented
            target_spec.metadata.status = "implemented"

            # Save the updated spec
            generator.save_spec(target_spec)

            print(f"✅ Specification {spec_id[:8]} published as implemented")
            print("📋 Status updated: draft → implemented")

            # Show updated graph
            print("\n📊 Updated specification graph:")
            print_spec_graph(specs_dir)

            # Sync status in database without touching existing tasks
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            async with AsyncSpecManager(backend) as manager:
                spec_db = await manager.backend.get_specification(spec_id)
                if spec_db:
                    spec_db.status = SpecStatus.IMPLEMENTED
                    spec_db.workflow_status = WorkflowStatus.COMPLETED
                    spec_db.updated = datetime.now()
                    spec_db.completed_at = datetime.now()
                    spec_db.is_completed = True
                    await manager.backend.update_specification(spec_db)

        except Exception:
            logger.exception("Error publishing spec")
            print("❌ Failed to publish specification")
            raise typer.Exit(1) from None

    asyncio.run(_publish())


@workflow_app.command("task-approve")
def approve_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    approved_by: str = Option("user", "--by", help="Who is approving the task"),
    level: str = Option(
        "self", "--level", help="Approval level: self, peer, ai, admin"
    ),
    comments: str | None = Option(None, "--comments", help="Approval comments"),
    override_reason: str | None = Option(
        None, "--override", help="Override reason if needed"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Approve a completed task."""

    async def approve_task_async():
        try:
            # Validate approval level
            try:
                approval_level = ApprovalLevel(level.lower())
            except ValueError:
                valid_levels = [level.value for level in ApprovalLevel]
                print(
                    f"❌ Invalid approval level. Valid levels: {', '.join(valid_levels)}"
                )
                raise typer.Exit(1)

            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)

                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break

                if not target_task:
                    print(
                        f"❌ Task at step {step_index} not found for specification {spec_id}"
                    )
                    raise typer.Exit(1)

                # Check if task can be approved
                if target_task.status != TaskStatus.COMPLETED:
                    print(f"❌ Task {step_id} is not completed")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.PENDING:
                        print("   Task must be started and completed first")
                    elif target_task.status == TaskStatus.IN_PROGRESS:
                        print(
                            f"   Task must be completed first: agentic-spec task-complete {step_id}"
                        )
                    raise typer.Exit(1)

                # Create approval record
                approval = ApprovalDB(
                    id=str(uuid.uuid4()),
                    task_id=target_task.id,
                    level=approval_level,
                    approved_by=approved_by,
                    approved_at=datetime.now(),
                    comments=comments,
                    override_reason=override_reason,
                )

                await manager.backend.create_approval(approval)

                # Update task status to approved
                target_task.status = TaskStatus.APPROVED
                target_task.approved_at = datetime.now()
                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} approved by {approved_by} ({level})")
                print(f"📋 Task: {target_task.task}")

                if comments:
                    print(f"💬 Comments: {comments}")
                if override_reason:
                    print(f"⚠️  Override reason: {override_reason}")

                print(
                    f"⏰ Approved at: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error approving task: {e}")
            raise typer.Exit(1)

    asyncio.run(approve_task_async())


@workflow_app.command("task-reject")
def reject_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    rejected_by: str = Option("user", "--by", help="Who is rejecting the task"),
    reason: str = Option(..., "--reason", help="Rejection reason"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Reject a task, requiring rework."""

    async def reject_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)

                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break

                if not target_task:
                    print(
                        f"❌ Task at step {step_index} not found for specification {spec_id}"
                    )
                    raise typer.Exit(1)

                # Check if task can be rejected
                if target_task.status not in [
                    TaskStatus.COMPLETED,
                    TaskStatus.APPROVED,
                ]:
                    print(f"❌ Task {step_id} cannot be rejected")
                    print(f"   Current status: {target_task.status.value}")
                    print("   Only completed or approved tasks can be rejected")
                    raise typer.Exit(1)

                # Update task to rejected and reset to pending for rework
                target_task.status = TaskStatus.REJECTED
                target_task.rejected_at = datetime.now()
                if target_task.completion_notes:
                    target_task.completion_notes += (
                        f"\n\nRejected by {rejected_by}: {reason}"
                    )
                else:
                    target_task.completion_notes = (
                        f"Rejected by {rejected_by}: {reason}"
                    )

                await manager.backend.update_task(target_task)

                print(f"❌ Task {step_id} rejected by {rejected_by}")
                print(f"📋 Task: {target_task.task}")
                print(f"📝 Reason: {reason}")
                print(
                    f"⏰ Rejected at: {target_task.rejected_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print("🔄 Task requires rework - reset to rejected status")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error rejecting task: {e}")
            raise typer.Exit(1)

    asyncio.run(reject_task_async())


@workflow_app.command("task-block")
def block_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    blocked_by: str = Option("user", "--by", help="Who is blocking the task"),
    blockers: list[str] = Option(
        ..., "--blocker", help="Blocking issues (can specify multiple)"
    ),
    notes: str | None = Option(
        None, "--notes", help="Additional notes about the block"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Block a task due to external dependencies or issues."""

    async def block_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)

                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break

                if not target_task:
                    print(
                        f"❌ Task at step {step_index} not found for specification {spec_id}"
                    )
                    raise typer.Exit(1)

                # Update task to blocked
                target_task.status = TaskStatus.BLOCKED
                target_task.blocked_at = datetime.now()
                target_task.blockers = blockers
                if notes:
                    if target_task.completion_notes:
                        target_task.completion_notes += (
                            f"\n\nBlocked by {blocked_by}: {notes}"
                        )
                    else:
                        target_task.completion_notes = (
                            f"Blocked by {blocked_by}: {notes}"
                        )

                await manager.backend.update_task(target_task)

                print(f"🚫 Task {step_id} blocked by {blocked_by}")
                print(f"📋 Task: {target_task.task}")
                print(f"🔒 Blockers: {', '.join(blockers)}")
                if notes:
                    print(f"📝 Notes: {notes}")
                print(
                    f"⏰ Blocked at: {target_task.blocked_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error blocking task: {e}")
            raise typer.Exit(1)

    asyncio.run(block_task_async())


@workflow_app.command("task-unblock")
def unblock_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    unblocked_by: str = Option("user", "--by", help="Who is unblocking the task"),
    resolution: str = Option(
        ..., "--resolution", help="How the blockers were resolved"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Unblock a task and return it to pending status."""

    async def unblock_task_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next(
                    (t for t in tasks if t.step_index == step_index), None
                )

                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                if target_task.status != TaskStatus.BLOCKED:
                    print(
                        f"❌ Task {step_id} is not blocked (status: {target_task.status.value})"
                    )
                    raise typer.Exit(1)

                target_task.status = TaskStatus.PENDING
                target_task.unblocked_at = datetime.now()
                target_task.blockers = []
                if target_task.completion_notes:
                    target_task.completion_notes += (
                        f"\n\nUnblocked by {unblocked_by}: {resolution}"
                    )
                else:
                    target_task.completion_notes = (
                        f"Unblocked by {unblocked_by}: {resolution}"
                    )

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} unblocked by {unblocked_by}")
                print(f"🔓 Resolution: {resolution}")
                print(
                    f"⏰ Unblocked at: {target_task.unblocked_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error unblocking task: {e}")
            raise typer.Exit(1)

    asyncio.run(unblock_task_async())


@workflow_app.command("task-override")
def override_strict_mode(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    override_by: str = Option("user", "--by", help="Who is overriding strict mode"),
    reason: str = Option(..., "--reason", help="Reason for override"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Override strict mode to start a task out of sequence."""

    async def override_task_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next(
                    (t for t in tasks if t.step_index == step_index), None
                )

                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                if target_task.status != TaskStatus.PENDING:
                    print(
                        f"❌ Task {step_id} is not pending (status: {target_task.status.value})"
                    )
                    raise typer.Exit(1)

                # Start the task with override
                target_task.status = TaskStatus.IN_PROGRESS
                target_task.started_at = datetime.now()
                if target_task.completion_notes:
                    target_task.completion_notes += (
                        f"\n\nStrict mode override by {override_by}: {reason}"
                    )
                else:
                    target_task.completion_notes = (
                        f"Strict mode override by {override_by}: {reason}"
                    )

                await manager.backend.update_task(target_task)

                print(f"⚠️  Strict mode overridden for task {step_id}")
                print(f"👤 Override by: {override_by}")
                print(f"📝 Reason: {reason}")
                print("🚀 Task has been started with override")
                print(
                    f"⏰ Started at: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error overriding strict mode: {e}")
            raise typer.Exit(1)

    asyncio.run(override_task_async())


@workflow_app.command("task-status")
def show_task_status(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Show detailed status information for a task."""

    async def show_task_status_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter(
                    "Step ID must be in format 'spec_id:step_index'"
                )

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            async with AsyncSpecManager(backend) as manager:
                # Get specification and tasks
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next(
                    (t for t in tasks if t.step_index == step_index), None
                )

                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                # Get approvals for this task
                approvals = await manager.backend.get_approvals_for_task(target_task.id)

                print(f"📋 Task Status: {step_id}")
                print(f"   Task: {target_task.task}")
                print(f"   Status: {target_task.status.value}")
                print(f"   Estimated Effort: {target_task.estimated_effort}")
                print(f"   Files: {', '.join(target_task.files)}")

                print("\n🚦 Actions Available:")
                can_start = target_task.status in [
                    TaskStatus.PENDING,
                    TaskStatus.BLOCKED,
                ]
                can_complete = target_task.status == TaskStatus.IN_PROGRESS
                can_approve = target_task.status == TaskStatus.COMPLETED
                print(f"   Can start: {'✅' if can_start else '❌'}")
                print(f"   Can complete: {'✅' if can_complete else '❌'}")
                print(f"   Can approve: {'✅' if can_approve else '❌'}")

                if target_task.started_at:
                    print("\n⏱️  Timing:")
                    print(
                        f"   Started: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if target_task.completed_at:
                        print(
                            f"   Completed: {target_task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        duration = target_task.completed_at - target_task.started_at
                        hours = duration.total_seconds() / 3600
                        print(f"   Duration: {hours:.1f} hours")
                    if target_task.time_spent_minutes:
                        print(
                            f"   Time Spent: {target_task.time_spent_minutes} minutes"
                        )

                if target_task.completion_notes:
                    print(f"\n📝 Notes: {target_task.completion_notes}")

                if target_task.blockers:
                    print("\n🚫 Blockers:")
                    for blocker in target_task.blockers:
                        print(f"   • {blocker}")

                if approvals:
                    print("\n✅ Approvals:")
                    for approval in approvals:
                        print(
                            f"   • {approval.level.value} by {approval.approved_by} at {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        if approval.comments:
                            print(f"     💬 {approval.comments}")
                        if approval.override_reason:
                            print(f"     ⚠️  Override: {approval.override_reason}")

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error getting task status: {e}")
            raise typer.Exit(1)

    asyncio.run(show_task_status_async())


@workflow_app.command("sync-foundation")
def sync_foundation_spec(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    discovery_config: str | None = Option(
        None,
        "--discovery-config",
        help="Path to sync-foundation discovery configuration file",
    ),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
    force: bool = Option(
        False, "--force", help="Force sync even if foundation spec is current"
    ),
):
    """Sync foundation specification with current codebase state.
    Analyzes the current codebase structure, dependencies, and architecture
    to update the agentic-spec-foundation.yaml template with accurate information.
    Enhanced Analysis Features:
    • Multi-source dependency detection (pyproject.toml, requirements.txt, setup.py)
    • Transitive dependency resolution using importlib.metadata
    • Advanced file categorization (CLI, web UI, database, API, test, config files)
    • Content-based categorization using file analysis
    • Architectural pattern detection (FastAPI, async operations, migrations)
    • Comprehensive skip patterns for virtual environments and build artifacts
    """

    async def _sync():
        logger = logging.getLogger("agentic_spec")
        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, discovery_config, set_options
            )
            print("🔍 Analyzing current codebase...")
            # Check if sync is needed
            if not force and not generator.check_foundation_sync_needed():
                print("✅ Foundation spec is already current")
                return
            print("🔄 Syncing foundation spec with codebase...")
            success = generator.sync_foundation_spec()
            if success:
                print("✅ Foundation spec successfully synced")
                print(
                    f"📄 Updated: {Path(templates_dir) / 'agentic-spec-foundation.yaml'}"
                )
                # Show what was updated
                try:
                    foundation = generator.load_template("agentic-spec-foundation")
                    last_synced = foundation.get("_last_synced", "Unknown")
                    print(f"🕒 Last synced: {last_synced}")
                    deps_count = len(
                        foundation.get("context", {}).get("dependencies", [])
                    )
                    print(f"📦 Dependencies tracked: {deps_count}")
                    print(
                        f"📋 Coding standards: {len(foundation.get('coding_standards', []))}"
                    )
                except (OSError, KeyError, ValueError, TypeError):
                    pass
            else:
                print("❌ Failed to sync foundation spec")
        except SyncFoundationConfigError as e:
            # Handle config-specific errors with more detail
            logger.error("Sync-foundation configuration error: %s", e.message)
            print(f"❌ Configuration Error: {e.message}")
            if e.details:
                print(f"   Details: {e.details}")
            if e.config_path:
                print(f"   Config file: {e.config_path}")
            if e.field:
                print(f"   Field: {e.field}")
            print("\n💡 Tips:")
            print("   • Check config file syntax and structure")
            print("   • Validate required fields are present")
            print("   • Run 'agentic-spec config validate' to check your config")
            raise typer.Exit(1) from None
        except AgenticSpecError as e:
            logger.exception("Application error during sync")
            print(f"❌ {e.message}")
            if e.details:
                print(f"   {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:
            logger.exception("Unexpected error syncing foundation spec")
            print(f"❌ Unexpected error: {e}")
            print(
                "💡 This may be a bug. Please report it with logs from the current session."
            )
            raise typer.Exit(1) from None

    asyncio.run(_sync())


@workflow_app.command("check-foundation")
def check_foundation_status(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Check if foundation specification needs to be synced.
    Analyzes the foundation spec and determines if it's out of sync
    with the current codebase state.
    """

    async def _check():
        logger = logging.getLogger("agentic_spec")
        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )
            print("🔍 Checking foundation spec status...")
            try:
                foundation = generator.load_template("agentic-spec-foundation")
                last_synced = foundation.get("_last_synced")
                sync_version = foundation.get("_sync_version", "unknown")
                print("📄 Foundation Spec Status:")
                print("  Exists: ✅")
                print(f"  Last synced: {last_synced or 'Never'}")
                print(f"  Sync version: {sync_version}")
                needs_sync = generator.check_foundation_sync_needed()
                if needs_sync:
                    print("  Status: ⚠️  Needs sync")
                    print("\n💡 Run 'agentic-spec sync-foundation' to update")
                else:
                    print("  Status: ✅ Current")
            except (OSError, UnicodeDecodeError, KeyError, ValueError):
                print("📄 Foundation Spec Status:")
                print("  Exists: ❌ Not found")
                print("  Status: ⚠️  Needs creation")
                print("\n💡 Run 'agentic-spec sync-foundation' to create")
        except Exception as e:
            logger.exception("Error checking foundation status")
            msg = "Failed to check foundation status"
            raise SpecificationError(msg, str(e)) from e

    asyncio.run(_check())
