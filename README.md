# Laputa-Py

Pure Python Laputa governance layer for AI agents.

## Overview

Laputa-Py is a governance framework for AI agents that provides structured evolution and management of agent behavior. It implements the Laputa governance protocol, enabling controlled modifications to agent configuration through a proposal-based system with audit trails and rollback capabilities.

## Features

- **Proposal-based governance**: All changes to agent behavior go through a structured proposal process
- **Six governance flows**: Complete lifecycle management for proposals (draft → review → approve → apply → audit → rollback)
- **Section-based configuration**: Organized into distinct sections (commitments, preferences, skills, etc.)
- **Conflict detection**: Automatic detection of conflicting proposals
- **Audit trail**: Complete history of all governance actions
- **Rollback support**: Ability to revert changes with expiration policies
- **Changelog tracking**: Detailed logs of all modifications

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/laputa-py.git
cd laputa-py

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Quick Start

```python
from laputa import LaputaService, ProposalType, RiskLevel

# Initialize the service
service = LaputaService()

# Create a proposal
proposal = service.create_proposal(
    proposal_type=ProposalType.MEMORY_PATCH,
    content="Update agent memory with new information",
    risk_level=RiskLevel.LOW,
    evidence_refs=[...]
)

# Apply the proposal through governance flow
service.apply_proposal(proposal.id)
```

## Design Documentation

Detailed design documents (architecture baselines, research, PRD reconciliation, legacy lineage) are consolidated under [`docs/`](docs/README.md). The canonical versions remain in `morediva/`; `docs/` is for centralized reading and cross-project traceability. See [`docs/README.md`](docs/README.md) for the full index, reading paths, and timeline.

## Project Structure

```
laputa-py/
├── src/
│   └── laputa/
│       ├── __init__.py          # Package initialization and exports
│       ├── types.py             # Core domain types and enums
│       ├── service.py           # Main service layer
│       ├── proposals.py         # Proposal management
│       ├── layout.py            # Storage layout management
│       ├── lock.py              # Concurrency control
│       ├── metrics.py           # Governance metrics
│       ├── atomic.py            # Atomic file operations
│       ├── error.py             # Custom exceptions
│       ├── cli.py               # Command-line interface
│       └── ...                  # Other modules
├── tests/                       # Test suite
├── docs/                        # Design documents (consolidated from morediva/)
├── pyproject.toml               # Project configuration
└── TODOLIST.md                  # Development roadmap
```

## Governance Sections

Laputa organizes agent configuration into the following sections:

- **Commitment**: Core behavioral commitments and constraints
- **Preferences**: User and system preferences
- **Skills**: Agent capabilities and skills
- **Memory**: Long-term memory configuration
- **Context**: Context management settings
- **Evolution**: Evolution and learning parameters

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/laputa
```

### Code Quality

```bash
# Run linting (if configured)
flake8 src/ tests/

# Run type checking (if configured)
mypy src/
```

## API Reference

### Core Classes

- `LaputaService`: Main service class for governance operations
- `EvolutionProposal`: Represents a governance proposal
- `ChangelogRecord`: Records changes made through governance
- `AuditEvent`: Tracks governance actions for audit purposes

### Key Methods

- `create_proposal()`: Create a new governance proposal
- `apply_proposal()`: Apply a proposal through the governance flow
- `write_section()`: Directly write to governance sections (with permission checks)
- `get_changelog()`: Retrieve changelog records
- `rollback_proposal()`: Rollback a previously applied proposal

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] HTTP API layer
- [ ] Event-driven interface
- [ ] Mentle integration
- [ ] Enhanced conflict resolution
- [ ] Performance optimizations

## Acknowledgments

- Inspired by the Laputa governance protocol
- Built for AI agent evolution and management