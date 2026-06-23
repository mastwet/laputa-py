
<!--
  Source: morediva/agent-diva-pro/.hermes/plans/laputa-py-final-architecture.md
  Consolidated to laputa-py on 2026-06-23 from morediva/.
  Authoritative canonical version lives at the source path above.
-->
# Laputa-Py 综合架构设计计划

## Context

### 项目目标
在桌面创建 `laputa-py` 文件夹，开发一个纯 Python 版本的 Laputa 治理层，集成 mempalace 作为底层存储。

### 参考项目
1. **diva-laputa (Rust)**：agent-diva-pro/agent-diva-laputa/
2. **hermes-agent**：agent-wiki/hermes-agent/agent/memory_provider.py
3. **mempalace**：agent-wiki/mempalace/mempalace/

### 设计理念
- **纯Python实现**：不依赖Rust代码
- **设计理念复用**：参考diva-laputa的设计，但独立实现
- **集成mempalace**：作为底层存储
- **MemoryProvider接口**：实现hermes-agent的插件接口

---

## 架构设计

### 1. 分层架构

```
laputa-py/
├── src/laputa/
│   ├── __init__.py
│   ├── types.py          # 核心数据类型
│   ├── error.py          # 错误类型
│   ├── metrics.py        # 指标计数器
│   ├── atomic.py         # 原子写操作
│   ├── lock.py           # 文件锁
│   ├── layout.py         # 存储布局
│   ├── proposals.py      # 提案仓库
│   ├── service.py        # 服务层
│   ├── memory_provider.py # MemoryProvider接口
│   ├── palace_bridge.py  # mempalace集成
│   ├── migration.py      # 迁移工具
│   └── cli.py            # CLI入口
├── tests/
│   ├── test_types.py
│   ├── test_proposals.py
│   ├── test_service.py
│   ├── test_memory_provider.py
│   └── test_palace_bridge.py
└── pyproject.toml
```

### 2. 核心组件

#### 2.1 数据模型 (types.py)
- `LaputaSectionName`：14个section枚举
- `ProposalType`：8种提案类型
- `ProposalState`：10个状态
- `EvolutionProposal`：提案数据结构
- `ChangelogRecord`：变更记录
- `AuditEvent`：审计事件

#### 2.2 存储层 (atomic.py, lock.py, layout.py)
- `atomic_write`：原子写操作
- `LaputaLock`：文件锁
- `LaputaPaths`：路径管理
- `LaputaStorage`：存储管理

#### 2.3 治理层 (proposals.py)
- `ProposalRepository`：提案仓库
- 6道治理流程：review → changelog → audit → lock → conflict_resolve → rollback

#### 2.4 服务层 (service.py)
- `LaputaService`：对外API门面
- 快照读取、changelog管理、rollback

#### 2.5 插件层 (memory_provider.py)
- `LaputaMemoryProvider`：实现hermes-agent的MemoryProvider接口

#### 2.6 存储适配层 (palace_bridge.py)
- `PalaceBridge`：集成mempalace作为底层存储

---

## 实现步骤

### Step 1: 项目骨架与核心类型

**创建目录**：`~/Desktop/laputa-py/`

**关键文件**：
- `src/laputa/types.py`：从 `agent-diva-core/src/evolution/types.rs` 翻译
  - `LaputaSectionName`（14个section）
  - `ProposalType`（8种）含 `target_section()` 路由
  - `ProposalState`（10个状态）含状态转换矩阵
  - `EvolutionProposal`、`ChangelogRecord`、`AuditEvent`、`RollbackRequest`

**依赖**：`pydantic`（序列化验证）

### Step 2: 存储层——原子写与文件锁

**关键文件**：
- `src/laputa/atomic.py`：从 `agent-diva-laputa/src/atomic.rs` 简化
  - `atomic_write(path, data)` = `tempfile + os.replace`
  - `atomic_write_json(path, obj)` = `json.dumps + atomic_write`

- `src/laputa/lock.py`：从 `agent-diva-laputa/src/lock.rs` 翻译
  - 用 `fcntl.flock(LOCK_EX)` 替代PID文件方案
  - context manager模式（`with Lock(path):`）

**跨平台考虑**：使用 `portalocker` 库处理Windows兼容性

### Step 3: 存储布局——LaputaPaths & LaputaStorage

**关键文件**：
- `src/laputa/layout.py`：从 `agent-diva-laputa/src/layout.rs` 翻译
  - `LaputaPaths` 类管理10个子目录路径
  - `LaputaStorage.open(workspace_root)` 创建 `.laputa/` 骨架

### Step 4: 提案仓库——状态机与治理

**关键文件**：
- `src/laputa/proposals.py`：从 `agent-diva-laputa/src/proposals.rs` 翻译核心逻辑
  - `ProposalRepository` 类：CRUD + 状态转换 + apply
  - `apply_proposal()`：6步治理链（validate -> lock -> write_section -> write_changelog -> write_audit -> update_proposal）

**状态机**：从 `proposals.rs:646-702` 翻译 `ensure_transition_allowed`

### Step 5: 服务层——LaputaService

**关键文件**：
- `src/laputa/service.py`：从 `agent-diva-laputa/src/service.rs` 翻译
  - `LaputaService`：对外API门面
  - `read_snapshot(since)`：读取14个section
  - `list_changelog(filter)`：分页读changelog
  - `rollback_changelog(id, request)`：30天回滚窗口

### Step 6: MemoryProvider接口与LaputaMemoryProvider

**关键文件**：
- `src/laputa/memory_provider.py`：实现hermes-agent的MemoryProvider ABC
  - `name = "laputa"`
  - `is_available()` 检查 `.laputa/` 存在
  - `initialize(session_id, **kwargs)`：打开LaputaService
  - `system_prompt_block()`：渲染6个authority section为markdown
  - `prefetch(query, **kwargs)`：返回空（Rust版也是Noop）
  - `sync_turn(user, assistant, **kwargs)`：返回空（Rust版也是Noop）
  - `get_tool_schemas()`：返回治理相关工具schema
  - `handle_tool_call(tool_name, args)`：分发治理操作

### Step 7: Mempalace集成层（可选）

**关键文件**：
- `src/laputa/palace_bridge.py`：轻量级mempalace集成
  - `PalaceBridge` 类：封装mempalace的search/diary_write
  - `prefetch` 时调用 `mempalace_search(query)` 做向量召回
  - `sync_turn` 时调用 `mempalace_diary_write(entry)` 写日记
  - **降级策略**：mempalace不可用时graceful skip

### Step 8: CLI与测试

**关键文件**：
- `src/laputa/cli.py`：`laputa-py init/status/proposal/rollback` 命令
- `tests/`：pytest测试覆盖核心治理流程

---

## 依赖关系

```
Step 1 (types.py)
    |
    v
Step 2 (atomic.py, lock.py)  -- 依赖types (错误类型)
    |
    v
Step 3 (layout.py)  -- 依赖atomic (atomic_write_json)
    |
    v
Step 4 (proposals.py)  -- 依赖layout + lock + types (所有底层)
    |
    v
Step 5 (service.py)  -- 依赖proposals + layout
    |
    v
Step 6 (memory_provider.py)  -- 依赖service (LaputaService)
    |
    v
Step 7 (palace_bridge.py)  -- 依赖types + layout (可选, 可并行)
    |
    v
Step 8 (cli/tests)  -- 依赖所有上层
```

---

## 风险与缓解

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| **跨平台锁差异** | 中 | 使用 `portalocker` 库（跨平台文件锁） |
| **mempalace版本不兼容** | 中 | L2设计为optional，import失败时graceful disable |
| **JSON schema漂移** | 中 | 共享schema定义（JSON Schema文件），CI中做兼容性测试 |
| **async/sync边界不匹配** | 高 | `system_prompt_block` 必须同步；其余3个方法async。Python用 `asyncio.run()` 桥接 |
| **事务回滚完整性** | 中 | Rust版用 `inspect_err` 链式回滚。Python版用try/except链实现同样逻辑 |

---

## 关键文件

| # | 文件 | 为什么关键 |
|---|------|-----------|
| 1 | `agent-diva-core/src/evolution/types.rs` (515行) | 所有核心类型的源头定义 |
| 2 | `agent-diva-laputa/src/proposals.rs` (731行) | 治理核心：提案生命周期、6步apply链、状态转换矩阵 |
| 3 | `agent-diva-laputa/src/service.rs` (740行) | 对外API门面：snapshot、changelog、rollback、event bus |
| 4 | `agent-wiki/hermes-agent/agent/memory_provider.py` (297行) | MemoryProvider ABC接口定义 |
| 5 | `agent-diva-laputa/src/memory_provider.rs` (332行) | Laputa适配器的参考实现 |

---

## 预估规模

| 模块 | 预估行数 | 对应Rust文件 |
|------|----------|-------------|
| types.py | ~300行 | types.rs (515行) |
| error.py | ~80行 | error.rs (125行) |
| metrics.py | ~40行 | metrics.rs (66行) |
| atomic.py | ~50行 | atomic.rs (88行) |
| lock.py | ~70行 | lock.rs (112行) |
| layout.py | ~100行 | layout.rs (167行) |
| proposals.py | ~400行 | proposals.rs (731行) |
| service.py | ~350行 | service.rs (740行) |
| memory_provider.py | ~200行 | memory_provider.rs (332行) |
| **总计** | **~1,590行** | **~2,876行** |

Python版预计为Rust版的~55%行数，主要缩减来自：无显式类型标注开销、dataclass比struct简洁、无需lifetime/ownership注解。

---

## 验证方案

### 单元测试
- 测试各个组件的独立功能
- 测试治理流程的正确性
- 测试权限控制的有效性

### 集成测试
- 测试与hermes-agent的集成
- 测试与mempalace的集成
- 测试端到端流程

### 性能测试
- 测试读写性能
- 测试并发处理能力
- 测试内存占用

---

## 总结

本方案设计了一个完整的纯Python版Laputa实现，通过集成mempalace作为底层存储，保持了diva的治理层设计，实现了统一治理、权限分离、完整治理流程等核心目标。

**关键决策**：
- 纯Python实现，不依赖Rust代码
- 设计理念复用diva-laputa，但独立实现
- 集成mempalace作为底层存储
- 实现完整的6道治理流程
- 预估~1,590行Python代码