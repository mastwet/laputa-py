---
title: "Laputa 设计文档索引"
date: 2026-06-23
status: consolidated (从 morediva/ 整理而来,只搬设计态,实现 task 留原处)
scope: laputa-py 的设计基线、架构、调研、PRD 调和、legacy 替代关系
source_root: morediva/ (agent-diva-pro 为主,agent-diva-selfinprove / diva-dev-ultra 为辅)
consolidated_on: 2026-06-23
---

# Laputa 设计文档索引

> 这个目录把散落在 `morediva/` 多个项目里的 **laputa 相关设计文档**集中到 laputa-py。每个文件顶部的 HTML 注释标了来源路径,原路径仍是**权威版本**;这里只是为了**集中查阅 + 跨项目追溯**。

## 0. 怎么读(5 分钟 / 30 分钟 / 2 小时)

| 你想了解什么 | 先看哪几份 |
|---|---|
| **Laputa 到底是什么** | `baseline/LAPUTA.md` (5 min) |
| **Mentle 跟 Laputa 怎么分工** | `baseline/MENTLE.md` (10 min) |
| **Harness Engineering 哲学** | `research/hermes-harness-overview.md` (15 min) |
| **laputa-py 怎么从 Rust 迁到 Python** | `architecture/laputa-py-final-architecture.md` + `architecture/laputa-python-implementation-plan.md` (20 min) |
| **为什么有 legacy/ 和 baseline/ 两套** | `legacy/laputa-new-architecture.md` 跟 `baseline/LAPUTA.md` 对照读 (30 min) |
| **完整设计 lineage** | 按下面的时间线顺序通读 (2 h) |

## 1. 目录结构

```
docs/
├── baseline/      # 2 份 — 权威基线索引(2026-06-12 / 2026-06-20)
├── architecture/  # 3 份 — laputa-py 专属架构 + 实现计划(2026-06-21)
├── research/      # 5 份 — Harness Engineering 哲学 + alife 调研(2026-06-18~20)
├── prds/          # 7 份 — PRD-laputa 2026-06-12 主线 + 自检评审(2026-06-12)
└── legacy/        # 7 份 — 替代/前置设计(2026-03~05,已被基线取代)
```

## 2. 主题地图

### 2.1 baseline/ — **基线索引(权威)**

当前 Laputa / Mentle 设计的**锚点文档**。设计态,不是实现态。

| 文件 | 版本 / 日期 | 角色 |
|---|---|---|
| `LAPUTA.md` | v0.0.6 final, 2026-06-12 | Laputa 架构索引:1 稀薄文档层 + 14 content section + 4 接口 + 6 治理 |
| `MENTLE.md` | v0.2, 2026-06-20 | Mentle 架构索引:跟 LAPUTA.md 平级,补全 + Session-End 治理正式化 |

### 2.2 architecture/ — **laputa-py 架构与实现计划**

从 Rust `agent-diva-laputa` 迁到纯 Python `laputa-py` 的设计稿。

| 文件 | 日期 | 角色 |
|---|---|---|
| `laputa-py-final-architecture.md` | 2026-06-21 | laputa-py 综合架构(分层 + MemoryProvider 接口 + mempalace 集成) |
| `laputa-python-implementation-plan.md` | 2026-06-21 | 实施计划(milestone / 任务拆分) |
| `laputa-hermes-architecture.md` | 2026-06-21 | laputa ↔ hermes-agent 集成架构(MemoryProvider 插件接口) |

### 2.3 research/ — **Harness Engineering 与 alife 调研**

Laputa 设计的**哲学根**:Model=CPU / Context=RAM / Harness=OS / Agent=App。

| 文件 | 日期 | 角色 |
|---|---|---|
| `hermes-harness-overview.md` | 2026-06-20 | hermes-agent 作为 harness 的全景调研 |
| `harness-engineering-three-way-comparison.md` | 2026-06-19 | 三方对比:alife / hermes / 现有 diva-pro |
| `harness-engineering-three-way-detailed-checklist.md` | 2026-06-19 | 21 维度逐项对比 checklist |
| `alife-harness-overview.md` | 2026-06-19 | alife 项目作为 harness 蓝本 |
| `alife-harness-gap-inventory.md` | 2026-06-19 | alife ↔ diva-pro 差距清单 |

### 2.4 prds/ — **PRD-laputa 2026-06-12 主线 + 自检评审**

PRD 主体在 `morediva/agent-diva-pro/docs/prds/prd-laputa-2026-06-12/prd.md`(没搬,留原处);这里搬的是**调和 + 评审**。

| 文件 | 角色 |
|---|---|
| `reconcile-laputa-new-architecture.md` | IR-1:把"新 Laputa 架构"(legacy/)调和进 v0.0.6 baseline |
| `reconcile-mentle-laputa.md` | IR-2:把"mentle-laputa memory role decision"(legacy/)调和进 LAPUTA/MENTLE 边界 |
| `reconcile-auto-evolution.md` | IR-3:AutoDream 跟 Laputa 写入边界调和 |
| `reconcile-laputa-v006.md` | 来自 selfinprove PRD:从 selfinprove 视角对 v0.0.6 的承接 |
| `review-rubric.md` / `review-adversarial.md` / `review-edge-case.md` | PRD 的三方自检(评分 / 反对意见 / 边缘情况) |

### 2.5 legacy/ — **前置与替代设计(lineage,已不适用)**

读这些是为了**理解设计怎么演进来的**;不要当作当前基线。

| 文件 | 日期 | 角色 |
|---|---|---|
| `laputa-new-architecture.md` | 2026-05-28 | "新 Laputa 架构" — 7 文件 / 三轴主体性 / 进阶心跳。**被 v0.0.6 baseline 取代** |
| `mentle-laputa-memory-role-decision.md` | 2026-05-31 | Mentle ↔ Laputa 角色分工的 295 行 accepted 决策。**被 MENTLE.md v0.2 + reconcile-mentle-laputa 吸收** |
| `2026-03-26-agent-diva-integrated-memory-design.md` | 2026-03-26 | 早期"集成 memory 设计"。**已被 v0.0.6 取代** |
| `mentle-runtime-assembly.md` | 2026-05~06 | Mentle 运行时装配(16-s3-a4-a6) |
| `mentle-feature-build-env.md` | 2026-05~06 | Mentle feature build env(22-s4-a10) |
| `mentle-tool-selection-and-gui-controls.md` | 2026-05~06 | Mentle 工具选型 + GUI 控件(25-s7-a1) |
| `mentle-early-snapshot.md` | 更早 | diva-dev-ultra 时代的 Mentle 模块描述(最早的快照) |

## 3. 时间线(2026-03 → 2026-06)

```
2026-03-26  legacy/2026-03-26-agent-diva-integrated-memory-design.md
            └─ 早期 "集成 memory" 思路

2026-05-xx  legacy/mentle-early-snapshot.md
            └─ diva-dev-ultra 时代 Mentle 模块

2026-05-28  legacy/laputa-new-architecture.md
            └─ "新 Laputa 架构" (7 文件 + 三轴主体性) — 后被取代
2026-05-31  legacy/mentle-laputa-memory-role-decision.md
            └─ Mentle ↔ Laputa 角色分工 accepted

2026-06-12  baseline/LAPUTA.md  v0.0.6 final  ← 当前权威
            prds/reconcile-* / review-*
            └─ PRD 主体在原 morediva 路径(prd-laputa-2026-06-12/prd.md)

2026-06-18  research/alife-* (harness engineering 三方对比起点)

2026-06-19  research/harness-engineering-three-way-*
            └─ 21 维度逐项 checklist

2026-06-20  baseline/MENTLE.md  v0.2            ← 与 LAPUTA.md 平级权威
            research/hermes-harness-overview.md

2026-06-21  architecture/laputa-{py-final,hermes,python-implementation}-*.md
            └─ laputa-py 完整架构与实现计划

2026-06-23  (今天)  本索引 — 把以上 24 份设计文档集中到 laputa-py
```

## 4. 没搬的(故意排除)

为了让 `docs/` 主题聚焦,**没有搬**以下文件 — 它们不在"laputa 设计"主题,或属于实现层:

- `morediva/agent-diva-pro/_bmad-output/implementation-artifacts/*` — **实现 task 拆解**(1-1 到 6-5),不是设计
- `morediva/agent-diva-pro/.hermes/plans/hermes-diva-integration-{deep,summary,research*,collection}.md` — **Hermes 全集成**(比 laputa 范围广)
- `morediva/agent-diva-pro/.hermes/plans/mempalace-correct-analysis.md` — **Mempalace 存储层**(laputa 的依赖,但本身不是 laputa 设计)
- `morediva/agent-diva-pro/.hermes/plans/distributed-doodling-napier.md` — **后台任务队列**(跟 laputa 主题无关)
- `morediva/agent-diva-pro/.hermes/plans/2026-06-10_*-comprehensive-code-review.md` — **代码评审**(不是设计)
- 其它 `agent-diva-*/docs/dev/archive(old-docs-dont-read-me)/` 下跟 laputa 无关的目录

## 5. 维护约定

- **每个文件顶部 HTML 注释**标了 `Source: morediva/<原路径>`,权威版本仍在原处
- **基线变更**:改 `baseline/LAPUTA.md` 或 `baseline/MENTLE.md` 之前,**先在 `prds/` 起一份 reconcile 文档**说明差异,再回写基线
- **新设计文档**:放进 `research/` 或 `prds/`(看是调研还是 PRD 调和);不要直接动 `baseline/`
- **legacy/ 不更新**:只读,不写。如果发现 legacy 某份比 baseline 还新,那是文档漂移,先在 prds/ 修基线
