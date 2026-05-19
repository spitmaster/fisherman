# Agents 目录

> 存放预定义的 Agent 定义

---

## 目录说明

本目录存放各种预定义的 Agent，每个 Agent 是一个专业角色。

---

## 添加新的 Agent

创建新 agent 文件，命名规范：`{agent-name}.md`

```markdown
# {Agent 名称}

## 角色
描述这个 agent 是什么角色

## 专业领域

## 触发词
- `召唤 {agent}`
- `使用 {agent}模式`
- `{关键词}`

## 工作流程

## 系统提示

## 工具权限

## 输出格式
```

---

## 现有 Agents

| Agent | 说明 |
|-------|------|
| SDD-Architect | 架构师，分析需求生成 SPEC |
| SDD-Developer | 开发者，按 SPEC 开发 |
| SDD-Reviewer | 审查员，代码审查 |
| SDD-Validator | 验证师，检查完整性 |
| SDD-Diagnoser | 诊断师，项目诊断 |

详情见 `docs/ai-config/for-codebuddy.md`

---

## 通用领域 Agents(跨项目复用)

这些 agent 定义的是**领域能力**,不绑定具体项目。被具体项目调用时,通过该项目的 orchestrator + overview 注入项目特定的契约/schema。

| Agent | 能力 |
| ----- | ---- |
| [static-code-analyzer](./static-code-analyzer.md) | 静态代码分析:AST、符号表、调用图、框架识别 |
| [io-entry-mapper](./io-entry-mapper.md) | IO 入口识别:HTTP / 前端事件 / CLI / 队列 / cron |
| [dataflow-tracer](./dataflow-tracer.md) | 单入口数据流追踪(含 ORM / 跨进程边) |
| [business-translator](./business-translator.md) | 代码到中文业务语言的 LLM 翻译(evidence + 置信度) |
| [3d-rendering-engineer](./3d-rendering-engineer.md) | Three.js / R3F 3D 场景渲染与流水动画 |
| [3d-interaction-designer](./3d-interaction-designer.md) | 3D 空间内的导航、聚焦、防迷路 UX |
| [fixture-validator](./fixture-validator.md) | 测试夹具构建 + 端到端准确性回归 |

---

## 项目专属 Agents

每个具体项目只写**自己的 orchestrator + overview**,复用上面的通用 agent。

### Fisherman(本项目)

Windows 桌面端的 YOLOv8 视觉自动化工具。技术栈:Python + PyQt5 + PyTorch CPU + Ultralytics YOLO + SQLAlchemy/SQLite + mss + pyautogui。真相源:[SPEC.md](../SPEC.md)。

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

### 脚手架自带(其它项目示例,与 Fisherman 无关)

下列 agent 是 sdd-starter 脚手架的内置示例,**与本项目无关**,可保留作参考或删除:

| Agent | 来源项目 |
| ----- | -------- |
| [codeviz-overview.md](./codeviz-overview.md)、[codeviz-orchestrator.md](./codeviz-orchestrator.md) | 代码可视化阅读器(codeviz) |
| [3d-rendering-engineer.md](./3d-rendering-engineer.md)、[3d-interaction-designer.md](./3d-interaction-designer.md) | 3D 可视化(codeviz 子任务) |
| [business-translator.md](./business-translator.md)、[dataflow-tracer.md](./dataflow-tracer.md)、[io-entry-mapper.md](./io-entry-mapper.md) | 代码可视化通用能力 |
| [miniprogram-orchestrator.md](./miniprogram-orchestrator.md)、[miniprogram-ui-developer.md](./miniprogram-ui-developer.md)、[miniapp-business-logic.md](./miniapp-business-logic.md)、[wx-cloud-backend.md](./wx-cloud-backend.md) | 微信小程序示例 |
| [static-code-analyzer.md](./static-code-analyzer.md)、[fixture-validator.md](./fixture-validator.md)、[spec-docs-curator.md](./spec-docs-curator.md) | 通用能力(可保留) |

---

## Agent 模板

```markdown
# {Agent 名称}

## 角色

## 专业领域

## 触发词

## 工作流程

## 系统提示

## 输出格式
```

复制模板创建新 agent：`docs/agents/{你的agent名称}.md`
