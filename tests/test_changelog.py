"""Tests for changelog query operations."""

import pytest
from datetime import datetime, timezone

from laputa.service import LaputaService, ChangelogFilter
from laputa.types import LaputaSectionName, ChangelogAction


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    return tmp_path


@pytest.fixture
def service(workspace):
    """Create a LaputaService instance."""
    return LaputaService.open(workspace)


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
    assert retrieved.applied_by == "test-user"


def test_get_changelog_not_found(service):
    """Test getting a non-existent changelog raises error."""
    with pytest.raises(ValueError, match="changelog not found"):
        service.get_changelog("nonexistent-id")


def test_list_changelog_empty(service):
    """Test listing changelog when empty."""
    records = service.list_changelog()
    assert len(records) == 0


def test_list_changelog_after_write(service):
    """Test listing changelog after a write."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "test content",
        "test-user",
    )
    records = service.list_changelog()
    assert len(records) == 1
    assert records[0].target_section == LaputaSectionName.COMMITMENT


def test_list_changelog_multiple(service):
    """Test listing multiple changelog records."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "content 1",
        "test-user",
    )
    service.write_section(
        LaputaSectionName.PREFERENCES,
        "content 2",
        "test-user",
    )
    records = service.list_changelog()
    assert len(records) == 2


def test_list_changelog_filter_by_section(service):
    """Test filtering changelog by section."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "commitment content",
        "test-user",
    )
    service.write_section(
        LaputaSectionName.PREFERENCES,
        "preferences content",
        "test-user",
    )
    
    filter = ChangelogFilter(target_section=LaputaSectionName.COMMITMENT)
    records = service.list_changelog(filter)
    assert len(records) == 1
    assert records[0].target_section == LaputaSectionName.COMMITMENT


def test_list_changelog_filter_by_action(service):
    """Test filtering changelog by action."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "test content",
        "test-user",
    )
    
    filter = ChangelogFilter(action=ChangelogAction.APPLY)
    records = service.list_changelog(filter)
    assert len(records) == 1
    assert records[0].action == ChangelogAction.APPLY


def test_list_changelog_pagination(service):
    """Test changelog pagination."""
    for i in range(5):
        service.write_section(
            LaputaSectionName.COMMITMENT,
            f"content {i}",
            "test-user",
        )
    
    filter = ChangelogFilter(page=1, page_size=2)
    records = service.list_changelog(filter)
    assert len(records) == 2
    
    filter = ChangelogFilter(page=2, page_size=2)
    records = service.list_changelog(filter)
    assert len(records) == 2
    
    filter = ChangelogFilter(page=3, page_size=2)
    records = service.list_changelog(filter)
    assert len(records) == 1


def test_list_changelog_sorted_by_date(service):
    """Test that changelog records are sorted by date (newest first)."""
    service.write_section(
        LaputaSectionName.COMMITMENT,
        "first content",
        "test-user",
    )
    service.write_section(
        LaputaSectionName.PREFERENCES,
        "second content",
        "test-user",
    )
    
    records = service.list_changelog()
    assert records[0].created_at >= records[1].created_at
