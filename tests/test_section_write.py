"""Tests for section write operations."""

import pytest
from datetime import datetime, timezone

from laputa.service import LaputaService
from laputa.error import DirectWriteNotAllowed
from laputa.types import LaputaSectionName


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    return tmp_path


@pytest.fixture
def service(workspace):
    """Create a LaputaService instance."""
    return LaputaService.open(workspace)


def test_write_commitment_section(service):
    """Test writing to commitment section (allowed)."""
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


def test_write_preferences_section(service):
    """Test writing to preferences section (allowed)."""
    changelog, audit = service.write_section(
        LaputaSectionName.PREFERENCES,
        "new preferences content",
        "test-user",
    )
    assert changelog.target_section == LaputaSectionName.PREFERENCES
    assert changelog.after == "new preferences content"


def test_write_identity_section_forbidden(service):
    """Test that writing to identity section is forbidden."""
    with pytest.raises(DirectWriteNotAllowed):
        service.write_section(
            LaputaSectionName.IDENTITY,
            "new identity",
            "test-user",
        )


def test_write_relationship_section_forbidden(service):
    """Test that writing to relationship section is forbidden."""
    with pytest.raises(DirectWriteNotAllowed):
        service.write_section(
            LaputaSectionName.RELATIONSHIP,
            "new relationship",
            "test-user",
        )


def test_write_memory_md_section_forbidden(service):
    """Test that writing to memory_md section is forbidden."""
    with pytest.raises(DirectWriteNotAllowed):
        service.write_section(
            LaputaSectionName.MEMORY_MD,
            "new memory",
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


def test_write_section_overwrites(service):
    """Test that writing overwrites previous content."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "first content",
        "test-user",
    )
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "second content",
        "test-user",
    )
    section = service.read_section(LaputaSectionName.COMMITMENT)
    assert section.content == "second content"


def test_write_section_changelog_recorded(service):
    """Test that changelog is recorded for direct write."""
    changelog, _ = service.write_section(
        LaputaSectionName.COMMITMENT,
        "test content",
        "test-user",
    )
    retrieved = service.get_changelog(changelog.id)
    assert retrieved.id == changelog.id
    assert retrieved.target_section == LaputaSectionName.COMMITMENT
    assert retrieved.applied_by == "test-user"


def test_write_section_audit_recorded(service):
    """Test that audit event is recorded for direct write."""
    _, audit = service.write_section(
        LaputaSectionName.COMMITMENT,
        "test content",
        "test-user",
        "test reason",
    )
    assert audit.kind.value == "proposal_applied"
    assert audit.message == "direct write to commitment: test reason"
