
<!--
  Source: morediva/agent-diva-pro/.hermes/plans/laputa-hermes-architecture.md
  Consolidated to laputa-py on 2026-06-23 from morediva/.
  Authoritative canonical version lives at the source path above.
-->
# Laputa for Hermes-Agent 完整架构方案

## 1. 架构概述

### 1.1 设计目标
将 agent-diva-pro 的 Laputa 治理层设计引入 hermes-agent，实现：
- **统一治理层**：管理记忆和人格
- **权限分离**：Laputa 写、Mempalace 读（authority 单向）
- **完整治理流程**：6 道治理保证数据质量
- **与 mempalace 集成**：作为底层存储层

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes-Agent                              │
├─────────────────────────────────────────────────────────────┤
│              Laputa MemoryProvider (插件层)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LaputaGovernance (治理层)                            │   │
│  │  - 权限控制                                          │   │
│  │  - 6 道治理流程                                      │   │
│  │  - 审计和回滚                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│              ↓                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MempalaceAdapter (存储适配层)                        │   │
│  │  - Wing/Room/Drawer 管理                              │   │
│  │  - 语义搜索                                          │   │
│  │  - 知识图谱                                          │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│              Mempalace (底层存储)                            │
│  - SQLite 存储 (palace.db)                                  │
│  - 向量索引                                                │
│  - 原文存储                                                │
└─────────────────────────────────────────────────────────────┘
```

## 2. 核心组件设计

### 2.1 LaputaMemoryProvider (插件入口)

```python
class LaputaMemoryProvider(MemoryProvider):
    """Laputa 记忆提供者 - 实现 MemoryProvider 接口"""

    def __init__(self):
        self._governance = LaputaGovernance()
        self._storage = MempalaceAdapter()
        self._session_id = ""
        self._config = {}

    # 核心生命周期方法
    def initialize(self, session_id: str, **kwargs) -> None
    def system_prompt_block(self) -> str
    def prefetch(self, query: str, *, session_id: str = "") -> str
    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None
    def shutdown(self) -> None

    # 工具接口
    def get_tool_schemas(self) -> List[Dict[str, Any]]
    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str

    # 可选钩子
    def on_session_end(self, messages: List[Dict[str, Any]]) -> None
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str
```

### 2.2 LaputaGovernance (治理层)

```python
class LaputaGovernance:
    """Laputa 治理层 - 实现 6 道治理流程"""

    def __init__(self):
        self._review_queue = []
        self._changelog = []
        self._audit_log = []
        self._lock_manager = LockManager()

    # 6 道治理流程
    def review(self, proposal: Proposal) -> ReviewResult
    def changelog(self, change: Change) -> ChangelogRecord
    def audit(self, event: AuditEvent) -> None
    def lock(self, resource: str) -> Lock
    def conflict_resolve(self, current: Any, proposed: Any) -> Resolution
    def rollback(self, changelog_id: str) -> RollbackResult

    # 权限控制
    def check_write_permission(self, data: Any, actor: str) -> bool
    def check_read_permission(self, data: Any, actor: str) -> bool

    # 治理策略
    def apply_memory_governance(self, memory: Memory, actor: str) -> bool
    def apply_identity_governance(self, identity: Identity, actor: str) -> bool
```

### 2.3 MempalaceAdapter (存储适配层)

```python
class MempalaceAdapter:
    """Mempalace 存储适配器 - 对接 mempalace 底层存储"""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._connection = None

    # Wing 管理
    def create_wing(self, name: str, description: str) -> Wing
    def get_wing(self, name: str) -> Wing
    def list_wings(self) -> List[Wing]

    # Room 管理
    def create_room(self, wing: str, name: str) -> Room
    def get_room(self, wing: str, name: str) -> Room
    def list_rooms(self, wing: str) -> List[Room]

    # Drawer 管理
    def add_drawer(self, wing: str, room: str, content: str, metadata: dict) -> Drawer
    def get_drawer(self, drawer_id: str) -> Drawer
    def update_drawer(self, drawer_id: str, content: str) -> Drawer
    def delete_drawer(self, drawer_id: str) -> bool

    # 搜索和检索
    def search(self, query: str, limit: int = 5) -> List[SearchResult]
    def semantic_search(self, query: str, limit: int = 5) -> List[SearchResult]
    def kg_query(self, subject: str) -> List[Triple]
```

## 3. 数据模型设计

### 3.1 14 个 Content Section (Laputa 核心)

```python
class LaputaSection(Enum):
    # Laputa-owned (6 个)
    IDENTITY = "identity"           # 身份信息
    RELATIONSHIP = "relationship"   # 关系信息
    COMMITMENT = "commitment"       # 承诺信息
    PREFERENCES = "preferences"     # 偏好信息
    MEMORY_MD = "memory_md"         # 长期记忆
    HISTORY_MD = "history_md"       # 记忆历史

    # Report-owned (3 个)
    DAILY = "daily"                 # 日报
    WEEKLY = "weekly"               # 周报
    MONTHLY = "monthly"             # 月报

    # TBD (5 个)
    JOURNAL_REFLECTIVE = "journal_reflective"  # 反思日记
    EVOLUTION_PROPOSAL = "evolution_proposal"   # 进化提案
    CHANGELOG = "changelog"                     # 变更日志
    REPORT_INDEXES = "report_indexes"           # 报告索引
    AAAK_SUMMARIES = "aaak_summaries"           # AAAK 摘要
```

### 3.2 权限控制矩阵

```python
PERMISSION_MATRIX = {
    # section: (写权限, 读权限)
    "identity": ("agent_self", "all"),
    "relationship": ("agent_self", "all"),
    "commitment": ("user_only", "all"),
    "preferences": ("agent_self", "all"),
    "memory_md": ("agent_self", "all"),
    "history_md": ("agent_self", "all"),
    "daily": ("agent_self", "all"),
    "weekly": ("agent_self", "all"),
    "monthly": ("agent_self", "all"),
    "journal_reflective": ("tbd", "all"),
    "evolution_proposal": ("tbd", "all"),
    "changelog": ("tbd", "all"),
    "report_indexes": ("tbd", "all"),
    "aaak_summaries": ("tbd", "all"),
}
```

### 3.3 Proposal 类型

```python
class ProposalType(Enum):
    MEMORY_PATCH = "memory_patch"           # 记忆补丁
    JOURNAL_NOTE = "journal_note"           # 日记笔记
    LEARNING_NOTE = "learning_note"         # 学习笔记
    IDENTITY_PATCH = "identity_patch"       # 身份补丁
    RELATIONSHIP_UPDATE = "relationship_update"  # 关系更新
    COMMITMENT_SET = "commitment_set"       # 承诺设置
    SOP_CREATE = "sop_create"               # SOP 创建
    DEPRECATION = "deprecation"             # 废弃
```

## 4. 工具接口设计

### 4.1 暴露的工具

```python
LAPUTA_TOOLS = [
    {
        "name": "laputa_query",
        "description": "查询 Laputa 记忆",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查询内容"},
                "section": {"type": "string", "description": "查询的 section"},
                "limit": {"type": "integer", "description": "返回结果数量"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "laputa_update",
        "description": "更新 Laputa 记忆（需要经过治理）",
        "parameters": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "更新的 section"},
                "content": {"type": "string", "description": "更新内容"},
                "actor": {"type": "string", "description": "操作者"}
            },
            "required": ["section", "content", "actor"]
        }
    },
    {
        "name": "laputa_propose",
        "description": "提交 Laputa 提案",
        "parameters": {
            "type": "object",
            "properties": {
                "proposal_type": {"type": "string", "description": "提案类型"},
                "target_section": {"type": "string", "description": "目标 section"},
                "content": {"type": "string", "description": "提案内容"},
                "evidence": {"type": "string", "description": "证据"}
            },
            "required": ["proposal_type", "target_section", "content"]
        }
    },
    {
        "name": "laputa_status",
        "description": "获取 Laputa 状态",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]
```

## 5. 配置管理设计

### 5.1 配置结构

```yaml
# ~/.hermes/config.yaml
memory:
  provider: "laputa"
  laputa:
    # 存储路径
    storage_path: "~/.hermes/laputa"
    # 治理配置
    governance:
      review_enabled: true
      changelog_enabled: true
      audit_enabled: true
      rollback_window_days: 30
    # 权限配置
    permissions:
      user_can_edit: ["commitment", "preferences"]
      agent_can_edit: ["identity", "relationship", "memory_md", "history_md"]
    # mempalace 配置
    mempalace:
      db_path: "~/.hermes/laputa/palace.db"
      enable_kg: true
      enable_semantic_search: true
```

## 6. 实现路线图

### 阶段一：基础框架（1-2周）
- [ ] 创建 LaputaMemoryProvider 插件骨架
- [ ] 实现 MemoryProvider 接口
- [ ] 集成 mempalace 存储
- [ ] 基础配置管理

### 阶段二：治理层实现（2-3周）
- [ ] 实现 LaputaGovernance 类
- [ ] 实现 6 道治理流程
- [ ] 实现权限控制
- [ ] 实现审计和回滚

### 阶段三：工具接口（1-2周）
- [ ] 实现 laputa_query 工具
- [ ] 实现 laputa_update 工具
- [ ] 实现 laputa_propose 工具
- [ ] 实现 laputa_status 工具

### 阶段四：完善优化（2-3周）
- [ ] 性能优化
- [ ] 错误处理
- [ ] 文档编写
- [ ] 测试覆盖

## 7. 技术挑战与解决方案

### 7.1 Rust vs Python 实现
- **挑战**：diva 是 Rust 实现，hermes-agent 是 Python 实现
- **解决方案**：保持设计思维，用 Python 重新实现核心逻辑

### 7.2 单一 provider 限制
- **挑战**：hermes-agent 只允许一个外部 provider
- **解决方案**：Laputa 作为单一 provider，内部集成 mempalace

### 7.3 治理流程复杂度
- **挑战**：6 道治理流程实现复杂
- **解决方案**：分阶段实现，先核心后完善

### 7.4 性能优化
- **挑战**：治理层可能影响性能
- **解决方案**：异步处理、缓存机制、批量操作

## 8. 验证方案

### 8.1 单元测试
- 测试各个组件的独立功能
- 测试治理流程的正确性
- 测试权限控制的有效性

### 8.2 集成测试
- 测试与 hermes-agent 的集成
- 测试与 mempalace 的集成
- 测试端到端流程

### 8.3 性能测试
- 测试读写性能
- 测试并发处理能力
- 测试内存占用

## 9. 风险评估

### 9.1 技术风险
- **风险**：hermes-agent 架构限制
- **应对**：深入分析现有架构，寻找扩展点

### 9.2 复杂度风险
- **风险**：设计过于复杂
- **应对**：采用渐进式设计，分阶段实施

### 9.3 性能风险
- **风险**：治理层影响性能
- **应对**：优化设计，使用缓存和异步处理

## 10. 总结

本方案设计了一个完整的 Laputa 实现，作为 hermes-agent 的 MemoryProvider 插件。通过集成 mempalace 作为底层存储，保持了 diva 的治理层设计，实现了统一治理、权限分离、完整治理流程等核心目标。

方案采用分层架构，清晰分离了插件层、治理层、存储适配层和底层存储，便于维护和扩展。通过分阶段实现，可以逐步完善功能，降低风险。</think>