# TODOLIST

## Completed

- [x] 任务1：完善6道治理流程 - 添加冲突解决逻辑
  - 在 `proposals.py` 中添加了 `_has_potential_conflict` 方法
  - 在 `_apply_proposal_internal` 中添加了冲突检测逻辑（Step 2.5）

- [x] 任务2：添加 Section 写入能力（write_section 方法）
  - 在 `service.py` 添加 `write_section` 方法
  - 实现权限检查：`#3 commitment` 和 `#4 preferences` 可直改，其他需要走 proposal flow
  - 记录 changelog 和 audit

- [x] 任务3：完善 Changelog 查询（get_changelog 方法）
  - 在 `service.py` 添加 `get_changelog(changelog_id)` 方法
  - 返回完整的 ChangelogRecord

- [x] 任务4：添加基础测试
  - `tests/test_governance.py` - 6道治理流程测试 (7 tests)
  - `tests/test_section_write.py` - Section 写入测试 (9 tests)
  - `tests/test_changelog.py` - Changelog 查询测试 (9 tests)
  - `tests/test_service.py` - Service 集成测试 (11 tests)
  - `tests/test_types.py` - 类型测试 (4 tests)

## Pending

- [ ] HTTP API 层
- [ ] 事件接口
- [ ] Mentle 集成
