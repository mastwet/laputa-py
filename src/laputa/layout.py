"""Storage layout for Laputa governance layer.

Translated from agent-diva-laputa/src/layout.rs
"""

from __future__ import annotations

from pathlib import Path

from .types import LaputaSectionName


class LaputaPaths:
    """Manages paths for the .laputa/ directory structure."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.laputa_dir = self.workspace_root / ".laputa"

    @property
    def state_file(self) -> Path:
        return self.laputa_dir / "state.json"

    @property
    def proposals_dir(self) -> Path:
        return self.laputa_dir / "proposals"

    @property
    def changelog_dir(self) -> Path:
        return self.laputa_dir / "changelog"

    @property
    def audit_dir(self) -> Path:
        return self.laputa_dir / "audit"

    @property
    def rollback_dir(self) -> Path:
        return self.laputa_dir / "rollback"

    @property
    def migrations_dir(self) -> Path:
        return self.laputa_dir / "migrations"

    @property
    def locks_dir(self) -> Path:
        return self.laputa_dir / "locks"

    @property
    def legacy_dir(self) -> Path:
        return self.laputa_dir / "legacy"

    @property
    def staging_dir(self) -> Path:
        return self.laputa_dir / "staging"

    @property
    def sections_dir(self) -> Path:
        return self.laputa_dir / "sections"

    def section_file(self, section: LaputaSectionName) -> Path:
        """Get the file path for a specific section."""
        return self.sections_dir / f"{section.value}.json"

    def proposal_file(self, proposal_id: str) -> Path:
        """Get the file path for a specific proposal."""
        return self.proposals_dir / f"{proposal_id}.json"

    def changelog_file(self, changelog_id: str) -> Path:
        """Get the file path for a specific changelog record."""
        return self.changelog_dir / f"{changelog_id}.json"

    def audit_file(self, audit_id: str) -> Path:
        """Get the file path for a specific audit event."""
        return self.audit_dir / f"{audit_id}.json"

    def rollback_file(self, changelog_id: str) -> Path:
        """Get the file path for a specific rollback request."""
        return self.rollback_dir / f"{changelog_id}.json"


class LaputaStorage:
    """Manages the .laputa/ storage directory."""

    def __init__(self, workspace_root: Path):
        self.paths = LaputaPaths(workspace_root)

    @classmethod
    def open(cls, workspace_root: Path) -> LaputaStorage:
        """Open or create the .laputa/ storage directory."""
        storage = cls(workspace_root)
        storage._ensure_directories()
        storage._ensure_state_file()
        return storage

    def _ensure_directories(self) -> None:
        """Create all required subdirectories."""
        dirs = [
            self.paths.laputa_dir,
            self.paths.proposals_dir,
            self.paths.changelog_dir,
            self.paths.audit_dir,
            self.paths.rollback_dir,
            self.paths.migrations_dir,
            self.paths.locks_dir,
            self.paths.legacy_dir,
            self.paths.staging_dir,
            self.paths.sections_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _ensure_state_file(self) -> None:
        """Create initial state.json if it doesn't exist."""
        if not self.paths.state_file.exists():
            from .atomic import atomic_write_json

            atomic_write_json(
                self.paths.state_file,
                {"schema_version": "1.0.0", "created_at": "now"},
            )
