"""Laputa service layer - facade for governance operations.

Translated from agent-diva-laputa/src/service.rs
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .atomic import atomic_write, atomic_write_json
from .error import DirectWriteNotAllowed, RollbackExpired, Unauthorized
from .layout import LaputaStorage
from .lock import LaputaLock
from .metrics import LaputaMetrics
from .proposals import ProposalFilter, ProposalRepository
from .types import (
    AuditEvent,
    AuditEventKind,
    ChangelogAction,
    ChangelogRecord,
    EvolutionProposal,
    LaputaSectionName,
    ProposalState,
    RollbackRequest,
)


class LaputaSection:
    """A single Laputa section with its content."""

    def __init__(
        self,
        name: LaputaSectionName,
        content: str,
        last_modified: Optional[datetime] = None,
    ):
        self.name = name
        self.content = content
        self.last_modified = last_modified


class LaputaSnapshot:
    """Complete snapshot of all Laputa sections."""

    def __init__(
        self,
        schema_version: str,
        sections: dict[str, LaputaSection],
        changed_sections: list[str],
        updated_at: Optional[datetime],
        server_time: datetime,
    ):
        self.schema_version = schema_version
        self.sections = sections
        self.changed_sections = changed_sections
        self.updated_at = updated_at
        self.server_time = server_time


class ChangelogFilter:
    """Filters for changelog list queries."""

    def __init__(
        self,
        target_section: Optional[LaputaSectionName] = None,
        action: Optional[ChangelogAction] = None,
        proposal_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        self.target_section = target_section
        self.action = action
        self.proposal_id = proposal_id
        self.since = since
        self.until = until
        self.page = max(1, page)
        self.page_size = max(1, min(100, page_size))

    def matches(self, record: ChangelogRecord) -> bool:
        if self.target_section and record.target_section != self.target_section:
            return False
        if self.action and record.action != self.action:
            return False
        if self.proposal_id and record.proposal_id != self.proposal_id:
            return False
        if self.since and record.created_at < self.since:
            return False
        if self.until and record.created_at > self.until:
            return False
        return True


class LaputaService:
    """Stable Laputa service API for governance operations."""

    def __init__(self, storage: LaputaStorage):
        self._storage = storage
        self._metrics = LaputaMetrics()
        self._proposals = ProposalRepository(storage, self._metrics)

    @classmethod
    def open(cls, workspace_root: Path) -> LaputaService:
        """Open or create a Laputa service instance."""
        storage = LaputaStorage.open(workspace_root)
        return cls(storage)

    @property
    def storage(self) -> LaputaStorage:
        return self._storage

    @property
    def metrics(self) -> LaputaMetrics:
        return self._metrics

    # -- Proposal operations --------------------------------------------------

    def create_proposal(self, proposal: EvolutionProposal) -> EvolutionProposal:
        return self._proposals.create_proposal(proposal)

    def get_proposal(self, proposal_id: str) -> EvolutionProposal:
        return self._proposals.get_proposal(proposal_id)

    def list_proposals(self, filter: Optional[ProposalFilter] = None) -> list[EvolutionProposal]:
        return self._proposals.list_proposals(filter)

    def apply_proposal(
        self,
        proposal_id: str,
        actor: str,
        applied_at: Optional[datetime] = None,
    ) -> tuple[EvolutionProposal, ChangelogRecord, AuditEvent]:
        return self._proposals.apply_proposal(proposal_id, actor, applied_at)

    def transition_proposal(
        self,
        proposal_id: str,
        to_state: ProposalState,
        updated_at: Optional[datetime] = None,
    ) -> EvolutionProposal:
        return self._proposals.transition_proposal(proposal_id, to_state, updated_at)

    # -- Section operations ---------------------------------------------------

    def read_section(self, name: LaputaSectionName) -> LaputaSection:
        """Read a single section."""
        path = self._storage.paths.section_file(name)
        content = ""
        last_modified = None

        if path.exists():
            content = path.read_text(encoding="utf-8")
            last_modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

        return LaputaSection(name=name, content=content, last_modified=last_modified)

    def write_section(
        self,
        name: LaputaSectionName,
        content: str,
        actor: str,
        reason: Optional[str] = None,
        applied_at: Optional[datetime] = None,
    ) -> tuple[ChangelogRecord, AuditEvent]:
        """Write content to a section directly (for user intervention).

        Only commitment and preferences sections can be written directly.
        Other sections must use the proposal flow.

        Args:
            name: Section to write
            content: New content
            actor: Who is writing
            reason: Why the change is being made
            applied_at: When the change is applied (defaults to now)

        Returns:
            Tuple of (ChangelogRecord, AuditEvent)

        Raises:
            DirectWriteNotAllowed: If section cannot be written directly
        """
        if name not in (LaputaSectionName.COMMITMENT, LaputaSectionName.PREFERENCES):
            raise DirectWriteNotAllowed(name.value)

        applied_at = applied_at or datetime.now(timezone.utc)
        reason = reason or "direct write by user"

        section = self.read_section(name)
        before = section.content

        path = self._storage.paths.section_file(name)
        atomic_write(path, content.encode("utf-8"))

        changelog_id = f"changelog-direct-{name.value}-{uuid.uuid4().hex[:8]}"
        changelog = ChangelogRecord(
            id=changelog_id,
            action=ChangelogAction.APPLY,
            target_section=name,
            before=before,
            after=content,
            diff=f"direct write: {reason}",
            proposal_id=None,
            audit_event_id=None,
            reverted=False,
            stale=False,
            created_at=applied_at,
            applied_by=actor,
        )
        atomic_write_json(
            self._storage.paths.changelog_file(changelog_id),
            asdict(changelog),
        )

        audit_id = f"audit-direct-{name.value}-{int(applied_at.timestamp())}"
        audit_event = AuditEvent(
            id=audit_id,
            kind=AuditEventKind.PROPOSAL_APPLIED,
            actor=actor,
            target_section=name,
            message=f"direct write to {name.value}: {reason}",
            created_at=applied_at,
        )
        atomic_write_json(
            self._storage.paths.audit_file(audit_id),
            asdict(audit_event),
        )

        self._metrics.record_write()
        return changelog, audit_event

    def read_snapshot(self, since: Optional[datetime] = None) -> LaputaSnapshot:
        """Read all 11 sections as a snapshot (Python版，报告系统走mempalace wings)."""
        sections = {}
        changed_sections = []
        updated_at = None

        for name in LaputaSectionName.all_v1():
            section = self.read_section(name)
            sections[name.value] = section

            if section.last_modified:
                if updated_at is None or section.last_modified > updated_at:
                    updated_at = section.last_modified
                if since is None or section.last_modified >= since:
                    changed_sections.append(name.value)
            elif since is None:
                changed_sections.append(name.value)

        return LaputaSnapshot(
            schema_version="1.0.0",
            sections=sections,
            changed_sections=changed_sections,
            updated_at=updated_at,
            server_time=datetime.now(timezone.utc),
        )

    # -- Changelog operations -------------------------------------------------

    def get_changelog(self, changelog_id: str) -> ChangelogRecord:
        """Get a single changelog record by ID.

        Args:
            changelog_id: The changelog record ID

        Returns:
            The ChangelogRecord

        Raises:
            ValueError: If changelog not found
        """
        changelog_path = self._storage.paths.changelog_file(changelog_id)
        if not changelog_path.exists():
            raise ValueError(f"changelog not found: {changelog_id}")

        data = json.loads(changelog_path.read_text(encoding="utf-8"))
        return self._changelog_from_dict(data)

    def list_changelog(self, filter: Optional[ChangelogFilter] = None) -> list[ChangelogRecord]:
        """List changelog records with optional filtering."""
        records = []
        changelog_dir = self._storage.paths.changelog_dir

        if not changelog_dir.exists():
            return records

        for path in changelog_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                record = self._changelog_from_dict(data)
                if filter is None or filter.matches(record):
                    records.append(record)
            except Exception:
                continue

        records.sort(key=lambda r: r.created_at, reverse=True)

        if filter:
            start = (filter.page - 1) * filter.page_size
            records = records[start : start + filter.page_size]

        return records

    def rollback_changelog(
        self,
        changelog_id: str,
        requested_by: str,
        reason: str,
        requested_at: Optional[datetime] = None,
    ) -> tuple[ChangelogRecord, AuditEvent]:
        """Rollback a changelog entry within the 30-day window."""
        requested_at = requested_at or datetime.now(timezone.utc)

        changelog_path = self._storage.paths.changelog_file(changelog_id)
        if not changelog_path.exists():
            raise ValueError(f"changelog not found: {changelog_id}")

        data = json.loads(changelog_path.read_text(encoding="utf-8"))
        changelog = self._changelog_from_dict(data)

        age = requested_at - changelog.created_at
        if age > timedelta(days=30):
            raise RollbackExpired(changelog_id, changelog.created_at.isoformat())

        section_path = self._storage.paths.section_file(changelog.target_section)
        if changelog.before:
            atomic_write_json(section_path, changelog.before)

        changelog.reverted = True
        atomic_write_json(changelog_path, asdict(changelog))

        audit_id = f"audit-rollback-{changelog_id}-{int(requested_at.timestamp())}"
        audit_event = AuditEvent(
            id=audit_id,
            kind=AuditEventKind.ROLLBACK_APPLIED,
            actor=requested_by,
            target_section=changelog.target_section,
            message=f"rollback changelog {changelog_id}: {reason}",
            created_at=requested_at,
        )
        atomic_write_json(
            self._storage.paths.audit_file(audit_id),
            asdict(audit_event),
        )

        self._metrics.record_rollback()
        return changelog, audit_event

    # -- Helpers --------------------------------------------------------------

    def _changelog_from_dict(self, data: dict) -> ChangelogRecord:
        """Convert dict to ChangelogRecord."""
        return ChangelogRecord(
            id=data["id"],
            action=ChangelogAction(data["action"]),
            target_section=LaputaSectionName(data["target_section"]),
            before=data.get("before", ""),
            after=data.get("after", ""),
            diff=data.get("diff", ""),
            proposal_id=data.get("proposal_id"),
            audit_event_id=data.get("audit_event_id"),
            reverted=data.get("reverted", False),
            stale=data.get("stale", False),
            created_at=datetime.fromisoformat(data["created_at"]),
            applied_by=data["applied_by"],
        )
