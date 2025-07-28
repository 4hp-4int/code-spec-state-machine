#!/usr/bin/env python3
"""Model audit script for data modeling consistency checks.

This script analyzes agentic_spec/models.py to identify inconsistent data modeling
approaches and provides recommendations for standardization.
"""

import ast
import json
from pathlib import Path
import sys
from typing import Any


def analyze_models_file(file_path: Path) -> dict[str, Any]:
    """Parse models.py and categorize all class definitions."""

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)

    classes = {
        "dataclass_models": [],
        "pydantic_models": [],
        "enum_models": [],
        "other_models": [],
    }

    # Find decorators and base classes
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "decorators": [
                    d.id if isinstance(d, ast.Name) else str(d)
                    for d in node.decorator_list
                ],
                "bases": [
                    b.id if isinstance(b, ast.Name) else str(b) for b in node.bases
                ],
            }

            # Categorize based on decorators and base classes
            if "dataclass" in class_info["decorators"]:
                classes["dataclass_models"].append(class_info)
            elif any("BaseModel" in base for base in class_info["bases"]):
                classes["pydantic_models"].append(class_info)
            elif any("Enum" in base for base in class_info["bases"]):
                classes["enum_models"].append(class_info)
            else:
                classes["other_models"].append(class_info)

    return classes


def generate_report(classes: dict[str, Any]) -> str:
    """Generate a formatted audit report."""

    total = sum(len(classes[key]) for key in classes)
    dataclass_count = len(classes["dataclass_models"])
    pydantic_count = len(classes["pydantic_models"])

    report = f"""# Model Audit Report - Generated Automatically

## Summary
- **Total Classes:** {total}
- **Dataclass Models:** {dataclass_count} (need conversion)
- **Pydantic Models:** {pydantic_count} (compliant)
- **Enum Models:** {len(classes['enum_models'])} (no change needed)
- **Other Models:** {len(classes['other_models'])}

## Consistency Status
"""

    if dataclass_count > 0:
        report += f"❌ **INCONSISTENT** - {dataclass_count} dataclass models need conversion to Pydantic\n\n"

        report += "### Dataclass Models (Require Conversion)\n"
        for model in classes["dataclass_models"]:
            report += f"- **{model['name']}** (line {model['line']})\n"
        report += "\n"
    else:
        report += "✅ **CONSISTENT** - All models use Pydantic BaseModel\n\n"

    report += "### Pydantic Models (Compliant)\n"
    for model in classes["pydantic_models"]:
        report += f"- **{model['name']}** (line {model['line']})\n"

    return report


def main():
    """Main audit function."""
    models_file = Path(__file__).parent.parent / "agentic_spec" / "models.py"

    if not models_file.exists():
        print(f"❌ Models file not found: {models_file}")
        sys.exit(1)

    try:
        classes = analyze_models_file(models_file)
        report = generate_report(classes)

        # Save report
        report_file = Path(__file__).parent.parent / "model_audit_report_auto.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        # Save JSON data
        json_file = Path(__file__).parent.parent / "model_audit_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(classes, f, indent=2)

        print("✅ Model audit completed successfully!")
        print(f"📄 Report saved to: {report_file}")
        print(f"📊 Data saved to: {json_file}")

        # Exit with error code if inconsistencies found
        dataclass_count = len(classes["dataclass_models"])
        if dataclass_count > 0:
            print(f"⚠️  Found {dataclass_count} dataclass models that need conversion")
            sys.exit(1)
        else:
            print("✅ All models are consistent!")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
