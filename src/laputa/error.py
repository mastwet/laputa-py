"""Error types for Laputa governance layer.

Translated from agent-diva-laputa/src/error.rs
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class LaputaError(Exception):
    """Base error for Laputa operations."""

    pass


class SectionNotFound(LaputaError):
    """Requested Laputa section does not exist."""

    def __init__(self, section: str):
        super().__init__(f"section not found: {section}")
        self.section = section


class ProposalNotFound(LaputaError):
    """Requested proposal does not exist."""

    def __init__(self, proposal_id: str):
        super().__init__(f"proposal not found: {proposal_id}")
        self.proposal_id = proposal_id


class InvalidStateTransition(LaputaError):
    """Proposal state transition is not allowed."""

    def __init__(self, from_state: str, to_state: str):
        super().__init__(f"invalid state transition: {from_state} -> {to_state}")
        self.from_state = from_state
        self.to_state = to_state


class LockTimeout(LaputaError):
    """Could not acquire file lock within timeout."""

    def __init__(self, path: Path, timeout: float):
        super().__init__(f"lock timeout after {timeout}s: {path}")
        self.path = path
        self.timeout = timeout


class UnresolvedConflict(LaputaError):
    """Three-way merge conflict could not be resolved automatically."""

    def __init__(self, section: str, message: str):
        super().__init__(f"unresolved conflict in {section}: {message}")
        self.section = section


class RollbackExpired(LaputaError):
    """Rollback window has expired (30 days)."""

    def __init__(self, changelog_id: str, created_at: str):
        super().__init__(f"rollback expired for {changelog_id} (created {created_at})")
        self.changelog_id = changelog_id


class SchemaIncompatible(LaputaError):
    """Schema version mismatch."""

    def __init__(self, expected: str, actual: str):
        super().__init__(f"schema incompatible: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class IoError(LaputaError):
    """File I/O error."""

    def __init__(self, path: Path, message: str, source: Optional[Exception] = None):
        super().__init__(f"I/O error at {path}: {message}")
        self.path = path
        self.source = source


class Unauthorized(LaputaError):
    """Actor is not authorized for this operation."""

    def __init__(self, actor: str, operation: str):
        super().__init__(f"unauthorized: {actor} cannot {operation}")
        self.actor = actor
        self.operation = operation


class DirectWriteNotAllowed(LaputaError):
    """Section cannot be written directly; must use proposal flow."""

    def __init__(self, section: str):
        super().__init__(f"direct write not allowed for section: {section}; use proposal flow")
        self.section = section
