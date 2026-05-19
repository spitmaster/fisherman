# CLAUDE.md

> 给未来的 Claude:**先读 [docs/](docs/) 再动手**。本仓库的真相源是 [docs/SPEC.md](docs/SPEC.md)。
> 本项目遵循 [~/.claude/CLAUDE.md](file:///c:/Users/zhouyijin/.claude/CLAUDE.md) v1.3 的文档规范。

---

## 第零步:看当前进度

> 摘自 ~/.claude/CLAUDE.md §5 — 分支 → 文件的发现协议。

### 三档晋升表

| 触发 | 动作 |
|------|------|
| 功能正式启动 | `roadmap.md` 标"⏳ 进行中"+ `milestones.md` 索引加一行 + 创建 `milestones/<branch>.md` |
| 开始具体 M | M 内容填入 `todo/<branch>.md`;`milestones/<branch>.md` 那行标 🚧 |
| M 完结 | `milestones/<branch>.md` 标 ✅ + commit + 日期;`todo/<branch>.md` 整段清空 |
| 功能完结 | `git mv milestones/<branch>.md → milestones/archive/<branch>.md`;主索引挪到"已归档";删 `todo/<branch>.md`;`roadmap.md` 加版本行 |

### 接手执行序列

1. `git branch --show-current` 拿到分支名
2. 打开 `docs/milestones/<branch with "/" → "_">.md` 看当前里程碑
3. 打开 `docs/todo/<branch with "/" → "_">.md` 看当前 M 的待办
4. 任一文件不存在 → **主动问用户**:新建?探索性工作?用其它文件名?
5. 分支是 `main` / `hotfix-*` 等非 feature 分支 → **不进入** milestone 上下文,主动问用户做什么

**唯一允许的文件名变换是 `/` → `_`**,其它不变。

---

## 第一步:读设计文档

| 优先 | 文档 | 用途 |
|------|------|------|
| 1 | [docs/SPEC.md](docs/SPEC.md) | **真相源**:项目定位 / 功能 / 非功能 / UI / 架构 / 状态 / 流程 / 不变量 |
| 2 | [docs/agents/fisherman-overview.md](docs/agents/fisherman-overview.md) | Agent 拓扑、共享契约、路由表 |
| 3 | [docs/roadmap.md](docs/roadmap.md) | 路线图 P0/P1/P2 + 技术债 |
| 4 | [docs/milestones.md](docs/milestones.md) | 里程碑主索引 |
| 5 | [docs/README.md](docs/README.md) | docs/ 子目录导览(脚手架默认) |
| 6 | [olddocs/原始设计文档/](olddocs/原始设计文档/) | 老设计文档(只读历史快照,作详细参考) |

---

## 项目一句话定位

**Fisherman** 是 Windows 桌面端的 YOLOv8 视觉自动化工具,提供「数据标注 → 模型训练 → 屏幕识别 → 自动点击」一站式 GUI 闭环。栈:Python 3.8+ / PyQt5 / PyTorch CPU / Ultralytics YOLO / SQLAlchemy + SQLite / mss / pyautogui / uv。

---

## 不可违反的架构不变量

详见 [docs/SPEC.md §8](docs/SPEC.md#8-架构不变量不可违反)。摘要:

1. **【MUST】SPEC 优先** — 业务规则改动先改 SPEC.md,再改代码
2. **【MUST】UI 线程安全** — 跨线程更新 QWidget 必须经 Qt 信号槽,**禁直接调用**
3. **【MUST】重任务串行** — 训练/识别必须经 `task_scheduler.submit()`,禁绕过
4. **【MUST】UUID 主键** — 所有数据库主键 + 训练集目录名一律 UUID v4
5. **【MUST】uv.lock 锁定** — 依赖锁文件入版本控制
6. **【MUST】CPU 推理** — 当前 CPU only,引入 GPU 需评估打包影响
7. **【SHOULD】logging 优先** — 新代码禁 `print`,统一 logging
8. **【SHOULD】opencv-python-headless** — 不引入 `opencv-python`(与 Qt 冲突)

任何动手前**先扫一遍**,可能违反时主动汇报。

---

## 关键目录速查

```
fisherman/
├── main.py                  入口(PyTorch 检查 + 日志 + MainWindow)
├── 启动_Fisherman.bat        Windows 一键启动(uv sync + uv run)
├── pyproject.toml + uv.lock 依赖管理(uv)
├── fisherman.db             SQLite(运行期产生,.gitignore)
├── yolov8n.pt               YOLOv8 预训练权重
│
├── global_support/          数据库 + 任务调度(单例)
│   ├── database.py             6 个 ORM 模型 + db_manager
│   └── task_scheduler.py       优先级队列 + Condition + RLock
├── gui/                     PyQt5 GUI(主线程唯一可操作 QWidget)
│   ├── main_window.py          约 160 行,挂载 Tabs
│   ├── tabs/                   主 Tab(training/recognition_*/settings)
│   ├── detail_tabs/            Dialog 内嵌 Tab
│   └── *.py                    标注窗口/日志窗口/区域选择器
├── recognition/             屏幕识别(后台线程)
├── training/                训练管道(facade + 3 子包)
│   ├── annotation/             Strategy 校验 + YOLO 格式
│   ├── task/                   任务/数据集元数据
│   ├── training/               训练执行 + YOLO 封装 + 回调
│   └── training_manager.py     对外门面
├── training_result/         模型管理
├── sql/create_tables.sql    建表 SQL(单一权威,与 ORM 同步)
│
├── docs/                    SDD 真相源 + agent + 三档规划
└── olddocs/                 老设计文档(只读历史快照)

运行期目录(.gitignore):
├── training_data/{uuid}/dataset/{images,labels}/
├── training_result/{name}/weights/best.pt
├── models/
└── logs/fisherman.log
```

---

## Agent 体系

详见 [docs/agents/README.md](docs/agents/README.md) 与 [docs/agents/fisherman-overview.md](docs/agents/fisherman-overview.md)。任务路由:

| 任务关键词 | Agent |
|-----------|-------|
| 跨模块协调 / 任务拆解 / 联调 | [fisherman-orchestrator](docs/agents/fisherman-orchestrator.md) |
| YOLO / 训练 / epoch / 超参 / mAP | [yolo-training-engineer](docs/agents/yolo-training-engineer.md) |
| 屏幕识别 / FPS / mss / 截图 / 点击 / ROI | [screen-recognition-engineer](docs/agents/screen-recognition-engineer.md) |
| Tab / Dialog / Widget / 信号槽 / Qt | [pyqt5-ui-developer](docs/agents/pyqt5-ui-developer.md) |
| 表 / ORM / 索引 / 迁移 / SQL | [sqlalchemy-db-engineer](docs/agents/sqlalchemy-db-engineer.md) |
| 调度 / 线程 / 并发 / Condition | [task-scheduler-engineer](docs/agents/task-scheduler-engineer.md) |
| 标注 / 校验 / Strategy / YOLO .txt | [annotation-tool-engineer](docs/agents/annotation-tool-engineer.md) |

---

## 测试 / 健康检查

```bash
# 1. 依赖同步
uv sync

# 2. PyTorch 可用性
uv run python diagnose_pytorch.py

# 3. 模块结构冒烟
uv run python test_modular_structure.py
uv run python simple_test.py

# 4. 启动应用
uv run python main.py
# 或双击 启动_Fisherman.bat(Windows)
```

预期:
- diagnose_pytorch:`PyTorch 库导入成功` + `device=cpu`
- 启动后 GUI 可见 5 个 Tab(训练 / 训练结果 / 识别测试 / 识别操作 / 设置)
- 日志写入 `logs/fisherman.log`

---

## 执行边界(摘自全局 ~/.claude/CLAUDE.md §10)

🚨 **下列动作必须先用 AskUserQuestion 征得明确同意,不可自主执行**:

- 改 `pyproject.toml` 版本号、git tag
- `uv publish` / 任何包发布
- `git push --force` / 共享分支 rebase
- `git push origin <长期分支>`(即使 commit 已完成,push 仍是独立门槛)
- 任何 `git merge`/`gh pr merge` 把分支并入长期分支
- 删除 git 跟踪过的文件
- 改 `fisherman.db` 生产数据 / schema 直接 DROP

**典型陷阱**:
- 用户说"合并到 dev" → **仅授权本地 merge**;push 是另一个门槛,必须再问一次
- 用户说"修这个 bug" → 改代码,**不要**自动 bump version、不要 publish
- 用户表达不满("为啥这么做") → **立刻停手**,不做善后

---

## 沟通约定

- **语言**:中文交流;commit message 也用中文(看历史:"优化"、"训练调整"、"识别模块, 选择模型"等)
- **commit footer**:遵循全局规范追加 `Generated with Claude Code` + `Co-Authored-By: AI-SDLC <aisdlc@radnova.com>`
- **代码注释**:默认不写;只写非显然的 *why*
- **文档比代码先行**:任何业务规则改动先改 SPEC,再改代码

---

## 修订日志

| 日期 | 变更 |
|------|------|
| 2026-05-19 | 初版。按全局 ~/.claude/CLAUDE.md v1.3 §7 最小骨架创建 |
