"""Tests for LaputaService."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from laputa.service import LaputaService
from laputa.error import DirectWriteNotAllowed
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


def test_service_open_creates_structure(service, workspace):
    """Test that opening service creates .laputa/ structure."""
    laputa_dir = workspace / ".laputa"
    assert laputa_dir.exists()
    assert (laputa_dir / "proposals").exists()
    assert (laputa_dir / "sections").exists()
    assert (laputa_dir / "changelog").exists()


def test_read_empty_section(service):
    """Test reading an empty section."""
    section = service.read_section(LaputaSectionName.IDENTITY)
    assert section.name == LaputaSectionName.IDENTITY
    assert section.content == ""


def test_read_snapshot(service):
    """Test reading snapshot."""
    snapshot = service.read_snapshot()
    assert snapshot.schema_version == "1.0.0"
    assert len(snapshot.sections) == 11


def test_create_and_get_proposal(service):
    """Test creating and retrieving a proposal."""
    now = datetime.now(timezone.utc)
    proposal = EvolutionProposal(
        id="test-1",
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

    created = service.create_proposal(proposal)
    assert created.id == "test-1"

    retrieved = service.get_proposal("test-1")
    assert retrieved.id == "test-1"
    assert retrieved.state == ProposalState.PENDING_REVIEW


def test_write_section_commitment(service):
    """Test direct write to commitment section."""
    changelog, audit = service.write_section(
        LaputaSectionName.COMMITMENT,
        "new commitment content",
        "test-user",
        "test update",
    )
    assert changelog.target_section == LaputaSectionName.COMMITMENT
    assert changelog.before == ""
    assert changelog.after == "new commitment content"
    assert audit.actor == "test-user"


def test_write_section_preferences(service):
    """Test direct write to preferences section."""
    changelog, audit = service.write_section(
        LaputaSectionName.PREFERENCES,
        "new preferences",
        "test-user",
    )
    assert changelog.target_section == LaputaSectionName.PREFERENCES
    assert changelog.after == "new preferences"


def test_write_section_unauthorized(service):
    """Test that direct write to other sections raises DirectWriteNotAllowed."""
    with pytest.raises(DirectWriteNotAllowed):
        service.write_section(
            LaputaSectionName.IDENTITY,
            "new identity",
            "test-user",
        )


def test_write_section_then_read(service):
    """Test that written content can be read back."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "persistent content",
        "test-user",
    )
    section = service.read_section(LaputaSectionName.COMMITMENT)
    assert section.content == "persistent content"


def test_get_changelog(service):
    """Test getting a single changelog record."""
    changelog, _ = service.write_section(
        LaputaSectionName.COMMITMENT,
        "test content",
        "test-user",
    )
    retrieved = service.get_changelog(changelog.id)
    assert retrieved.id == changelog.id
    assert retrieved.target_section == LaputaSectionName.COMMITMENT


def test_get_changelog_not_found(service):
    """Test getting a non-existent changelog raises error."""
    with pytest.raises(ValueError, match="changelog not found"):
        service.get_changelog("nonexistent-id")


def test_apply_proposal(service):
    """Test applying a proposal creates changelog and audit."""
    now = datetime.now(timezone.utc)
    proposal = EvolutionProposal(
        id="test-apply",
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
        proposed_patch="new memory content",
        risk_level=RiskLevel.LOW,
        state=ProposalState.PENDING_REVIEW,
    )

    service.create_proposal(proposal)

    service.transition_proposal("test-apply", ProposalState.APPROVED)

    applied_proposal, changelog, audit = service.apply_proposal(
        "test-apply", "test-user"
    )

    assert applied_proposal.state == ProposalState.APPLIED
    assert changelog.target_section == LaputaSectionName.MEMORY_MD
    assert changelog.after == "new memory content"
    assert audit.actor == "test-user"
