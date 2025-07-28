#!/usr/bin/env python3
"""
Test script to demonstrate dynamic task injection with YAML persistence.

This script showcases the implementation details of:
1. Atomic YAML file writes
2. Task injection with metadata tracking
3. Schema compatibility and validation
4. Injection history tracking
"""

from pathlib import Path

from agentic_spec.core import SpecGenerator


def test_dynamic_task_injection():
    """Test the dynamic task injection functionality."""
    print("🧪 Testing Dynamic Task Injection with YAML Persistence")
    print("=" * 60)

    # Initialize the generator
    generator = SpecGenerator(
        spec_templates_dir=Path("templates"), specs_dir=Path("specs")
    )

    # Load an existing spec to inject tasks into
    test_spec_id = "e42b7b72"  # Git-aware workflow spec

    print(f"📋 Loading specification: {test_spec_id}")
    original_spec = generator.find_spec_by_id(test_spec_id)
    if not original_spec:
        print(f"❌ Specification {test_spec_id} not found")
        return

    original_task_count = len(original_spec.implementation)
    print(f"📊 Original task count: {original_task_count}")

    # Test 1: Single task injection
    print("\n🔬 Test 1: Single Task Injection")
    print("-" * 40)

    new_task = {
        "task": "Add comprehensive logging for git operations",
        "details": "Implement structured logging for all git utility operations to aid in debugging and monitoring. Include success/failure states, operation timing, and error details.",
        "files": ["agentic_spec/core.py", "agentic_spec/logging_config.py"],
        "acceptance": "All git operations are logged with appropriate detail levels",
        "estimated_effort": "low",
    }

    success, message = generator.inject_task_into_spec(
        spec_id=test_spec_id,
        new_task=new_task,
        parent_task_index=0,  # Insert after first task
        injection_metadata={
            "reason": "scope_gap_detected",
            "trigger": "git_operation_debugging_needed",
            "source": "ai_analysis",
        },
    )

    print(
        f"✅ Injection result: {message}"
        if success
        else f"❌ Injection failed: {message}"
    )

    # Verify injection by reloading spec
    updated_spec = generator.find_spec_by_id(test_spec_id)
    if updated_spec:
        new_task_count = len(updated_spec.implementation)
        print(f"📊 Updated task count: {new_task_count}")
        print(f"📈 Tasks added: {new_task_count - original_task_count}")

        # Find and display the injected task
        for i, task in enumerate(updated_spec.implementation):
            if getattr(task, "injected", False):
                print(f"🎯 Found injected task at index {i}:")
                print(f"   📋 Task: {task.task}")
                print(f"   🏷️  Step ID: {task.step_id}")
                print(
                    f"   📅 Injected: {task.injection_metadata.get('injected_at', 'Unknown')}"
                )
                print(
                    f"   🤖 Injected by: {task.injection_metadata.get('injected_by', 'Unknown')}"
                )
                print(
                    f"   📝 Reason: {task.injection_metadata.get('reason', 'Unknown')}"
                )
                break

    # Test 2: Batch task injection
    print("\n🔬 Test 2: Batch Task Injection")
    print("-" * 40)

    batch_tasks = [
        {
            "task": "Add git operation performance metrics",
            "details": "Implement timing and performance metrics for git operations to identify bottlenecks",
            "files": ["agentic_spec/core.py"],
            "acceptance": "Git operations report timing metrics",
            "estimated_effort": "low",
        },
        {
            "task": "Add git repository health checks",
            "details": "Implement health checks for git repository state and integrity",
            "files": ["agentic_spec/core.py", "agentic_spec/health_checks.py"],
            "acceptance": "Repository health can be validated before operations",
            "estimated_effort": "medium",
        },
    ]

    success, messages = generator.batch_inject_tasks(
        spec_id=test_spec_id,
        tasks_to_inject=batch_tasks,
        injection_metadata={
            "reason": "performance_enhancement",
            "trigger": "operational_requirements_analysis",
            "source": "system_optimization",
        },
    )

    if success:
        print("✅ Batch injection successful:")
        for msg in messages:
            print(f"   📝 {msg}")
    else:
        print("❌ Batch injection failed:")
        for msg in messages:
            print(f"   ❌ {msg}")

    # Test 3: Verify atomic writes and injection history
    print("\n🔬 Test 3: Atomic Writes & Injection History")
    print("-" * 40)

    final_spec = generator.find_spec_by_id(test_spec_id)
    if final_spec:
        final_task_count = len(final_spec.implementation)
        total_injected = final_task_count - original_task_count
        print(f"📊 Final task count: {final_task_count}")
        print(f"📈 Total tasks injected: {total_injected}")

        # Display injection history
        if (
            hasattr(final_spec.metadata, "injection_history")
            and final_spec.metadata.injection_history
        ):
            print("\n📚 Injection History:")
            for i, injection in enumerate(final_spec.metadata.injection_history):
                print(f"   🕐 Injection {i+1}:")
                print(f"      📅 When: {injection.get('injected_at', 'Unknown')}")
                print(
                    f"      📝 Reason: {injection.get('injection_reason', 'Unknown')}"
                )
                if injection.get("batch_injection"):
                    print(f"      📦 Batch: {injection.get('task_count', 0)} tasks")
                else:
                    print(f"      🎯 Task: {injection.get('task_id', 'Unknown')}")

        # Count injected vs original tasks
        injected_count = sum(
            1 for task in final_spec.implementation if getattr(task, "injected", False)
        )
        original_count = final_task_count - injected_count

        print("\n📊 Task Breakdown:")
        print(f"   📋 Original tasks: {original_count}")
        print(f"   🤖 Injected tasks: {injected_count}")
        print(f"   📈 Total tasks: {final_task_count}")

    # Test 4: Verify YAML file integrity
    print("\n🔬 Test 4: YAML File Integrity")
    print("-" * 40)

    spec_file = Path(f"specs/2025-07-28-{test_spec_id}.yaml")
    if spec_file.exists():
        print(f"📁 YAML file exists: {spec_file}")
        print(f"📏 File size: {spec_file.stat().st_size} bytes")

        # Try loading the file directly to verify YAML integrity
        try:
            reloaded_spec = generator.load_spec(spec_file)
            print("✅ YAML file loads successfully")
            print(f"📊 Loaded {len(reloaded_spec.implementation)} tasks")

            # Check for injection metadata preservation
            injected_tasks_in_yaml = [
                task
                for task in reloaded_spec.implementation
                if getattr(task, "injected", False)
            ]
            print(f"🤖 Injected tasks preserved in YAML: {len(injected_tasks_in_yaml)}")

        except Exception as e:
            print(f"❌ YAML file corrupted: {e}")
    else:
        print(f"❌ YAML file not found: {spec_file}")

    print("\n🎉 Dynamic Task Injection Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_dynamic_task_injection()
