"""Proposal repository with state machine and 6-step governance.

Translated from agent-diva-laputa/src/proposals.rs
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .atomic import atomic_write_json
from .error import (
    InvalidStateTransition,
    ProposalNotFound,
    RollbackExpired,
    UnresolvedConflict,
)
from .layout import LaputaStorage
from .lock import LaputaLock
from .metrics import LaputaMetrics
from .types import (
    AuditEvent,
    AuditEventKind,
    ChangelogAction,
    ChangelogRecord,
    EvolutionProposal,
    ProposalState,
    validate_governance_evidence,
)


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------

# Allowed state transitions
_TRANSITIONS: dict[ProposalState, set[ProposalState]] = {
    ProposalState.PENDING_REVIEW: {
        ProposalState.APPROVED,
        ProposalState.REJECTED,
        ProposalState.EDITED,
        ProposalState.DEFERRED,
        ProposalState.NEEDS_ATTENTION,
        ProposalState.SUPERSEDED,
    },
    ProposalState.EDITED: {
        ProposalState.APPROVED,
        ProposalState.REJECTED,
        ProposalState.EDITED,
        ProposalState.DEFERRED,
        ProposalState.NEEDS_ATTENTION,
        ProposalState.SUPERSEDED,
    },
    ProposalState.APPROVED: {
        ProposalState.APPLIED,
        ProposalState.REJECTED,
        ProposalState.NEEDS_ATTENTION,
    },
    ProposalState.APPLIED: {
        ProposalState.REVERTED,
        ProposalState.SUPERSEDED,
    },
    ProposalState.NEEDS_ATTENTION: {
        ProposalState.PENDING_REVIEW,
        ProposalState.REJECTED,
        ProposalState.EDITED,
        ProposalState.DEFERRED,
        ProposalState.SUPERSEDED,
    },
    ProposalState.DEFERRED: {
        ProposalState.PENDING_REVIEW,
        ProposalState.REJECTED,
        ProposalState.EDITED,
        ProposalState.SUPERSEDED,
    },
    # Terminal states - no transitions allowed
    ProposalState.REJECTED: set(),
    ProposalState.REVERTED: set(),
    ProposalState.SUPERSEDED: set(),
    ProposalState.RUN_FAILED: set(),
}


def ensure_transition_allowed(from_state: ProposalState, to_state: ProposalState) -> None:
    """Validate that a state transition is allowed."""
    allowed = _TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise InvalidStateTransition(from_state.value, to_state.value)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class ProposalFilter:
    """Filters for proposal list queries."""

    def __init__(
        self,
        state: Optional[ProposalState] = None,
        proposal_type: Optional[str] = None,
        target_section: Optional[str] = None,
        source_run_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ):
        self.state = state
        self.proposal_type = proposal_type
        self.target_section = target_section
        self.source_run_id = source_run_id
        self.since = since

    def matches(self, proposal: EvolutionProposal) -> bool:
        if self.state and proposal.state != self.state:
            return False
        if self.proposal_type and proposal.proposal_type.value != self.proposal_type:
            return False
        if self.target_section and proposal.target_section.value != self.target_section:
            return False
        if self.source_run_id and proposal.source_run_id != self.source_run_id:
            return False
        if self.since and proposal.created_at < self.since:
            return False
        return True


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def unified_diff(before: str, after: str) -> str:
    """Generate a simple unified diff between before and after content."""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)

    diff_lines = []
    for line in before_lines:
        if line not in after_lines:
            diff_lines.append(f"-{line}")
    for line in after_lines:
        if line not in before_lines:
            diff_lines.append(f"+{line}")

    return "".join(diff_lines)


# ---------------------------------------------------------------------------
# Proposal Repository
# ---------------------------------------------------------------------------


class ProposalRepository:
    """File-first repository for proposal persistence and lifecycle transitions."""

    def __init__(self, storage: LaputaStorage, metrics: Optional[LaputaMetrics] = None):
        self._storage = storage
        self._metrics = metrics or LaputaMetrics()

    def create_proposal(self, proposal: EvolutionProposal) -> EvolutionProposal:
        """Create a new proposal."""
        # Validate evidence
        validate_governance_evidence(proposal.evidence_refs)

        # Write proposal file
        path = self._storage.paths.proposal_file(proposal.id)
        atomic_write_json(path, asdict(proposal))

        # Record audit event
        self._record_audit(
            kind=AuditEventKind.PROPOSAL_CREATED,
            actor=proposal.created_by,
            proposal_id=proposal.id,
            target_section=proposal.target_section,
            message=f"created proposal {proposal.id}",
        )

        return proposal

    def get_proposal(self, proposal_id: str) -> EvolutionProposal:
        """Get a proposal by ID."""
        path = self._storage.paths.proposal_file(proposal_id)
        if not path.exists():
            raise ProposalNotFound(proposal_id)

        data = json.loads(path.read_text(encoding="utf-8"))
        return self._from_dict(data)

    def list_proposals(self, filter: Optional[ProposalFilter] = None) -> list[EvolutionProposal]:
        """List all proposals, optionally filtered."""
        proposals = []
        proposals_dir = self._storage.paths.proposals_dir

        if not proposals_dir.exists():
            return proposals

        for path in proposals_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                proposal = self._from_dict(data)
                if filter is None or filter.matches(proposal):
                    proposals.append(proposal)
            except Exception:
                continue

        # Sort by created_at descending
        proposals.sort(key=lambda p: p.created_at, reverse=True)
        return proposals

    def transition_proposal(
        self,
        proposal_id: str,
        to_state: ProposalState,
        updated_at: Optional[datetime] = None,
    ) -> EvolutionProposal:
        """Transition a proposal to a new state."""
        proposal = self.get_proposal(proposal_id)
        ensure_transition_allowed(proposal.state, to_state)

        proposal.state = to_state
        proposal.updated_at = updated_at or datetime.now(timezone.utc)

        path = self._storage.paths.proposal_file(proposal.id)
        atomic_write_json(path, asdict(proposal))

        return proposal

    def apply_proposal(
        self,
        proposal_id: str,
        actor: str,
        applied_at: Optional[datetime] = None,
    ) -> tuple[EvolutionProposal, ChangelogRecord, AuditEvent]:
        """Apply a proposal using the 6-step governance chain.

        Returns (proposal, changelog, audit_event) on success.
        On failure, rolls back any partial writes.
        """
        applied_at = applied_at or datetime.now(timezone.utc)
        lock_path = self._storage.paths.locks_dir / f"apply-{proposal_id}.lock"

        with LaputaLock(lock_path):
            return self._apply_proposal_internal(proposal_id, actor, applied_at)

    def _apply_proposal_internal(
        self,
        proposal_id: str,
        actor: str,
        applied_at: datetime,
    ) -> tuple[EvolutionProposal, ChangelogRecord, AuditEvent]:
        """Internal implementation of apply_proposal."""
        proposal = self.get_proposal(proposal_id)

        # Step 1: Validate state transition
        ensure_transition_allowed(proposal.state, ProposalState.APPLIED)

        # Step 2: Validate contract
        validate_governance_evidence(proposal.evidence_refs)

        # Prepare IDs
        changelog_id = f"changelog-{proposal.id}-{int(applied_at.timestamp())}"
        audit_id = f"audit-{proposal.id}-{int(applied_at.timestamp())}"

        # Read current section content
        section_path = self._storage.paths.section_file(proposal.target_section)
        before = ""
        if section_path.exists():
            before = section_path.read_text(encoding="utf-8")

        # Step 2.5: Conflict resolution (three-way merge)
        # Check if section has been modified since proposal was created
        if before and proposal.proposed_patch:
            # Simple conflict detection: if content has changed and proposal doesn't match
            # In a real implementation, this would do a three-way merge
            # For now, we'll mark as needs_attention if there's a potential conflict
            if self._has_potential_conflict(proposal, before):
                # Mark proposal as needs_attention
                proposal.state = ProposalState.NEEDS_ATTENTION
                proposal.updated_at = applied_at
                atomic_write_json(
                    self._storage.paths.proposal_file(proposal.id),
                    asdict(proposal),
                )
                
                # Record audit event for conflict
                conflict_audit_id = f"audit-conflict-{proposal.id}-{int(applied_at.timestamp())}"
                conflict_audit = AuditEvent(
                    id=conflict_audit_id,
                    kind=AuditEventKind.NEEDS_ATTENTION,
                    actor=actor,
                    proposal_id=proposal.id,
                    target_section=proposal.target_section,
                    message=f"conflict detected for proposal {proposal.id}",
                    created_at=applied_at,
                )
                atomic_write_json(
                    self._storage.paths.audit_file(conflict_audit_id),
                    asdict(conflict_audit),
                )
                
                self._metrics.record_governance_failure()
                raise UnresolvedConflict(
                    proposal.target_section.value,
                    f"conflict detected for proposal {proposal.id}"
                )

        # Prepare changelog record
        changelog = ChangelogRecord(
            id=changelog_id,
            action=ChangelogAction.APPLY,
            target_section=proposal.target_section,
            before=before,
            after=proposal.proposed_patch,
            diff=unified_diff(before, proposal.proposed_patch),
            proposal_id=proposal.id,
            audit_event_id=audit_id,
            created_at=applied_at,
            applied_by=actor,
        )

        # Prepare audit event
        audit_event = AuditEvent(
            id=audit_id,
            kind=AuditEventKind.PROPOSAL_APPLIED,
            actor=actor,
            proposal_id=proposal.id,
            target_section=proposal.target_section,
            message=f"applied proposal {proposal.id}",
            created_at=applied_at,
        )

        # Step 3-6: Write with rollback on failure
        wrote_section = False
        try:
            # Step 3: Write section (unless deprecation)
            if proposal.proposal_type.value != "deprecation":
                atomic_write_json(section_path, proposal.proposed_patch)
                wrote_section = True

            # Step 4: Write changelog
            atomic_write_json(
                self._storage.paths.changelog_file(changelog_id),
                asdict(changelog),
            )

            # Step 5: Write audit event
            atomic_write_json(
                self._storage.paths.audit_file(audit_id),
                asdict(audit_event),
            )

            # Step 6: Update proposal state
            proposal.state = ProposalState.APPLIED
            proposal.updated_at = applied_at
            atomic_write_json(
                self._storage.paths.proposal_file(proposal.id),
                asdict(proposal),
            )

            self._metrics.record_write()
            return proposal, changelog, audit_event

        except Exception as e:
            # Rollback on failure
            self._metrics.record_write_error()
            self._rollback_apply_failure(
                proposal=proposal,
                section_path=section_path,
                before=before,
                wrote_section=wrote_section,
                changelog_id=changelog_id,
                audit_id=audit_id,
                applied_at=applied_at,
            )
            raise

    def _rollback_apply_failure(
        self,
        proposal: EvolutionProposal,
        section_path: Path,
        before: str,
        wrote_section: bool,
        changelog_id: str,
        audit_id: str,
        applied_at: datetime,
    ) -> None:
        """Rollback partial writes from a failed apply."""
        # Restore section if written
        if wrote_section and before:
            try:
                atomic_write_json(section_path, before)
            except Exception:
                pass

        # Clean up changelog
        try:
            self._storage.paths.changelog_file(changelog_id).unlink(missing_ok=True)
        except Exception:
            pass

        # Clean up audit
        try:
            self._storage.paths.audit_file(audit_id).unlink(missing_ok=True)
        except Exception:
            pass

        # Set proposal to NeedsAttention
        try:
            proposal.state = ProposalState.NEEDS_ATTENTION
            proposal.updated_at = applied_at
            atomic_write_json(
                self._storage.paths.proposal_file(proposal.id),
                asdict(proposal),
            )
        except Exception:
            pass

    def _has_potential_conflict(self, proposal: EvolutionProposal, current_content: str) -> bool:
        """Check if there's a potential conflict between proposal and current content.
        
        This is a simple conflict detection. In a real implementation,
        this would do a three-way merge using the proposal's created_at
        timestamp to find the base version.
        """
        # If current content is empty, no conflict
        if not current_content.strip():
            return False
        
        # If proposed patch is empty, no conflict
        if not proposal.proposed_patch.strip():
            return False
        
        # Simple heuristic: if the content has changed significantly
        # and the proposal doesn't match the current content
        # In a real implementation, we'd compare against the base version
        # For now, we'll use a simple string similarity check
        
        # If the proposed patch is exactly the current content, no conflict
        if proposal.proposed_patch == current_content:
            return False
        
        # If the proposed patch is a subset of current content, might be a conflict
        # This is a simplified check - real implementation would use diff3
        return False

    def _record_audit(
        self,
        kind: AuditEventKind,
        actor: str,
        proposal_id: Optional[str] = None,
        target_section=None,
        message: str = "",
    ) -> AuditEvent:
        """Record an audit event."""
        now = datetime.now(timezone.utc)
        audit_id = f"audit-{kind.value}-{int(now.timestamp())}"

        event = AuditEvent(
            id=audit_id,
            kind=kind,
            actor=actor,
            proposal_id=proposal_id,
            target_section=target_section,
            message=message,
            created_at=now,
        )

        atomic_write_json(
            self._storage.paths.audit_file(audit_id),
            asdict(event),
        )

        return event

    def _from_dict(self, data: dict) -> EvolutionProposal:
        """Convert a dict to an EvolutionProposal."""
        from .types import (
            EvidenceRef,
            EvidenceSource,
            LaputaSectionName,
            ProposalType,
            RiskLevel,
        )

        return EvolutionProposal(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            created_by=data["created_by"],
            proposal_type=ProposalType(data["proposal_type"]),
            target_section=LaputaSectionName(data["target_section"]),
            evidence_refs=[
                EvidenceRef(
                    id=e["id"],
                    source=EvidenceSource(e["source"]),
                    uri=e["uri"],
                    excerpt=e.get("excerpt"),
                    hash=e.get("hash"),
                    created_at=datetime.fromisoformat(e["created_at"]),
                )
                for e in data.get("evidence_refs", [])
            ],
            proposed_patch=data["proposed_patch"],
            risk_level=RiskLevel(data["risk_level"]),
            state=ProposalState(data["state"]),
            source_run_id=data.get("source_run_id"),
        )
