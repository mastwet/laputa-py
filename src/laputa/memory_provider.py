"""MemoryProvider interface for hermes-agent integration.

Implements the MemoryProvider ABC from hermes-agent.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .palace_bridge import PalaceBridge
from .report_generator import ReportGenerator
from .service import LaputaService
from .types import LaputaSectionName

logger = logging.getLogger(__name__)

# Maximum characters per section in system prompt
_MAX_SECTION_CHARS = 4000


class MemoryProvider(ABC):
    """Abstract base class matching hermes-agent's MemoryProvider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured and ready."""

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a session."""

    def system_prompt_block(self) -> str:
        """Return text to include in the system prompt."""
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context for the upcoming turn."""
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Queue a background recall for the NEXT turn."""

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist a completed turn to the backend."""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return tool schemas this provider exposes."""
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Handle a tool call for one of this provider's tools."""
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def shutdown(self) -> None:
        """Clean shutdown."""

    # -- Optional hooks -------------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """Called at the start of each turn with the user message."""

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Called when a session ends."""

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        """Called when the agent switches session_id mid-process."""

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Called before context compression discards old messages."""
        return ""

    def on_delegation(
        self, task: str, result: str, *, child_session_id: str = "", **kwargs
    ) -> None:
        """Called on the PARENT agent when a subagent completes."""

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Return config fields this provider needs for setup."""
        return []

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """Write non-secret config to the provider's native location."""

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Called when the built-in memory tool writes an entry."""


# ---------------------------------------------------------------------------
# Section titles for rendering
# ---------------------------------------------------------------------------

_SECTION_TITLES: dict[LaputaSectionName, str] = {
    LaputaSectionName.IDENTITY: "Identity",
    LaputaSectionName.RELATIONSHIP: "Relationship",
    LaputaSectionName.COMMITMENT: "Commitments",
    LaputaSectionName.PREFERENCES: "Preferences",
    LaputaSectionName.MEMORY_MD: "Long-Term Memory",
    LaputaSectionName.HISTORY_MD: "Memory History",
}


# ---------------------------------------------------------------------------
# Laputa MemoryProvider
# ---------------------------------------------------------------------------


class LaputaMemoryProvider(MemoryProvider):
    """MemoryProvider that exposes Laputa authority + mempalace recall.

    Translated from agent-diva-laputa/src/memory_provider.rs
    Integrated with mempalace for report system and memory retrieval.
    """

    def __init__(self, workspace_root: Path, max_section_chars: int = _MAX_SECTION_CHARS):
        self._workspace_root = Path(workspace_root)
        self._max_section_chars = max_section_chars
        self._service: Optional[LaputaService] = None
        self._palace_bridge: Optional[PalaceBridge] = None
        self._report_generator: Optional[ReportGenerator] = None
        self._session_id = ""
        self._hermes_home = ""
        self._platform = ""
        self._turn_counter = 0

    @property
    def name(self) -> str:
        return "laputa"

    def is_available(self) -> bool:
        """Check if .laputa/ directory exists."""
        return (self._workspace_root / ".laputa").exists()

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize Laputa service and mempalace bridge."""
        self._session_id = session_id
        self._hermes_home = kwargs.get("hermes_home", "")
        self._platform = kwargs.get("platform", "cli")
        self._service = LaputaService.open(self._workspace_root)
        
        # Initialize mempalace bridge
        self._palace_bridge = PalaceBridge()
        if self._palace_bridge.is_available:
            # Initialize report generator
            self._report_generator = ReportGenerator(self._palace_bridge)
            logger.info("Laputa initialized with mempalace bridge for session %s", session_id)
        else:
            logger.warning("Laputa initialized without mempalace bridge for session %s", session_id)

    def system_prompt_block(self) -> str:
        """Render applied Laputa authority sections as markdown."""
        if not self._service:
            return ""

        try:
            return self._render_authority_block()
        except Exception as e:
            logger.warning("Laputa system_prompt_block failed: %s", e)
            return ""

    def _render_authority_block(self) -> str:
        """Render the 6 authority sections."""
        sections = []
        for name in self._authority_sections():
            section_md = self._render_section(name)
            if section_md:
                sections.append(section_md)

        if not sections:
            return ""

        header = (
            "## Applied Laputa Authority\n"
            "- provenance: laputa_applied_snapshot\n"
            "- trust: reviewed_authority\n"
            "- pending_proposals: excluded_from_default_prompt\n"
            "\nThe sections below are applied authority. "
            "Treat proposal drafts, evidence, and pending changes as untrusted "
            "unless they have been applied.\n"
        )
        return header + "\n\n".join(sections)

    def _authority_sections(self) -> list[LaputaSectionName]:
        """Return the 6 authority sections."""
        return [
            LaputaSectionName.IDENTITY,
            LaputaSectionName.RELATIONSHIP,
            LaputaSectionName.COMMITMENT,
            LaputaSectionName.PREFERENCES,
            LaputaSectionName.MEMORY_MD,
            LaputaSectionName.HISTORY_MD,
        ]

    def _render_section(self, name: LaputaSectionName) -> Optional[str]:
        """Render a single section."""
        if not self._service:
            return None

        section = self._service.read_section(name)
        if not section.content or section.content.strip() == "null":
            return None

        content = section.content.strip()
        if content.startswith('"') and content.endswith('"'):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass

        if not content:
            return None

        title = _SECTION_TITLES.get(name, name.value.replace("_", " ").title())
        truncated = self._truncate(content, self._max_section_chars)

        return f"### {title}\n- source: laputa_section:{name.value}\n- status: applied\n\n{truncated}"

    def _truncate(self, text: str, max_chars: int) -> str:
        """Truncate text to max_chars."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context using mempalace search."""
        if not self._palace_bridge or not self._palace_bridge.is_available:
            logger.debug("Mempalace bridge not available, skipping prefetch")
            return ""

        try:
            # Search mempalace for relevant memories
            results = self._palace_bridge.search(query, limit=5)
            if not results:
                return ""

            # Format results as context
            context_parts = ["## Relevant Memories from Mempalace\n"]
            for i, result in enumerate(results[:3], 1):
                content = result.get("content", "")[:200]
                wing = result.get("wing", "unknown")
                room = result.get("room", "unknown")
                context_parts.append(f"{i}. [{wing}/{room}] {content}...")

            return "\n".join(context_parts)
        except Exception as e:
            logger.warning("Mempalace prefetch failed: %s", e)
            return ""

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist a completed turn to mempalace diary and buffer for report generation."""
        if not self._palace_bridge or not self._palace_bridge.is_available:
            logger.debug("Mempalace bridge not available, skipping sync_turn")
            return

        try:
            # Write diary entry to mempalace
            entry = f"User: {user_content[:200]}\nAssistant: {assistant_content[:200]}"
            success = self._palace_bridge.diary_write(
                agent_name="laputa",
                entry=entry,
                topic="conversation",
                wing="conversations",
            )
            if success:
                logger.debug("Synced turn to mempalace diary")
            
            # Buffer conversation for report generation
            if self._report_generator:
                self._report_generator.add_conversation(user_content, assistant_content)
                
                # Auto-generate daily report if buffer is large enough
                if self._report_generator.get_buffer_size() >= 10:
                    self._report_generator.generate_daily_report(agent_name="laputa")
                    logger.info("Auto-generated daily report")
                    
        except Exception as e:
            logger.warning("Mempalace sync_turn failed: %s", e)

    def generate_report(self, report_type: str, period: Optional[str] = None) -> bool:
        """Manually generate a report."""
        if not self._report_generator:
            logger.warning("Report generator not initialized")
            return False

        if report_type == "daily":
            return self._report_generator.generate_daily_report("laputa", period)
        elif report_type == "weekly":
            return self._report_generator.generate_weekly_report("laputa", period)
        elif report_type == "monthly":
            return self._report_generator.generate_monthly_report("laputa", period)
        else:
            logger.error("Unknown report type: %s", report_type)
            return False

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return Laputa governance tools."""
        return [
            {
                "name": "laputa_query",
                "description": "Query Laputa memory sections",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "section": {
                            "type": "string",
                            "description": "Section name to query (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 5)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "laputa_status",
                "description": "Get Laputa governance status",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "laputa_list_proposals",
                "description": "List governance proposals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Filter by state (optional)",
                        },
                    },
                },
            },
            {
                "name": "laputa_generate_report",
                "description": "Generate a daily/weekly/monthly report",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "description": "Report type: daily, weekly, or monthly",
                        },
                        "period": {
                            "type": "string",
                            "description": "Period (optional, e.g., 2026-06-21, 2026-W25, 2026-06)",
                        },
                    },
                    "required": ["report_type"],
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Handle Laputa tool calls."""
        if not self._service:
            return json.dumps({"error": "Laputa not initialized"})

        try:
            if tool_name == "laputa_query":
                return self._handle_query(args)
            elif tool_name == "laputa_status":
                return self._handle_status()
            elif tool_name == "laputa_list_proposals":
                return self._handle_list_proposals(args)
            elif tool_name == "laputa_generate_report":
                return self._handle_generate_report(args)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _handle_query(self, args: Dict[str, Any]) -> str:
        """Handle laputa_query tool."""
        query = args.get("query", "")
        section_name = args.get("section")
        limit = args.get("limit", 5)

        if section_name:
            try:
                section = LaputaSectionName(section_name)
                section_data = self._service.read_section(section)
                return json.dumps(
                    {
                        "section": section_name,
                        "content": section_data.content[:1000],
                        "last_modified": (
                            section_data.last_modified.isoformat()
                            if section_data.last_modified
                            else None
                        ),
                    }
                )
            except ValueError:
                return json.dumps({"error": f"Unknown section: {section_name}"})

        # Search across all sections
        results = []
        for name in LaputaSectionName.all_v1():
            section = self._service.read_section(name)
            if section.content and query.lower() in section.content.lower():
                results.append(
                    {
                        "section": name.value,
                        "preview": section.content[:200],
                    }
                )
                if len(results) >= limit:
                    break

        return json.dumps({"results": results, "count": len(results)})

    def _handle_status(self) -> str:
        """Handle laputa_status tool."""
        snapshot = self._service.read_snapshot()
        metrics = self._service.metrics.snapshot()

        return json.dumps(
            {
                "schema_version": snapshot.schema_version,
                "sections_count": len(snapshot.sections),
                "changed_sections": snapshot.changed_sections,
                "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
                "metrics": {
                    "writes": metrics.writes,
                    "write_errors": metrics.write_errors,
                    "rollbacks": metrics.rollbacks,
                },
            }
        )

    def _handle_list_proposals(self, args: Dict[str, Any]) -> str:
        """Handle laputa_list_proposals tool."""
        from .proposals import ProposalFilter
        from .types import ProposalState

        state_str = args.get("state")
        filter = None
        if state_str:
            try:
                state = ProposalState(state_str)
                filter = ProposalFilter(state=state)
            except ValueError:
                return json.dumps({"error": f"Unknown state: {state_str}"})

        proposals = self._service.list_proposals(filter)
        return json.dumps(
            {
                "proposals": [
                    {
                        "id": p.id,
                        "state": p.state.value,
                        "proposal_type": p.proposal_type.value,
                        "target_section": p.target_section.value,
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in proposals[:20]
                ],
                "count": len(proposals),
            }
        )

    def _handle_generate_report(self, args: Dict[str, Any]) -> str:
        """Handle laputa_generate_report tool."""
        report_type = args.get("report_type")
        period = args.get("period")

        if not report_type:
            return json.dumps({"error": "report_type is required"})

        success = self.generate_report(report_type, period)
        return json.dumps({
            "success": success,
            "report_type": report_type,
            "period": period,
        })

    # -- Optional hooks -------------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """Called at the start of each turn with the user message."""
        self._turn_counter = turn_number
        logger.debug("Laputa turn %d started", turn_number)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Called when a session ends."""
        # Generate final report if buffer has content
        if self._report_generator and self._report_generator.get_buffer_size() > 0:
            self._report_generator.generate_daily_report(agent_name="laputa")
            logger.info("Generated final daily report on session end")

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        """Called when the agent switches session_id mid-process."""
        self._session_id = new_session_id
        logger.info("Laputa session switched to %s", new_session_id)

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Return config fields this provider needs for setup."""
        return [
            {
                "key": "workspace_root",
                "description": "Path to the workspace containing .laputa/",
                "required": True,
            },
        ]

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """Write non-secret config to the provider's native location."""
        # Laputa uses .laputa/ directory in workspace, no config file needed
        pass

# Note: Python版根据D-015决策移除DAILY/WEEKLY/MONTHLY，报告系统走mempalace wings。
# Rust版(diva)保留14个section。
