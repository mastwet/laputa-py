
<!--
  Source: morediva/diva-dev-ultra/docs/core-modules/mentle.md
  Consolidated to laputa-py on 2026-06-23 from morediva/.
  Authoritative canonical version lives at the source path above.
-->
# Mentle 集成 — 混合记忆与嵌入式运行时

> **模块位置**: `agent-diva-core/src/memory/hybrid.rs` · `agent-diva-agent/src/mentle_runtime.rs` ·
> `agent-diva-agent/src/mentle_discovery.rs` · `agent-diva-agent/src/tool_config/mentle.rs`
>
> 本文档面向有 Python / JavaScript 背景的开发者，详解 Agent-Diva 的 Mentle 集成：
> 混合记忆架构、嵌入式运行时、工具注册与配置管理。

---

## 1. 什么是 Mentle？

Mentle 是一个**嵌入式长期记忆数据库**，基于 SQLite/Turso 技术栈，
提供结构化的"记忆宫殿"（Memory Palace）存储能力。

类比：如果你熟悉 Python 的 `sqlite3` 模块或 JavaScript 的 `better-sqlite3`，
那么 Mentle 就是 Agent-Diva 专用的"记忆数据库 + 工具包"。

### 核心概念

- **Palace（宫殿）**: Mentle 数据库实例，存储在 `workspace/memory/palace.db`
- **Wing（翼楼）**: 记忆的顶级分类（如 `history`、`project`、`personal`）
- **Room（房间）**: Wing 下的子分类
- **Drawer（抽屉）**: 具体的记忆条目
- **Graph（图谱）**: Room 之间的关联关系

### 重要命名说明

> 代码中使用 **Mentle** / **MemtleToolkit** 命名，而非 "Laputa"。
> 工具名称前缀为 `memtle_`（注意拼写差异）。

---

## 2. Feature Gate — 编译时条件

Mentle 集成完全由 `mentle` feature gate 控制：

```rust
// agent-diva-core/src/memory/hybrid.rs 注释说明
//! This module is only compiled with the `mentle` feature. The default core
//! build keeps using file-backed memory and does not depend on `memtle`.
```

### 编译方式

```bash
# 启用 Mentle feature 编译
cargo check -p agent-diva-agent --features mentle

# Windows 环境需要 clang-cl.exe
# 如果 LLVM 安装在 C:\Program Files\LLVM\bin，需要确保在 PATH 中
```

### 条件编译示例

```rust
// mentle_discovery.rs
pub const fn mentle_discovery_available() -> bool {
    cfg!(feature = "mentle")
}

pub async fn discover_mentle_tool_names(workspace: &Path) -> Vec<String> {
    #[cfg(feature = "mentle")]
    {
        return crate::mentle_runtime::discover_mentle_tool_names(workspace).await;
    }
    #[cfg(not(feature = "mentle"))]
    {
        let _ = workspace;
        Vec::new()  // 未启用时返回空列表
    }
}
```

---

## 3. HybridMemoryProvider — 混合记忆架构

`HybridMemoryProvider` 是记忆系统的核心，将**文件记忆**与**Mentle 数据库**
组合为统一的记忆提供者。

### 3.1 记忆分层

```text
┌─────────────────────────────────────────────┐
│             HybridMemoryProvider            │
├──────────────┬──────────────────────────────┤
│  L0/L1 层    │         L2 层               │
│  文件记忆     │       Mentle 宫殿           │
│              │                              │
│  MEMORY.md   │   palace.db (SQLite)        │
│  HISTORY.md  │   ├─ Wing: history          │
│  .agent-diva │   │  ├─ Room: diary         │
│   /memory/   │   │  └─ Room: facts         │
│              │   └─ Wing: project          │
│              │      └─ Room: roadmap       │
├──────────────┴──────────────────────────────┤
│           MemoryProvider trait              │
│  system_prompt_block()  prefetch()          │
│  sync_turn()           on_session_end()     │
└─────────────────────────────────────────────┘
```

### 3.2 内部结构

```rust
pub struct HybridMemoryProvider {
    file_manager: Arc<MemoryManager>,                    // L0/L1 文件记忆
    palace_toolkit: Arc<Mutex<MemtleToolkit>>,           // L2 Mentle 工具包
    palace_snapshot: RwLock<CachedPalaceSnapshot>,       // 宫殿状态缓存
}
```

### 3.3 PalaceStatusSnapshot — 宫殿状态快照

```rust
struct PalaceStatusSnapshot {
    total_drawers: i64,    // 抽屉（记忆条目）总数
    rooms_total: usize,    // 房间总数
    edges_total: usize,    // 关联边总数
}
```

快照有三种状态：

```rust
enum PalaceSnapshotState {
    Ready(PalaceStatusSnapshot),          // 正常：数据新鲜
    Stale {                               // 过期：有旧数据但刷新失败
        snapshot: PalaceStatusSnapshot,
        last_refresh_error: String,
    },
    Degraded { reason: String },          // 降级：从未成功获取数据
}
```

状态转换逻辑：

```text
启动成功 → Ready
启动失败 → Degraded
Ready + 刷新失败 → Stale（保留旧数据）
Stale + 刷新成功 → Ready
Stale + 刷新失败 → Stale（更新错误信息）
Degraded + 刷新成功 → Ready
Degraded + 刷新失败 → Degraded（更新原因）
```

---

## 4. MemoryProvider 接口实现

### 4.1 system_prompt_block — 系统提示词注入

在 Agent 启动时，将记忆信息注入系统提示词：

```rust
fn system_prompt_block(&self, request: &SystemPromptRequest)
    -> Result<SystemPromptResponse>
{
    // 1. 获取文件记忆（MEMORY.md 等）
    let file_response = self.file_manager.system_prompt_block(request)?;
    let file_markdown = /* ... */;

    // 2. 获取宫殿状态
    let palace_snapshot = self.palace_snapshot.read();
    let palace_markdown = palace_snapshot.render_markdown();

    // 3. 合并两部分
    let markdown = [file_markdown, palace_markdown]
        .filter(|s| !s.is_empty())
        .join("\n\n");

    // 4. 如果两者都不可用，返回降级状态
    if !file_available && !palace_available {
        return Ok(SystemPromptResponse::degraded("..."));
    }

    Ok(SystemPromptResponse::ready(SystemPromptBlock {
        shape: StartupInjectionShape::CompactRenderedMarkdown,
        markdown,
    }))
}
```

注入到系统提示词中的内容示例：

```markdown
## Memory Palace Overview
- snapshot_status: ready
- active_drawers: 42
- graph_rooms: 15
- graph_tunnels: 23
```

### 4.2 prefetch — 深度回忆预取

在用户消息到达前，根据意图预取相关记忆：

```rust
async fn prefetch(&self, request: PrefetchRequest) -> Result<PrefetchResponse> {
    // 跳过空白意图
    if request.intent.trim().is_empty() {
        return Ok(PrefetchResponse { status: SkippedNoIntent, ... });
    }

    // 在宫殿中搜索
    let args = memtle::tools::SearchArgs {
        query: request.intent.clone(),
        limit: 5,
        wing: None,
        room: request.current_room.clone(),
        context: request.user_message.clone(),
    };

    match toolkit.search(args).await {
        Ok(output) => {
            // 渲染为 Markdown
            let mut markdown = format!("## Palace Deep Recall\nQuery: {}\n", request.intent);
            for item in output.results {
                markdown.push_str(&format!("- [{}/{}] {}\n",
                    item.wing, item.room, item.content));
            }
            Ok(PrefetchResponse { status: Ready, prompt_block: Some(markdown) })
        }
        Err(err) => Ok(PrefetchResponse { status: Failed { reason: err.to_string() }, ... })
    }
}
```

预取结果注入示例：

```markdown
## Palace Deep Recall
Query: provider boundary startup prompt
- [project/roadmap] Provider boundary work keeps startup prompt assembly synchronous.
- [project/decisions] Decided to keep provider abstraction in agent-diva-core.
```

### 4.3 sync_turn — 轮次同步

每轮对话结束后，同步记忆到文件和宫殿：

```rust
async fn sync_turn(&self, request: SyncTurnRequest) -> Result<SyncTurnResponse> {
    // 1. 保存 MEMORY.md 更新
    if let Some(memory_update) = request.memory_update_markdown {
        self.file_manager.save_memory(&Memory::with_content(memory_update))?;
    }

    // 2. 追加 HISTORY.md + 写入宫殿日记
    if let Some(history_entry) = request.history_entry {
        self.file_manager.append_history(history_entry)?;

        // 同步写入 Mentle 宫殿
        let result = toolkit.call_json("memtle_diary_write",
            json!({
                "agent_name": "agent-diva",
                "entry": history_entry,
                "topic": "history",
                "wing": "history"
            })
        ).await;

        match result {
            Ok(value) if diary_write_succeeded(&value) => {
                // 写入成功，刷新宫殿快照
                self.refresh_palace_snapshot().await;
            }
            Ok(value) | Err(err) => {
                // 失败时记录警告，但不影响主流程
                // HISTORY.md 仍然是权威数据源
                tracing::warn!("failed to persist Mentle diary entry; HISTORY.md remains authoritative");
            }
        }
    }
}
```

> **容错设计**: Mentle 写入失败不会阻断主流程。
> `HISTORY.md`（文件记忆）始终是权威数据源。

### 4.4 on_session_end — 会话结束

会话结束时的处理由文件记忆层管理，Mentle 层透传调用。

---

## 5. MentleRuntime — 嵌入式运行时组装

`MentleRuntime` 负责在 AgentLoop 启动时组装 Mentle 的所有组件。

### 5.1 初始化流程

```rust
// agent-diva-agent/src/mentle_runtime.rs
pub(super) async fn try_build(
    workspace: &Path,
    tool_config: &MentleToolRuntimeConfig,
) -> Option<Self> {
    // 1. 检查是否需要启用 Mentle
    if !tool_config.is_active_request() {
        return None;
    }

    // 2. 打开宫殿数据库
    let db_path = workspace.join("memory").join("palace.db");
    let toolkit = memtle::toolkit::MemtleToolkit::open(&db_path).await?;

    // 3. 创建混合记忆提供者
    let toolkit = Arc::new(Mutex::new(toolkit));
    let file_manager = Arc::new(MemoryManager::new(workspace));
    let memory_provider = Arc::new(
        HybridMemoryProvider::new(file_manager, toolkit.clone()).await
    );

    // 4. 发现并过滤 Mentle 工具
    let tool_defs = toolkit.lock().await.tool_definitions();
    let custom_tools = filter_mentle_tools(
        mentle_tools_from_definitions(tool_defs, toolkit.clone()),
        tool_config,
    );

    Some(Self { toolkit, memory_provider, custom_tools })
}
```

### 5.2 MentleRuntime 结构

```rust
pub(super) struct MentleRuntime {
    toolkit: Arc<Mutex<memtle::toolkit::MemtleToolkit>>,  // 工具包
    memory_provider: Arc<dyn MemoryProvider>,              // 记忆提供者
    custom_tools: Vec<Arc<dyn Tool>>,                      // 注册的工具
    active: bool,                                          // 是否激活
}
```

`active` 标志通过检查 `memtle_status` 工具是否存在来确定：

```rust
fn from_parts(...) -> Self {
    let active = custom_tools.iter()
        .any(|tool| tool.name() == "memtle_status");
    Self { toolkit, memory_provider, custom_tools, active }
}
```

---

## 6. Mentle 工具发现与注册

### 6.1 工具发现

Mentle 工具通过 `MemtleToolkit::tool_definitions()` 动态发现：

```rust
pub(super) fn mentle_tools_from_definitions(
    tool_defs: impl IntoIterator<Item = serde_json::Value>,
    toolkit: Arc<Mutex<MemtleToolkit>>,
) -> Vec<Arc<dyn Tool>> {
    let mut tools = Vec::new();
    for def in tool_defs {
        if let Some(tool) = mentle_tool_from_definition(&def, toolkit.clone()) {
            tools.push(tool);
        }
    }
    tools
}
```

### 6.2 工具定义解析

每个工具定义是一个 JSON 对象，需要包含 `name`、`description`、`inputSchema`：

```rust
pub(super) fn mentle_tool_metadata_from_definition(
    def: &serde_json::Value,
) -> Option<(String, String, serde_json::Value)> {
    let name = def.get("name")?.as_str()?;
    let description = def.get("description")?.as_str()?;
    let parameters = def.get("inputSchema")?;  // 必须是 object
    Some((name.to_string(), description.to_string(), parameters.clone()))
}
```

### 6.3 MentleToolkitTool — 工具适配器

将 Mentle 工具定义适配为 Agent-Diva 的 `Tool` trait：

```rust
pub(super) struct MentleToolkitTool {
    pub(super) name: String,
    pub(super) description: String,
    pub(super) parameters: serde_json::Value,
    pub(super) toolkit: Arc<Mutex<MemtleToolkit>>,
}

#[async_trait]
impl Tool for MentleToolkitTool {
    fn name(&self) -> &str { &self.name }
    fn description(&self) -> &str { &self.description }
    fn parameters(&self) -> serde_json::Value { self.parameters.clone() }

    async fn execute(&self, args: serde_json::Value) -> Result<String> {
        let toolkit = self.toolkit.lock().await;
        let result = toolkit.call_json(&self.name, args).await?;
        // 返回字符串结果
        if let Some(text) = result.as_str() {
            Ok(text.to_string())
        } else {
            serde_json::to_string_pretty(&result)
        }
    }
}
```

### 6.4 常见 memtle_* 工具

| 工具名 | 类型 | 说明 |
|--------|------|------|
| `memtle_status` | 只读 | 查询宫殿状态（抽屉数、房间数等） |
| `memtle_search` | 只读 | 在宫殿中搜索记忆 |
| `memtle_diary_write` | 写入 | 写入日记条目 |
| `memtle_add_drawer` | 写入 | 添加新的记忆抽屉 |
| `memtle_add_room` | 写入 | 添加新的房间 |

---

## 7. MentleToolRuntimeConfig — 工具配置

### 7.1 MentleToolMode — 工具模式

```rust
pub enum MentleToolMode {
    Off,       // 完全禁用
    ReadOnly,  // 只读模式：只允许 memtle_status 和 memtle_search
    Full,      // 完全模式：允许所有 memtle_* 工具
    Custom,    // 自定义模式：只允许 allowed_tools 列表中的工具
}
```

### 7.2 MentleToolRuntimeConfig

```rust
pub struct MentleToolRuntimeConfig {
    pub enabled: bool,                 // 是否启用
    pub mode: MentleToolMode,          // 工具模式
    pub allowed_tools: Vec<String>,    // Custom 模式下的允许工具列表
}
```

### 7.3 工具过滤逻辑

```rust
pub fn allows_tool(&self, name: &str) -> bool {
    if !name.starts_with("memtle_") {
        return false;  // 只处理 memtle_ 前缀的工具
    }
    match self.mode {
        MentleToolMode::Off => false,
        MentleToolMode::ReadOnly => READ_ONLY_TOOLS.contains(&name),
        // READ_ONLY_TOOLS = ["memtle_status", "memtle_search"]
        MentleToolMode::Full => true,
        MentleToolMode::Custom => self.allowed_tools
            .iter()
            .any(|allowed| allowed == name && allowed.starts_with("memtle_")),
    }
}
```

### 7.4 配置来源

配置可以从 `Config` 对象派生，并自动处理 `tools.builtin.mentle` 兼容：

```rust
pub fn from_config(config: &Config) -> Self {
    let mut runtime = Self::from_core(&config.mentle);
    // 兼容旧配置：如果 mentle 配置为默认关闭但 tools.builtin.mentle 为 true
    if runtime.is_default_off() && config.tools.builtin.mentle {
        runtime.enabled = true;
        runtime.mode = MentleToolMode::Full;
    }
    runtime
}
```

### 7.5 配置示例

```yaml
# config.yaml
mentle:
  enabled: true
  mode: "full"           # off | read_only | full | custom
  allowed_tools: []       # 仅在 mode=custom 时生效

# 或使用旧格式
tools:
  builtin:
    mentle: true
```

---

## 8. 错误处理与容错

Mentle 运行时实现了完善的错误分类和降级策略：

### 8.1 错误阶段

```rust
enum MentleErrorPhase {
    StartupOpen,        // 启动时打开数据库
    ToolDefinition,     // 解析工具定义
    ToolCallTransport,  // 工具调用传输层
    ToolCallPayload,    // 工具调用返回值
}
```

### 8.2 错误分类

```rust
enum MentleErrorCategory {
    Io,                // I/O 错误
    Database,          // 数据库错误
    Json,              // JSON 解析错误
    Config,            // 配置错误
    InvalidArguments,  // 参数错误
    UnknownTool,       // 未知工具
    NotFound,          // 未找到
    InvalidDefinition, // 无效工具定义
    ToolPayload,       // 工具返回值错误
    Internal,          // 内部错误
}
```

### 8.3 降级策略

```rust
enum MentleFallbackAction {
    DisableMentle,     // 完全禁用 Mentle（启动失败时）
    SkipTool,          // 跳过单个无效工具定义
    ReturnToolError,   // 返回工具执行错误给 Agent
}
```

### 8.4 典型降级场景

```text
场景 1: 数据库打开失败
  → DisableMentle → Agent 继续使用纯文件记忆

场景 2: 单个工具定义无效
  → SkipTool → 跳过该工具，其他工具正常注册

场景 3: 工具执行失败
  → ReturnToolError → Agent 收到错误信息，可以重试或换策略
```

---

## 9. Mentle 对系统提示词的影响

当 Mentle 启用时，系统提示词会发生以下变化：

### 9.1 启动时注入宫殿概览

```markdown
## Memory Palace Overview
- snapshot_status: ready
- active_drawers: 42
- graph_rooms: 15
- graph_tunnels: 23
```

### 9.2 预取时注入深度回忆

```markdown
## Palace Deep Recall
Query: 用户的意图摘要
- [wing/room] 相关记忆内容 1
- [wing/room] 相关记忆内容 2
- No deep factual memories recalled.  （无匹配时）
```

### 9.3 轮次结束时自动同步

- `MEMORY.md` 更新 → 文件记忆
- `HISTORY.md` 追加 → 文件记忆 + Mentle 双写
- Mentle 写入失败时回退到仅文件记忆

---

## 10. 代码中的命名约定

| 概念 | 代码中的名称 | 说明 |
|------|-------------|------|
| 记忆数据库 | `palace.db` | SQLite 文件 |
| 工具包 | `MemtleToolkit` | 核心工具接口 |
| 工具前缀 | `memtle_*` | 所有工具名以此开头 |
| 混合提供者 | `HybridMemoryProvider` | 组合文件 + 宫殿 |
| 运行时 | `MentleRuntime` | AgentLoop 内部组装 |
| 配置 | `MentleToolRuntimeConfig` | 工具模式与过滤 |
| 发现 | `mentle_discovery` | 配置 UI 的工具发现 |

> **注意**: 代码中 "Mentle" 和 "Memtle" 的拼写差异是有意为之的。
> `MemtleToolkit` 是库名称，`Mentle` 是功能模块名称。

---

## 11. 源码索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `agent-diva-core/src/memory/hybrid.rs` | 961 | HybridMemoryProvider、PalaceSnapshot、MemoryProvider 实现 |
| `agent-diva-agent/src/mentle_runtime.rs` | 456 | MentleRuntime 组装、MentleToolkitTool 适配器、错误处理 |
| `agent-diva-agent/src/mentle_discovery.rs` | 23 | 工具发现入口（条件编译包装） |
| `agent-diva-agent/src/tool_config/mentle.rs` | 139 | MentleToolRuntimeConfig、MentleToolMode、工具过滤 |
