"""CLI entry point for laputa-py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .service import LaputaService


def main(args: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="laputa-py",
        description="Laputa governance layer CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize Laputa in workspace")
    init_parser.add_argument("workspace", type=Path, help="Workspace path")

    # status command
    status_parser = subparsers.add_parser("status", help="Show Laputa status")
    status_parser.add_argument("workspace", type=Path, help="Workspace path")

    # section command
    section_parser = subparsers.add_parser("section", help="Read a section")
    section_parser.add_argument("workspace", type=Path, help="Workspace path")
    section_parser.add_argument("name", help="Section name")

    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 1

    try:
        if parsed.command == "init":
            return cmd_init(parsed.workspace)
        elif parsed.command == "status":
            return cmd_status(parsed.workspace)
        elif parsed.command == "section":
            return cmd_section(parsed.workspace, parsed.name)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_init(workspace: Path) -> int:
    """Initialize Laputa in workspace."""
    service = LaputaService.open(workspace)
    print(f"Laputa initialized in {workspace}")
    print(f"  .laputa/ directory created with {len(service.storage.paths.__dict__)} subdirectories")
    return 0


def cmd_status(workspace: Path) -> int:
    """Show Laputa status."""
    service = LaputaService.open(workspace)
    snapshot = service.read_snapshot()
    metrics = service.metrics.snapshot()

    print("Laputa Status")
    print("=" * 40)
    print(f"Schema version: {snapshot.schema_version}")
    print(f"Sections: {len(snapshot.sections)}")
    print(f"Changed sections: {len(snapshot.changed_sections)}")
    print()
    print("Metrics:")
    print(f"  Writes: {metrics.writes}")
    print(f"  Write errors: {metrics.write_errors}")
    print(f"  Rollbacks: {metrics.rollbacks}")

    return 0


def cmd_section(workspace: Path, name: str) -> int:
    """Read a section."""
    from .types import LaputaSectionName

    service = LaputaService.open(workspace)

    try:
        section_name = LaputaSectionName(name)
    except ValueError:
        print(f"Unknown section: {name}", file=sys.stderr)
        print(f"Valid sections: {[s.value for s in LaputaSectionName.all_v1()]}")
        return 1

    section = service.read_section(section_name)
    print(f"Section: {section.name.value}")
    if section.last_modified:
        print(f"Last modified: {section.last_modified.isoformat()}")
    print()
    print(section.content or "(empty)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
