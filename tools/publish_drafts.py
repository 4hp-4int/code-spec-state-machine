"""Publish all draft specifications in specs/ directory.

Cross-platform replacement for the shell loop in Makefile.
"""

from pathlib import Path
import subprocess
import sys

import yaml

SPECS_DIR = Path("specs")


def is_draft(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("metadata", {}).get("status", "").lower() == "draft"
    except Exception:
        return False


def main() -> None:
    draft_files = [p for p in SPECS_DIR.glob("*.yaml") if is_draft(p)]
    if not draft_files:
        print("✅ No new specifications to publish")
        return

    success = 0
    for path in draft_files:
        # Extract ID (string after the final hyphen).
        spec_id = path.stem.split("-")[-1]
        # Additional safety: ensure metadata.id matches extracted id
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            meta_id = data.get("metadata", {}).get("id")
            if meta_id and meta_id != spec_id:
                spec_id = meta_id
        except Exception:
            pass
        print(f"📋 Publishing draft spec: {spec_id}")
        result = subprocess.run(["agentic-spec", "publish", spec_id], check=False)
        if result.returncode == 0:
            success += 1
        else:
            print(f"❌ Failed to publish {spec_id}")
    print(f"✅ Published {success} draft specifications")


if __name__ == "__main__":
    sys.exit(main())
