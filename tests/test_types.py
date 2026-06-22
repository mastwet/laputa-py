"""Tests for core types."""

import pytest
from datetime import datetime, timezone

from laputa.types import (
    LaputaSectionName,
    ProposalType,
    ProposalState,
    RiskLevel,
    EvidenceSource,
    EvidenceRef,
    EvolutionProposal,
    route_proposal_type,
    validate_governance_evidence,
)


def test_laputa_section_all_v1():
    """Test all_v1 returns 14 sections."""
    sections = LaputaSectionName.all_v1()
    assert len(sections) == 11
    assert sections[0] == LaputaSectionName.IDENTITY
    assert sections[-1] == LaputaSectionName.AAAK_SUMMARIES


def test_proposal_type_target_section():
    """Test proposal type routing."""
    assert ProposalType.MEMORY_PATCH.target_section() == LaputaSectionName.MEMORY_MD
    assert ProposalType.IDENTITY_PATCH.target_section() == LaputaSectionName.IDENTITY
    assert ProposalType.DEPRECATION.target_section() == LaputaSectionName.CHANGELOG


def test_route_proposal_type():
    """Test route_proposal_type function."""
    assert route_proposal_type("memory_patch") == LaputaSectionName.MEMORY_MD


def test_validate_governance_evidence():
    """Test evidence validation."""
    now = datetime.now(timezone.utc)
    
    # Empty evidence should fail
    with pytest.raises(ValueError, match="at least one"):
        validate_governance_evidence([])
    
    # Only compaction evidence should fail
    compaction = EvidenceRef(
        id="1",
        source=EvidenceSource.CONTEXT_COMPACTION,
        uri="test://1",
        created_at=now,
    )
    with pytest.raises(ValueError, match="context compaction"):
        validate_governance_evidence([compaction])
    
    # Session evidence should pass
    session = EvidenceRef(
        id="2",
        source=EvidenceSource.SESSION,
        uri="session://1",
        created_at=now,
    )
    validate_governance_evidence([session])
