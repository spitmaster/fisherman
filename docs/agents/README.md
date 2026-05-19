# Agents 目录

> 项目内 agent 一览。真相源 [SPEC.md](../SPEC.md);项目层契约 [fisherman-overview.md](./fisherman-overview.md)。

---

## Fisherman 专属 Agents

Windows 桌面端的 YOLOv8 视觉自动化工具。技术栈:Python + PyQt5 + PyTorch CPU + Ultralytics YOLO + SQLAlchemy/SQLite + mss + pyautogui。

| 文档 | 说明 |
| ---- | ---- |
| [fisherman-overview.md](./fisherman-overview.md) | 项目层文档:agent 角色映射、共享契约、架构不变量、里程碑路径 |
| [fisherman-orchestrator.md](./fisherman-orchestrator.md) | 项目主调度:任务拆解、契约对齐、全局联调 |
| [yolo-training-engineer.md](./yolo-training-engineer.md) | YOLOv8 训练管道(executor / trainer / callbacks / result saver) |
| [screen-recognition-engineer.md](./screen-recognition-engineer.md) | 屏幕识别(mss 截图 + YOLO 推理 + pyautogui 点击 + FPS 优化) |
| [pyqt5-ui-developer.md](./pyqt5-ui-developer.md) | PyQt5 主窗口 + Tabs + Dialogs + 跨线程信号槽 |
| [sqlalchemy-db-engineer.md](./sqlalchemy-db-engineer.md) | SQLAlchemy ORM + SQLite schema + migration + 索引 |
| [task-scheduler-engineer.md](./task-scheduler-engineer.md) | TaskScheduler + 优先级队列 + 线程模型 + 优雅关闭 |
| [annotation-tool-engineer.md](./annotation-tool-engineer.md) | 标注子系统(Strategy 校验 + YOLO 格式 + 批量) |

任务路由表见 [fisherman-overview.md](./fisherman-overview.md#路由表) 或项目根 [CLAUDE.md](../../CLAUDE.md#agent-体系)。

---

## 通用领域 Agents(跨项目复用)

下列 agent 定义的是**领域能力**,不绑定具体项目;Fisherman 在需要时通过 orchestrator 调用。

| Agent | 能力 |
| ----- | ---- |
| [static-code-analyzer](./static-code-analyzer.md) | 静态代码分析:AST、符号表、调用图、框架识别 |
| [fixture-validator](./fixture-validator.md) | 测试夹具构建 + 端到端准确性回归 |
| [spec-docs-curator](./spec-docs-curator.md) | 文档/规范的维护与同步(SPEC ↔ 代码) |

---

## 添加新的 Agent

1. 在本目录创建 `{agent-name}.md`,遵循模板(下方)
2. 在上面 Fisherman 表或通用表加一行
3. 如果是项目专属,同步更新 [fisherman-overview.md](./fisherman-overview.md) 的角色映射与路由表
4. 同步更新项目根 [CLAUDE.md](../../CLAUDE.md#agent-体系) 的路由表

### Agent 文件模板

```markdown
---
name: agent-name
description: 一句话角色描述
model: opus | sonnet | haiku
color: blue | green | ...
---

# {Agent 名称}

## 角色

## 专业领域

## 工作流程

## 输出格式
```
