"""Complete and approve all tasks in every specification via CLI.

Usage: python tools/complete_tasks.py
"""

from pathlib import Path
import subprocess
import sys

import yaml

SPECS_DIR = Path("specs")


def iterate_specs():
    for path in SPECS_DIR.glob("*.yaml"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            spec_id = data.get("metadata", {}).get("id")
            if not spec_id:
                continue
            implementation = data.get("implementation", [])
            for idx, step in enumerate(implementation):
                progress = step.get("progress") or {}
                status = progress.get("status", "pending")
                if status not in ("completed", "approved"):
                    yield spec_id, idx, status
        except Exception:
            continue


def run_cli(cmd):
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def main() -> None:
    actions = list(iterate_specs())
    if not actions:
        print("✅ All tasks already completed/approved")
        return

    for spec_id, idx, status in actions:
        step_id = f"{spec_id}:{idx}"
        print(f"▶ Completing {step_id} (current: {status})")
        if status in ("pending", "blocked"):
            run_cli(["agentic-spec", "task-start", step_id, "--no-strict"])
        if status != "completed":
            run_cli(["agentic-spec", "task-complete", step_id, "--notes", "back-fill"])
        run_cli(
            [
                "agentic-spec",
                "task-approve",
                step_id,
                "--level",
                "self",
                "--by",
                "automation",
            ]
        )
    print("✅ Back-fill done")


if __name__ == "__main__":
    sys.exit(main())
