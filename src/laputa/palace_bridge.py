"""Mempalace integration bridge for Laputa.

Provides optional integration with mempalace for enhanced memory retrieval.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PalaceBridge:
    """Bridge to mempalace for enhanced memory operations.

    This is an optional component - if mempalace is not available,
    operations will gracefully degrade.
    """

    def __init__(self, palace_path: Optional[str] = None):
        self._palace_path = palace_path
        self._available = False
        self._mempalace = None
        self._try_init()

    def _try_init(self) -> None:
        """Try to initialize mempalace connection."""
        try:
            import mempalace
            self._mempalace = mempalace
            self._available = True
            logger.info("Mempalace bridge initialized")
        except ImportError:
            logger.info("Mempalace not available, bridge disabled")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if mempalace is available."""
        return self._available

    def search(self, query: str, limit: int = 5, wing: Optional[str] = None, room: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search mempalace for relevant memories."""
        if not self._available:
            return []

        try:
            # Use mempalace_search tool
            result = self._mempalace.tool_search(
                query=query,
                limit=limit,
                wing=wing,
                room=room,
            )
            if "error" in result:
                logger.warning("Mempalace search error: %s", result["error"])
                return []
            return result.get("results", [])
        except Exception as e:
            logger.warning("Mempalace search failed: %s", e)
            return []

    def diary_write(self, agent_name: str, entry: str, topic: str = "general", wing: Optional[str] = None) -> bool:
        """Write a diary entry to mempalace."""
        if not self._available:
            return False

        try:
            # Use mempalace_diary_write tool
            result = self._mempalace.tool_diary_write(
                agent_name=agent_name,
                entry=entry,
                topic=topic,
                wing=wing or "",
            )
            if "error" in result:
                logger.warning("Mempalace diary write error: %s", result["error"])
                return False
            return True
        except Exception as e:
            logger.warning("Mempalace diary write failed: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get mempalace status."""
        return {
            "available": self._available,
            "palace_path": self._palace_path,
        }

    def write_daily_report(self, agent_name: str, date: str, content: str) -> bool:
        """写入日报到mempalace wings/daily/"""
        if not self._available:
            return False
        try:
            # 调用mempalace API写入wings/daily/{date}
            result = self._mempalace.tool_diary_write(
                agent_name=agent_name,
                entry=content,
                topic="daily_report",
                wing="daily",
            )
            if "error" in result:
                logger.error("Failed to write daily report: %s", result["error"])
                return False
            logger.info("Writing daily report to mempalace wings/daily/%s", date)
            return True
        except Exception as e:
            logger.error("Failed to write daily report: %s", e)
            return False

    def write_weekly_report(self, agent_name: str, week: str, content: str) -> bool:
        """写入周报到mempalace wings/weekly/"""
        if not self._available:
            return False
        try:
            # 调用mempalace API写入wings/weekly/{week}
            result = self._mempalace.tool_diary_write(
                agent_name=agent_name,
                entry=content,
                topic="weekly_report",
                wing="weekly",
            )
            if "error" in result:
                logger.error("Failed to write weekly report: %s", result["error"])
                return False
            logger.info("Writing weekly report to mempalace wings/weekly/%s", week)
            return True
        except Exception as e:
            logger.error("Failed to write weekly report: %s", e)
            return False

    def write_monthly_report(self, agent_name: str, month: str, content: str) -> bool:
        """写入月报到mempalace wings/monthly/"""
        if not self._available:
            return False
        try:
            # 调用mempalace API写入wings/monthly/{month}
            result = self._mempalace.tool_diary_write(
                agent_name=agent_name,
                entry=content,
                topic="monthly_report",
                wing="monthly",
            )
            if "error" in result:
                logger.error("Failed to write monthly report: %s", result["error"])
                return False
            logger.info("Writing monthly report to mempalace wings/monthly/%s", month)
            return True
        except Exception as e:
            logger.error("Failed to write monthly report: %s", e)
            return False
