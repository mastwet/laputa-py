"""Stable domain contracts shared by Laputa, AutoDream, reports, and UI.

Translated from agent-diva-core/src/evolution/types.rs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EvolutionError(Exception):
    """Base error for governance domain helpers."""

    pass


class UnknownProposalType(EvolutionError):
    """The proposal type string is not part of the v1 governance contract."""

    def __init__(self, value: str):
        super().__init__(f"unknown proposal type: {value}")
        self.value = value


class UnknownLaputaSection(EvolutionError):
    """The Laputa section string is not part of the v1 governance contract."""

    def __init__(self, value: str):
        super().__init__(f"unknown Laputa section: {value}")
        self.value = value


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class EvidenceSource(str, Enum):
    """Evidence origin for a governance proposal."""

    SESSION = "session"
    REPORT = "report"
    AUTO_DREAM_RUN = "auto_dream_run"
    LAPUTA_SECTION = "laputa_section"
    USER_INPUT = "user_input"
    FILE = "file"
    CONTEXT_COMPACTION = "context_compaction"


@dataclass(frozen=True)
class EvidenceRef:
    """Typed pointer to bounded evidence used by governance review."""

    id: str
    source: EvidenceSource
    uri: str
    excerpt: Optional[str] = None
    hash: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def is_primary_governance_evidence(evidence: EvidenceRef) -> bool:
    """Return true when evidence can act as primary authority evidence.

    Context compaction is session-local prompt survival. It can support review as
    secondary evidence, but cannot be the sole authority behind durable changes.
    """
    return evidence.source != EvidenceSource.CONTEXT_COMPACTION


def validate_governance_evidence(evidence_refs: list[EvidenceRef]) -> None:
    """Validate that a proposal evidence set is not based only on context compaction."""
    if not evidence_refs:
        raise ValueError("governance evidence requires at least one evidence ref")
    if not any(is_primary_governance_evidence(e) for e in evidence_refs):
        raise ValueError(
            "context compaction evidence is secondary only and cannot be the sole evidence for a durable proposal"
        )


# ---------------------------------------------------------------------------
# Proposal Types
# ---------------------------------------------------------------------------


class ProposalType(str, Enum):
    """Supported EVO-DIVA governance proposal categories."""

    MEMORY_PATCH = "memory_patch"
    JOURNAL_NOTE = "journal_note"
    LEARNING_NOTE = "learning_note"
    IDENTITY_PATCH = "identity_patch"
    RELATIONSHIP_UPDATE = "relationship_update"
    COMMITMENT_SET = "commitment_set"
    SOP_CREATE = "sop_create"
    DEPRECATION = "deprecation"

    def target_section(self) -> LaputaSectionName:
        """Route this proposal type to the canonical v1 Laputa section."""
        _ROUTE = {
            ProposalType.MEMORY_PATCH: LaputaSectionName.MEMORY_MD,
            ProposalType.JOURNAL_NOTE: LaputaSectionName.JOURNAL_REFLECTIVE,
            ProposalType.LEARNING_NOTE: LaputaSectionName.PREFERENCES,
            ProposalType.IDENTITY_PATCH: LaputaSectionName.IDENTITY,
            ProposalType.SOP_CREATE: LaputaSectionName.IDENTITY,
            ProposalType.RELATIONSHIP_UPDATE: LaputaSectionName.RELATIONSHIP,
            ProposalType.COMMITMENT_SET: LaputaSectionName.COMMITMENT,
            ProposalType.DEPRECATION: LaputaSectionName.CHANGELOG,
        }
        return _ROUTE[self]


# ---------------------------------------------------------------------------
# Proposal States
# ---------------------------------------------------------------------------


class ProposalState(str, Enum):
    """Lifecycle state of a governance proposal."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    DEFERRED = "deferred"
    APPLIED = "applied"
    REVERTED = "reverted"
    SUPERSEDED = "superseded"
    NEEDS_ATTENTION = "needs_attention"
    RUN_FAILED = "run_failed"


# ---------------------------------------------------------------------------
# Risk Level
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Risk level attached to a proposal during review."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Laputa Sections
# ---------------------------------------------------------------------------


class LaputaSectionName(str, Enum):
    """Canonical names for the 11 Laputa v1 sections (Python版).
    
    Note: Python版根据D-015决策移除DAILY/WEEKLY/MONTHLY，报告系统走mempalace wings。
    Rust版(diva)保留14个section。
    """

    IDENTITY = "identity"
    RELATIONSHIP = "relationship"
    COMMITMENT = "commitment"
    PREFERENCES = "preferences"
    MEMORY_MD = "memory_md"
    HISTORY_MD = "history_md"
    JOURNAL_REFLECTIVE = "journal_reflective"
    PROPOSAL_INBOX = "proposal_inbox"
    CHANGELOG = "changelog"
    REPORT_INDEXES = "report_indexes"
    AAAK_SUMMARIES = "aaak_summaries"

    @classmethod
    def all_v1(cls) -> list[LaputaSectionName]:
        """Return all v1 Laputa sections in canonical order."""
        return [
            cls.IDENTITY,
            cls.RELATIONSHIP,
            cls.COMMITMENT,
            cls.PREFERENCES,
            cls.MEMORY_MD,
            cls.HISTORY_MD,
            cls.JOURNAL_REFLECTIVE,
            cls.PROPOSAL_INBOX,
            cls.CHANGELOG,
            cls.REPORT_INDEXES,
            cls.AAAK_SUMMARIES,
        ]


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


class ChangelogAction(str, Enum):
    """Action represented by a Laputa changelog record."""

    APPLY = "apply"
    REVERT = "revert"
    ROLLBACK = "rollback"


@dataclass
class ChangelogRecord:
    """Durable record of an applied, reverted, or rolled-back governance change."""

    id: str
    action: ChangelogAction
    target_section: LaputaSectionName
    before: str
    after: str
    diff: str
    created_at: datetime
    applied_by: str
    proposal_id: Optional[str] = None
    audit_event_id: Optional[str] = None
    reverted: bool = False
    stale: bool = False


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


class AuditEventKind(str, Enum):
    """Kind of audit event emitted by the governance spine."""

    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    PROPOSAL_EDITED = "proposal_edited"
    PROPOSAL_APPLIED = "proposal_applied"
    PROPOSAL_REVERTED = "proposal_reverted"
    ROLLBACK_REQUESTED = "rollback_requested"
    ROLLBACK_APPLIED = "rollback_applied"
    WRITE_FAILED = "write_failed"
    NEEDS_ATTENTION = "needs_attention"


@dataclass
class AuditEvent:
    """Auditable governance event for proposal and Laputa operations."""

    id: str
    kind: AuditEventKind
    actor: str
    message: str
    created_at: datetime
    proposal_id: Optional[str] = None
    target_section: Optional[LaputaSectionName] = None


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


@dataclass
class RollbackRequest:
    """Request to rollback a previously recorded changelog entry."""

    changelog_id: str
    requested_by: str
    reason: str
    requested_at: datetime


# ---------------------------------------------------------------------------
# Evolution Proposal
# ---------------------------------------------------------------------------


@dataclass
class EvolutionProposal:
    """Shared governance proposal envelope."""

    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    proposal_type: ProposalType
    target_section: LaputaSectionName
    evidence_refs: list[EvidenceRef]
    proposed_patch: str
    risk_level: RiskLevel
    state: ProposalState
    source_run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def route_proposal_type(value: str) -> LaputaSectionName:
    """Route a raw proposal type string to its canonical v1 Laputa section."""
    try:
        proposal_type = ProposalType(value)
    except ValueError:
        raise UnknownProposalType(value)
    return proposal_type.target_section()


def parse_laputa_section(value: str) -> LaputaSectionName:
    """Parse a string into a LaputaSectionName."""
    try:
        return LaputaSectionName(value)
    except ValueError:
        raise UnknownLaputaSection(value)
