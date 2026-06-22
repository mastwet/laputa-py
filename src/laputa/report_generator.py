"""Report generator for daily/weekly/monthly reports.

Generates reports from conversation history and writes to mempalace wings.
Uses LLM to summarize and compress conversation history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from .palace_bridge import PalaceBridge

logger = logging.getLogger(__name__)

# Type for LLM callback function
LlmCallback = Callable[[str], str]


class ReportGenerator:
    """Generates daily/weekly/monthly reports from conversation history."""

    def __init__(self, palace_bridge: PalaceBridge, llm_callback: Optional[LlmCallback] = None):
        self._palace_bridge = palace_bridge
        self._llm_callback = llm_callback  # Callback function for LLM generation
        self._conversation_buffer: list[str] = []

    def add_conversation(self, user_content: str, assistant_content: str) -> None:
        """Add a conversation to the buffer for report generation."""
        self._conversation_buffer.append(f"User: {user_content[:200]}")
        self._conversation_buffer.append(f"Assistant: {assistant_content[:200]}")

    def generate_daily_report(self, agent_name: str, date: Optional[str] = None) -> bool:
        """Generate and write daily report to mempalace."""
        if not self._palace_bridge.is_available:
            logger.warning("Mempalace not available, cannot generate daily report")
            return False

        if not self._conversation_buffer:
            logger.info("No conversations to generate daily report")
            return False

        date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Generate report content using LLM
        content = self._generate_report_content("daily", date)
        
        # Write to mempalace
        success = self._palace_bridge.write_daily_report(
            agent_name=agent_name,
            date=date,
            content=content,
        )
        
        if success:
            logger.info("Generated daily report for %s", date)
            # Clear buffer after successful report generation
            self._conversation_buffer.clear()
        
        return success

    def generate_weekly_report(self, agent_name: str, week: Optional[str] = None) -> bool:
        """Generate and write weekly report to mempalace."""
        if not self._palace_bridge.is_available:
            logger.warning("Mempalace not available, cannot generate weekly report")
            return False

        week = week or datetime.now(timezone.utc).strftime("%Y-W%W")
        
        # Generate report content using LLM
        content = self._generate_report_content("weekly", week)
        
        # Write to mempalace
        success = self._palace_bridge.write_weekly_report(
            agent_name=agent_name,
            week=week,
            content=content,
        )
        
        if success:
            logger.info("Generated weekly report for %s", week)
        
        return success

    def generate_monthly_report(self, agent_name: str, month: Optional[str] = None) -> bool:
        """Generate and write monthly report to mempalace."""
        if not self._palace_bridge.is_available:
            logger.warning("Mempalace not available, cannot generate monthly report")
            return False

        month = month or datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Generate report content using LLM
        content = self._generate_report_content("monthly", month)
        
        # Write to mempalace
        success = self._palace_bridge.write_monthly_report(
            agent_name=agent_name,
            month=month,
            content=content,
        )
        
        if success:
            logger.info("Generated monthly report for %s", month)
        
        return success

    def _generate_report_content(self, report_type: str, period: str) -> str:
        """Generate report content from conversation buffer.
        
        Uses LLM callback if available, otherwise falls back to simple concatenation.
        """
        if not self._conversation_buffer:
            return f"## {report_type.title()} Report - {period}\n\nNo conversations recorded."

        # Try to use LLM callback for report generation
        if self._llm_callback:
            try:
                return self._generate_with_llm(report_type, period)
            except Exception as e:
                logger.warning("LLM report generation failed: %s", e)
                # Fall back to simple concatenation
        
        # Fallback: simple concatenation
        return self._generate_simple(report_type, period)

    def _generate_with_llm(self, report_type: str, period: str) -> str:
        """Generate report using LLM callback."""
        conversations = "\n".join(self._conversation_buffer[-20:])
        
        prompt = f"""Generate a {report_type} report for period {period}.

Conversation history:
{conversations}

Please summarize:
1. Key topics discussed
2. Important decisions made
3. Action items or commitments
4. Notable insights or learnings

Format as a structured report."""

        # Call the LLM callback
        report_content = self._llm_callback(prompt)
        
        return report_content

    def _generate_simple(self, report_type: str, period: str) -> str:
        """Generate report using simple concatenation (fallback)."""
        conversations = "\n".join(self._conversation_buffer[-20:])
        
        return f"""## {report_type.title()} Report - {period}

### Summary
Generated from {len(self._conversation_buffer)} conversation entries.

### Key Conversations
{conversations}

### Generated at
{datetime.now(timezone.utc).isoformat()}
"""

    def get_buffer_size(self) -> int:
        """Get the current conversation buffer size."""
        return len(self._conversation_buffer)
