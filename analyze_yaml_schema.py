#!/usr/bin/env python3
"""
YAML Schema Analysis Tool

Analyzes all YAML specification files to understand the actual schema
structure and validate our mapping assumptions.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import yaml


def analyze_yaml_structure(file_path: Path) -> dict[str, Any]:
    """Analyze a single YAML file and return its structure."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return {
            "file": str(file_path),
            "valid": True,
            "structure": extract_structure(data),
            "data": data,
        }
    except Exception as e:
        return {
            "file": str(file_path),
            "valid": False,
            "error": str(e),
            "structure": {},
            "data": None,
        }


def extract_structure(obj: Any, path: str = "") -> dict[str, Any]:
    """Recursively extract the structure of a Python object."""
    if obj is None:
        return {"type": "null", "path": path}
    if isinstance(obj, bool):
        return {"type": "bool", "path": path, "value": obj}
    if isinstance(obj, int):
        return {"type": "int", "path": path, "value": obj}
    if isinstance(obj, float):
        return {"type": "float", "path": path, "value": obj}
    if isinstance(obj, str):
        return {"type": "str", "path": path, "length": len(obj)}
    if isinstance(obj, list):
        item_types = set()
        structures = []
        for i, item in enumerate(obj):
            item_structure = extract_structure(item, f"{path}[{i}]")
            item_types.add(item_structure.get("type", "unknown"))
            if i < 3:  # Only keep first 3 items to avoid huge outputs
                structures.append(item_structure)

        return {
            "type": "list",
            "path": path,
            "length": len(obj),
            "item_types": list(item_types),
            "sample_items": structures,
        }
    if isinstance(obj, dict):
        fields = {}
        for key, value in obj.items():
            fields[key] = extract_structure(value, f"{path}.{key}")

        return {"type": "dict", "path": path, "fields": fields}
    return {"type": type(obj).__name__, "path": path}


def analyze_field_usage(all_structures: list) -> dict[str, Any]:
    """Analyze field usage across all files."""
    field_stats = defaultdict(
        lambda: {"count": 0, "types": Counter(), "paths": set(), "examples": []}
    )

    def collect_fields(structure: dict[str, Any], parent_path: str = ""):
        if structure.get("type") == "dict":
            for field_name, field_info in structure.get("fields", {}).items():
                full_path = f"{parent_path}.{field_name}" if parent_path else field_name
                field_stats[full_path]["count"] += 1
                field_stats[full_path]["types"][field_info.get("type", "unknown")] += 1
                field_stats[full_path]["paths"].add(full_path)

                if len(field_stats[full_path]["examples"]) < 3:
                    if "value" in field_info:
                        field_stats[full_path]["examples"].append(field_info["value"])
                    elif field_info.get("type") == "list":
                        field_stats[full_path]["examples"].append(
                            f"list[{field_info.get('length', 0)}]"
                        )

                # Recurse into nested structures
                collect_fields(field_info, full_path)
        elif structure.get("type") == "list":
            for item in structure.get("sample_items", []):
                collect_fields(item, f"{parent_path}[]")

    for file_analysis in all_structures:
        if file_analysis["valid"]:
            collect_fields(file_analysis["structure"])

    # Convert sets to lists for JSON serialization
    for field_info in field_stats.values():
        field_info["paths"] = list(field_info["paths"])
        field_info["types"] = dict(field_info["types"])

    return dict(field_stats)


def main():
    """Main analysis function."""
    specs_dir = Path("specs")

    if not specs_dir.exists():
        print(f"Error: {specs_dir} directory not found")
        return

    yaml_files = list(specs_dir.glob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML files")

    all_analyses = []
    valid_count = 0

    for file_path in yaml_files:
        analysis = analyze_yaml_structure(file_path)
        all_analyses.append(analysis)
        if analysis["valid"]:
            valid_count += 1
        else:
            print(f"Error in {file_path}: {analysis['error']}")

    print(f"Successfully analyzed {valid_count}/{len(yaml_files)} files")

    # Analyze field usage
    field_usage = analyze_field_usage(all_analyses)

    # Generate summary report
    report = {
        "summary": {
            "total_files": len(yaml_files),
            "valid_files": valid_count,
            "invalid_files": len(yaml_files) - valid_count,
            "unique_fields": len(field_usage),
        },
        "field_usage": field_usage,
        "common_patterns": {},
        "schema_variations": [],
    }

    # Identify common patterns
    required_fields = {
        field: stats
        for field, stats in field_usage.items()
        if stats["count"] >= valid_count * 0.8
    }  # Present in 80%+ of files

    optional_fields = {
        field: stats
        for field, stats in field_usage.items()
        if stats["count"] < valid_count * 0.8
    }

    report["common_patterns"] = {
        "required_fields": list(required_fields.keys()),
        "optional_fields": list(optional_fields.keys()),
        "field_type_consistency": {},
    }

    # Check type consistency
    for field, stats in field_usage.items():
        if len(stats["types"]) == 1:
            report["common_patterns"]["field_type_consistency"][field] = list(
                stats["types"].keys()
            )[0]
        else:
            report["common_patterns"]["field_type_consistency"][field] = (
                f"MIXED: {dict(stats['types'])}"
            )

    # Save detailed report
    with open("specs/yaml-schema-analysis.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    print("\n=== YAML Schema Analysis Summary ===")
    print("Required fields (in 80%+ files):")
    for field in sorted(required_fields.keys()):
        field_type = report["common_patterns"]["field_type_consistency"].get(
            field, "unknown"
        )
        print(f"  {field}: {field_type}")

    print("\nOptional fields:")
    for field in sorted(optional_fields.keys()):
        field_type = report["common_patterns"]["field_type_consistency"].get(
            field, "unknown"
        )
        count = optional_fields[field]["count"]
        print(f"  {field}: {field_type} (in {count}/{valid_count} files)")

    print("\nType inconsistencies:")
    for field, type_info in report["common_patterns"]["field_type_consistency"].items():
        if type_info.startswith("MIXED:"):
            print(f"  {field}: {type_info}")

    print("\nDetailed analysis saved to: specs/yaml-schema-analysis.json")


if __name__ == "__main__":
    main()
