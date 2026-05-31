# Fisherman — 里程碑主索引

> 三档规划的**中粒度**:单功能里程碑 (M)。周级更新。
> 粗粒度路线图见 [roadmap.md](./roadmap.md);具体待办见 `docs/todo/<branch>.md`。
> 三档晋升规则见 [CLAUDE.md](../CLAUDE.md#三档晋升表) 与全局 ~/.claude/CLAUDE.md §2.2。

---

## 文件组织

- 本文件**只做索引**(进行中 + 已归档),不写 M 详情
- 每个 active 分支独占一份 `docs/milestones/<branch with / → _>.md`
- 分支与文件的机械映射规则:全局 ~/.claude/CLAUDE.md §5.1

---

## 进行中

> 按时间倒序,最新在最上面。每行 ≤ 120 字符。

| 分支 | 当前 M | Milestone 文件 | Todo 文件 |
|------|--------|----------------|-----------|
| `20260204` | M7 钓鱼后台模式(M6 独立 exe 待干净 Windows E2E) | [milestones/20260204.md](./milestones/20260204.md) | [todo/20260204.md](./todo/20260204.md) |

---

## 已归档

> 按归档时间倒序。每个完工的 feature 一行,链接到 `archive/` 路径。

(暂无)

---

## 维护规则

- 启动新功能:`roadmap.md` 标"⏳ 进行中" + 本表"进行中"区加一行 + 创建 `milestones/<branch>.md` + `todo/<branch>.md`
- M 完结:`milestones/<branch>.md` 那行标 ✅ + commit + 日期;`todo/<branch>.md` 清空开下一个 M
- 功能完结:`git mv milestones/<branch>.md milestones/archive/<branch>.md`;本表中行从"进行中"挪到"已归档";`todo/<branch>.md` 删除;`roadmap.md` 加版本行
