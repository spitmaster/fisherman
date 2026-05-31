# Fisherman — 路线图

> 功能级粗粒度路线图。月级更新。
> 细化里程碑见 [milestones.md](./milestones.md);具体待办见 `docs/todo/<branch>.md`。
> 真相源 [SPEC.md](./SPEC.md)。

---

## 当前版本

**v1.0.0**(2026-05 之前) — 完成训练 / 识别 / GUI 主体闭环,详见 [SPEC.md §6.1 模块完成度](./SPEC.md#61-模块完成度)。

---

## 进行中

### M7 钓鱼后台模式 🚧 设计阶段(2026-05-31 启动)

**背景**:M5 前台钓鱼要求游戏常驻前台、占用鼠标键盘,用户无法同时用电脑。M7 给 FishingTab 加「后台模式」:按窗口句柄 `PrintWindow` 抓帧 + `PostMessage` 投键投右键,游戏可后台 / 被遮挡,真实光标不动,挂机同时电脑自由用。可行性已 E2E 验证通过。

**设计落点**:SPEC [§2.16 BackgroundFishing](./SPEC.md#216-钓鱼后台模式backgroundfishing--待开发m7) + [§5.5d window_io](./SPEC.md#55d-钓鱼后台模式-io-window_io)。
**详情**:[milestones/20260204.md#m7--钓鱼后台模式--设计阶段](./milestones/20260204.md)。

- `recognition/window_io.py` ctypes 后端(零新依赖,win32-only)— 已落
- 检测范围 = 窗口内可框选子区域(D2);同步进独立 exe(D3)
- 前台模式保留共存,默认前台,向后兼容
- 后台拾取经 PostMessage 不动真实光标 → 鼠标键盘自由(核心价值)

### M6 钓鱼独立 exe 打包 🚧 编码完成,待干净 Windows E2E(2026-05-25 启动)

**背景**:把钓鱼 Tab 单独打包成 exe 文件夹分发给朋友(免装 Python)。复用 FishingTab + FishingLoop,极简入口 + PyInstaller onedir。编码完成(commit `d0482ee`),唯一剩余:无 Python 的干净 Windows 机器 E2E。

**设计落点**:SPEC [§2.15 StandaloneFishing](./SPEC.md#215-钓鱼独立-exe-打包standalonefishing--待开发m6)。
**详情**:[milestones/20260204.md#m6--钓鱼独立-exe-打包--设计阶段](./milestones/20260204.md)。

- 模型固定 `good_models/wow_fish.pt`,不读 DB;onedir + zip 分发;exe 名 `fisherman_fishing.exe`
- 干净 Windows 实测通过 → 完结

---

## 技术债

| # | 内容 | 优先级 |
|---|------|--------|
| TD-1 | 旧版 `gui/tabs/recognition_tab.py` 已被替代,需决定保留或删除 | 低 |
| TD-2 | 数据库无 `ON DELETE CASCADE`,删训练任务时业务层手动级联 | 中 |
| TD-3 | 训练/识别线程内有散落的 `print` 调试,应统一进 logging | 中 |
| TD-4 | YOLO `runs/` 缓存目录与 `training_result/` 同步逻辑不明确 | 低 |
| TD-5 | 脚手架自带的 codeviz / miniprogram / 3D agent 与本项目无关,可删 | 低 |
| TD-6 | `olddocs/技术设计/`、`olddocs/需求文档/`、`olddocs/README.md` 是脚手架占位,吸收完后可删 | 低 |

---

## 非目标(明确不做)

参见 [SPEC.md §1.3](./SPEC.md#13-非目标non-goals):

- ❌ Web / 云端推理服务
- ❌ 分布式训练
- ❌ 从零开始的模型结构设计
- ❌ macOS / Linux 正式支持(理论可跑,不投入测试)

---

## 已发布版本

| 版本 | 日期 | 简介 |
|------|------|------|
| M5 自动钓鱼 | 2026-05-25 | 独立 FishingTab + F11/F12 死循环六步骤(预备 / 钓鱼前准备 / 抛竿 / 抛竿后等浮漂 + 位移检测超时 / 触发后等待 + 右键拾取 / 钓鱼后处理);卡片式 UI + 实时预览(右下);双屏 click 偏移修复;默认值实测最优(5/3/17/1 s)。详见 [milestones/20260204.md](./milestones/20260204.md#m5--自动钓鱼-) |
| M4 位移测试 Tab 完善 | 2026-05-24 | bbox 自适应阈值(灵敏度 % + 最小阈值) / 默认值实测调优 / 触发日志增强 / 左右分栏 + 预览不占满 bug 修复,详见 [milestones/20260204.md](./milestones/20260204.md#m4--位移测试-tab-完善-) |
| M3 训练图库 | 2026-05-22 | F9 全局截图 + 图库管理 + 一键导入训练集,详见 [milestones/20260204.md](./milestones/20260204.md#m3--训练图库-) |
| v1.0.0 | 2026 上半年(具体日期见 git tag) | 训练 / 识别 / GUI 主体闭环 |

> 当版本数 ≥ 5 时,按全局 ~/.claude/CLAUDE.md §3.3 把旧版本压缩到 `docs/roadmap/archive/early-versions.md`。

---

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-05-25 | **M5 自动钓鱼 ✅ 完结**(用户实测通过)。同日完成:设计 → 编码 → 调试 → UI 优化 → E2E。SPEC §2.14 ⏳ → ✅、§6.1 fishing 0% → ~95%、§9.3 v1.5 changelog;「进行中」清空待下一个 M |
| 2026-05-25 | M5 自动钓鱼 🚧 启动(设计阶段)。SPEC §2.14 FishingTab 功能规格 + §5.5c FishingLoop 状态机落地;独立 Tab + F11/F12 死循环 + 复用 M4 位移检测;初版不入 DB |
| 2026-05-24 | M4 位移测试 Tab 完善 ✅ 完结(精简交付)。原计划的"轨迹可视化"+"参数热更新"评估后认定鸡肋,从 scope 移除;实际交付:bbox 自适应阈值 / 默认值调优 / 日志增强 / 布局重构。M5 自动钓鱼进入"进行中" |
| 2026-05-22 | 重新规划路线：M3 训练图库 → M4 位移测试完善 → M5 自动钓鱼，旧 P0/P1/P2 计划清除 |
| 2026-05-22 | P1-1 多设备支持骨架 ✅(架构落地,打包评估待补);SPEC 不变量 6 更新 |
| 2026-05-19 | SDD 体系建立 ✅(M1 完结);P0-1 多目标识别策略启动(M2)。"进行中"区从 SDD 切换为 P0-1 |
| 2026-05-19 | 初版。从 `olddocs/原始设计文档/09_roadmap.md` 吸收,按 SDD 三档规划分级到 P0/P1/P2 |
