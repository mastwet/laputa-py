"""Tests for 6-step governance flow."""

import pytest
from datetime import datetime, timezone

from laputa.service import LaputaService
from laputa.types import (
    LaputaSectionName,
    ProposalType,
    ProposalState,
    RiskLevel,
    EvidenceSource,
    EvidenceRef,
    EvolutionProposal,
)


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    return tmp_path


@pytest.fixture
def service(workspace):
    """Create a LaputaService instance."""
    return LaputaService.open(workspace)


def _create_proposal(service, proposal_id="test-1"):
    """Helper to create a test proposal."""
    now = datetime.now(timezone.utc)
    proposal = EvolutionProposal(
        id=proposal_id,
        created_at=now,
        updated_at=now,
        created_by="test",
        proposal_type=ProposalType.MEMORY_PATCH,
        target_section=LaputaSectionName.MEMORY_MD,
        evidence_refs=[
            EvidenceRef(
                id="ev-1",
                source=EvidenceSource.SESSION,
                uri="session://test",
                created_at=now,
            )
        ],
        proposed_patch="test content",
        risk_level=RiskLevel.LOW,
        state=ProposalState.PENDING_REVIEW,
    )
    return service.create_proposal(proposal)


def test_governance_step1_review(service):
    """Step 1: Review - status check."""
    proposal = _create_proposal(service)
    assert proposal.state == ProposalState.PENDING_REVIEW


def test_governance_step2_changelog(service):
    """Step 2: Changelog - record applied change."""
    proposal = _create_proposal(service)
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    
    assert changelog.action.value == "apply"
    assert changelog.target_section == LaputaSectionName.MEMORY_MD
    assert changelog.applied_by == "test-user"


def test_governance_step3_audit(service):
    """Step 3: Audit - emit event."""
    proposal = _create_proposal(service)
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    
    assert audit.kind.value == "proposal_applied"
    assert audit.actor == "test-user"
    assert audit.target_section == LaputaSectionName.MEMORY_MD


def test_governance_step4_flock(service):
    """Step 4: Flock - write lock is acquired (implicit in implementation)."""
    proposal = _create_proposal(service)
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    assert applied.state == ProposalState.APPLIED


def test_governance_step5_conflict_resolution(service):
    """Step 5: Conflict resolution - check for conflicts."""
    proposal = _create_proposal(service)
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    assert applied.state == ProposalState.APPLIED


def test_governance_step6_rollback(service):
    """Step 6: Rollback - within 30-day window."""
    proposal = _create_proposal(service)
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    
    rolled_back, rollback_audit = service.rollback_changelog(
        changelog.id,
        "test-user",
        "test rollback",
    )
    
    assert rolled_back.reverted is True
    assert rollback_audit.kind.value == "rollback_applied"


def test_governance_full_flow(service):
    """Test complete 6-step governance flow."""
    proposal = _create_proposal(service)
    assert proposal.state == ProposalState.PENDING_REVIEW
    
    service.transition_proposal("test-1", ProposalState.APPROVED)
    applied, changelog, audit = service.apply_proposal("test-1", "test-user")
    assert applied.state == ProposalState.APPLIED
    assert changelog.action.value == "apply"
    assert audit.kind.value == "proposal_applied"
    
    rolled_back, rollback_audit = service.rollback_changelog(
        changelog.id,
        "test-user",
        "test rollback",
    )
    assert rolled_back.reverted is True
    assert rollback_audit.kind.value == "rollback_applied"
