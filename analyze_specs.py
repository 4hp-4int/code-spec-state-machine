#!/usr/bin/env python3
"""Analyze specifications to categorize them for cleanup."""

from pathlib import Path
from typing import Any

import yaml


def analyze_spec(spec_path: Path) -> dict[str, Any]:
    """Analyze a single specification file."""
    try:
        with spec_path.open(encoding="utf-8") as f:
            spec = yaml.safe_load(f)

        metadata = spec.get("metadata", {})
        context = spec.get("context", {})
        requirements = spec.get("requirements", {})

        return {
            "id": metadata.get("id", "unknown"),
            "status": metadata.get("status", "unknown"),
            "created": metadata.get("created", "unknown"),
            "project": context.get("project", "unknown"),
            "domain": context.get("domain", "unknown"),
            "functional_reqs": len(requirements.get("functional", [])),
            "impl_steps": len(spec.get("implementation", [])),
            "child_specs": metadata.get("child_spec_ids", []) or [],
            "parent_spec": metadata.get("parent_spec_id"),
            "has_review": bool(spec.get("review_notes", [])),
        }
    except (yaml.YAMLError, OSError) as e:
        return {"id": spec_path.stem, "error": str(e), "status": "error"}


def categorize_specs():
    """Categorize all specifications."""
    specs_dir = Path("specs")

    if not specs_dir.exists():
        print("No specs directory found")
        return None

    specs = []
    for spec_file in specs_dir.glob("*.yaml"):
        analysis = analyze_spec(spec_file)
        analysis["filename"] = spec_file.name
        specs.append(analysis)

    # Sort by creation date
    specs.sort(key=lambda x: x.get("created", ""))

    print(f"Found {len(specs)} specifications\n")

    # Categorize
    completed_work = []
    test_specs = []
    cache_related = []
    unused_specs = []

    for spec in specs:
        if "error" in spec:
            print(f"ERROR: {spec['filename']} - {spec['error']}")
            continue

        # Check for test/temporary specs
        project = spec["project"].lower()
        domain = spec["domain"].lower()

        if (
            project in ["project", "general"]
            and spec["functional_reqs"] <= 1
            and spec["impl_steps"] <= 1
        ):
            test_specs.append(spec)
        elif "cache" in domain or "semantic" in domain:
            cache_related.append(spec)
        elif (
            spec["functional_reqs"] > 1
            and spec["impl_steps"] > 2
            and spec["has_review"]
            and project == "agentic-spec"
        ):
            completed_work.append(spec)
        else:
            unused_specs.append(spec)

    print("=== COMPLETED WORK (Keep & Publish) ===")
    for spec in completed_work:
        print(f"  {spec['filename']} - {spec['id']} - {spec['domain']}")

    print("\n=== CACHE-RELATED (Remove - already implemented) ===")
    for spec in cache_related:
        print(f"  {spec['filename']} - {spec['id']} - {spec['domain']}")

    print("\n=== TEST/TEMPORARY SPECS (Remove) ===")
    for spec in test_specs:
        print(
            f"  {spec['filename']} - {spec['id']} - {spec['project']}/{spec['domain']}"
        )

    print("\n=== UNUSED/UNCLEAR SPECS (Review) ===")
    for spec in unused_specs:
        print(
            f"  {spec['filename']} - {spec['id']} - {spec['project']}/{spec['domain']}"
        )

    print("\nSUMMARY:")
    print(f"  Completed work: {len(completed_work)}")
    print(f"  Cache-related: {len(cache_related)}")
    print(f"  Test specs: {len(test_specs)}")
    print(f"  Unused/unclear: {len(unused_specs)}")

    return {
        "completed": completed_work,
        "cache_related": cache_related,
        "test_specs": test_specs,
        "unused": unused_specs,
    }


if __name__ == "__main__":
    categorize_specs()
