# Fisherman — 项目 SPEC(真相源)

> 本文件是 Fisherman 项目按 SDD 方法论维护的**唯一真相源**。所有需求与架构决策以本文为准。
> 代码注释、git log、README 都可能滞后,**冲突时以本 SPEC 为准**。
>
> 版本:v1.0(2026-05-19 由 olddocs 吸收 + 代码扫描产出)
> 维护人:Fisherman Team
> 上次同步:2026-05-19

---

## 0. 文档定位

- 信息来源:`olddocs/原始设计文档/` 全部 10 份 + 实际代码扫描 + `pyproject.toml`
- 吸收记录:[olddocs-摘要.md](./olddocs-摘要.md)
- 详细模块清单/运行期目录结构等长尾信息:`olddocs/原始设计文档/04_modules.md`、`07_directory_layout.md`(只读历史快照)

---

## 1. 项目概述

### 1.1 基本信息

| 项 | 内容 |
|----|------|
| 项目名称 | Fisherman |
| 当前版本 | 1.0.0 |
| 项目类型 | Windows 桌面应用 |
| 项目简介 | 基于 YOLOv8 的视觉自动化工具,提供「数据标注 → 模型训练 → 屏幕识别 → 自动点击」一站式闭环能力 |
| 目标用户 | 游戏辅助开发者、自动化办公人员、CV 初学者 |
| 项目背景 | 让用户无需编写代码即可通过图形界面训练识别模型并实时监控屏幕、识别目标、触发鼠标点击 |

### 1.2 核心价值

- **闭环完整**:数据 → 模型 → 实时推理全流程可视化
- **零代码**:用户全程 GUI 操作,不需要写 Python
- **模块化**:gui / training / recognition / training_result / global_support 解耦,易扩展
- **本地化**:全部 CPU 推理,无云端依赖

### 1.3 非目标(Non-Goals)

- ❌ 不做 Web / 云端推理服务
- ❌ 不做分布式训练(单机 CPU)
- ❌ 不提供从零开始的模型结构设计(基于 YOLOv8 预训练权重微调)
- ❌ 不做 macOS / Linux 正式支持(代码理论可跑,未正式测试)

---

## 2. 功能需求

按 GUI 主入口拆解。每个功能项标注当前完成度。

### 2.1 训练标签页(TrainingTab)— ✅ 已完成

**作为** 用户,**我希望** 通过列表管理我的训练集,**以便** 组织多个独立的识别任务。

**功能点**:
- F2.1.1 新建训练集(输入名称 + 备注 → 生成 UUID 训练集)
- F2.1.2 训练集列表(显示名称、备注、图片数、标注进度、状态、创建时间)
- F2.1.3 删除训练集(二次确认,同时删除数据库记录 + 磁盘目录)
- F2.1.4 双击打开训练集详情对话框

**验收标准**:
- [x] 训练集 UUID 与目录名一致(避免名称冲突)
- [x] 删除训练集后数据库与磁盘均无残留
- [x] 列表实时刷新

### 2.2 训练集详情 — 图片管理(ImagesTab)— ✅ 已完成

**功能点**:
- F2.2.1 导入图片(选文件/文件夹 → **复制**到 `dataset/images/`,不动原文件)
- F2.2.2 图片列表(显示文件名 + 已标注/未标注状态)
- F2.2.3 进入标注(打开 `AnnotationWindow` 逐张标注)
- F2.2.4 清空全部图片(同时清空 `labels/`)
- F2.2.5 **从图库导入图集**:按钮「从图库导入图集」→ 弹出图集下拉框(名称 + 图片数)→ 选中后把该图集所有图片复制到当前训练集 `dataset/images/`;走 `library_manager.import_album_to_dataset(album_id, task_id)`,与图库侧导入逻辑一致(复制不移动)

### 2.3 训练集详情 — 训练(detail_tabs/training)— ✅ 已完成

**功能点**:
- F2.3.1 参数配置:epochs、batch_size、imgsz、模型类型(yolov8n/s/m)、lr、patience
- F2.3.2 训练控制:开始 / 暂停 / 停止
- F2.3.3 实时日志:epoch / loss / mAP 滚动显示
- F2.3.4 训练完成后权重自动归档到 `training_result/{task_name}/weights/best.pt`

**验收标准**:
- [x] 训练参数有合法性校验(epochs 1-1000、batch 1-128)
- [x] 训练过程不阻塞 UI 主线程
- [x] 训练异常不导致主程序崩溃

### 2.4 标注窗口(AnnotationWindow)— ✅ 已完成

**作为** 用户,**我希望** 用图形化方式给图片画框打标签,**以便** 不写代码就能产出 YOLO 训练数据。

**功能点**:
- F2.4.1 矩形框绘制(鼠标拖拽)
- F2.4.2 多类别标签
- F2.4.3 撤销 / 上一张 / 下一张
- F2.4.4 自动保存为 YOLO 格式 `.txt` 到 `dataset/labels/`
- F2.4.5 标注一致性校验(`AnnotationValidator`)

### 2.5 训练结果标签页(TrainingResultTab)— 🚧 75% 完成

**功能点**:
- F2.5.1 列出 `training_result/` 与 `models/` 的所有 `.pt` 模型
- F2.5.2 导入外部模型
- F2.5.3 删除模型(同步 `model_versions` 表)
- F2.5.4 设为默认(`is_default=1`,其它置 0)
- ⏳ F2.5.5 模型对比(mAP / loss 曲线对比)— **未实现**

### 2.6 识别测试标签页(RecognitionTestTab)— ✅ 已完成

**作为** 用户,**我希望** 在不触发点击的情况下验证模型识别效果,**以便** 调试模型/参数。

**功能点**:
- F2.6.1 选择模型 + 置信度阈值(10-95)
- F2.6.2 ROI 区域选择(可拖拽)或全屏监控
- F2.6.3 实时显示 BBox + 置信度 + 类别
- F2.6.4 FPS / 识别总数统计

### 2.7 识别操作标签页(RecognitionActionTab)— 🚧 65% 完成

继承 RecognitionTestTab 的能力,增加点击执行。

**功能点**:
- F2.7.1 点击冷却时间(避免连续触发)
- F2.7.2 点击动作类型
- F2.7.3 可选自定义 Python 脚本
- F2.7.4 受 TaskScheduler 调度,与训练任务串行

**进行中 / 待优化**:
- ⏳ 多目标识别策略(轮流/优先级)
- ⏳ 错误处理与重试
- ⏳ 自定义脚本沙箱

### 2.8 位移测试标签页(DisplacementTestTab)— ✅ 已完成

**作为** 用户,**我希望** 只有当目标明显移动时才被提醒,**以便** 忽略静止目标的干扰。

继承识别测试的全部能力,在回调层叠加**位移感知过滤**——只有当追踪目标在时间窗口内中心点移动距离超过阈值时才触发提示。不触发点击。

**功能点**:
- F2.8.1 所有识别参数同 RecognitionTestTab(模型/置信度/设备/ROI 区域)
- F2.8.2 位移参数(详见 §5.5,bbox 自适应):
  - 灵敏度滑块(5–50 %,默认 **9%**)— 实际阈值 = bbox 对角线 × 该比例
  - 最小阈值滑块(1–30 px,默认 **5 px**)— 兜底防 YOLO 抖动假阳
  - 时间窗口滑块(0.5–10.0 s,默认 **0.5 s**)
  - 触发冷却滑块(0–10 s,默认 1.0 s)
- F2.8.3 实时预览帧仍显示所有检测框(不限于触发目标)
- F2.8.4 触发时日志:目标 class + 位移距离/阈值 px + bbox 百分比 + bbox 对角线 + 当前坐标
- F2.8.5 布局:左右分栏,左侧参数+日志,右侧预览撑满;预览随窗口/分隔条尺寸变化自适应

**验收标准**:
- [x] 目标静止不移动 → 不触发
- [x] 历史记录不足 window_seconds → 不触发(目标刚出现)
- [x] 中心点移动 > 自适应阈值 且历史充足 → 触发
- [x] 冷却期内不重复触发
- [x] 远距离小目标(bbox 30×30)与近距离大目标(bbox 80×80)用同一组灵敏度参数都能稳定触发

### 2.9 位移操作标签页(DisplacementActionTab)— ✅ 已完成

继承位移测试的位移感知过滤能力,触发时执行用户自定义 Python 脚本(同 RecognitionActionTab 脚本机制)。

**功能点**:
- F2.9.1 所有参数同 DisplacementTestTab(模型/置信度/设备/ROI/灵敏度/最小阈值/时间窗口/冷却,bbox 自适应阈值)
- F2.9.2 Python 脚本配置区(同 RecognitionActionTab)
- F2.9.3 脚本内 `detections` 变量只包含触发了位移条件的目标(过滤后列表),每个元素含:`class_name` / `center` / `confidence` / `bbox` / `displacement_px` / `threshold_px` / `displacement_ratio` / `bbox_diag_px`
- F2.9.4 统计:识别帧数、位移触发次数、脚本执行次数、FPS

**验收标准**:
- [x] 触发条件与 DisplacementTestTab 完全一致
- [x] 脚本在后台线程执行,不阻塞识别循环
- [x] 脚本内 `print` 走 `QMetaObject.invokeMethod` 线程安全写日志

### 2.10 设置标签页(SettingsTab)— ✅ 已完成

- F2.10.1 显示运行环境(Python、PyTorch、CUDA 状态)
- F2.10.2 显示项目路径、数据库位置

### 2.11 日志查看器(LogViewerDialog)— ✅ 已完成

- F2.11.1 按任务 ID / 级别 / 时间过滤
- F2.11.2 读取 `training_logs`、`recognition_logs` 表 + `logs/fisherman.log`

### 2.12 任务调度(隐式能力)— ✅ 已完成

- F2.12.1 训练 + 识别任务统一走 `task_scheduler.submit()`
- F2.12.2 同一时刻至多一个重任务运行(`max_concurrent_tasks=1`)
- F2.12.3 用户无感知

### 2.13 图库标签页(ImageLibraryTab)— ✅ 已完成

**作为** 用户,**我希望** 在玩游戏的同时快速采集截图并按「图集」分组管理图片库,**以便** 把不同场景(浮漂-白天 / 浮漂-夜晚)的素材独立组织,再分别导入对应训练集。

**布局**:左右两栏。

```text
[新建图集]
┌──────────┬──────────────────────────────┐
│ 默认图集  │  [导入图片] [导入文件夹]        │
│ 浮漂-白天 │  ┌───┐ ┌───┐ ┌───┐          │
│ 浮漂-夜晚 │  │   │ │   │ │   │ ...      │
│          │  └───┘ └───┘ └───┘          │
│          │  [全选] [删除选中] [导入训练集] │
└──────────┴──────────────────────────────┘
截图热键: F9 框选 / F8 800×600 跟随 → 当前图集: 默认图集
```

**功能点**:

- F2.13.1 **图集列表(左栏)**:每行显示图集名 + 图片数;右键菜单提供「重命名 / 删除」;底部「新建图集」按钮
- F2.13.2 **图集 CRUD**(所有图集等权,均可改名/删除):
  - 新建:弹出输入框,名称非空 + 同名校验
  - 重命名:右键 → 输入新名称
  - 删除:二次确认;删除图集时一并删除图集内所有图片(DB 记录 + 磁盘文件)
- F2.13.3 **首启状态**:首次运行不自动创建任何图集,UI 左栏为空;按 F9/F8 时若无任何图集,后台仅日志告警,不截图(用户需先点「新建图集」)
- F2.13.4 缩略图网格浏览(右栏,仅显示当前选中图集的图片)
- F2.13.5 文件导入(单张或多张 `.jpg`/`.png`/`.bmp` 文件 → **当前选中图集**,复制不移动)
- F2.13.6 文件夹批量导入(递归扫描 → **当前选中图集**,复制不移动)
- F2.13.7 全局快捷键截图,两种模式皆把所截矩形存入 `image_library_files/<album_id>/` 并归入**当前选中图集**;选择器已弹出时再次按任一热键都被忽略:
  - **F9 自由框选**:弹出全屏覆盖层,鼠标拖拽矩形,松开鼠标即确认,Esc 取消
  - **F8 固定 800×600 跟随**:弹出全屏覆盖层,**800×600 橙色矩形以鼠标为中心实时跟随**,贴近屏幕边缘时自动 clamp 不越界;**左键点击**确认,Esc 取消(适合 YOLO 训练:统一视野,鱼漂占比稳定)
- F2.13.8 删除选中图片(二次确认;仅删库记录 + 磁盘文件,不影响已导入训练集的副本)
- F2.13.9 **选中导入到训练集**:可选「仅选中图片」或「当前图集全部图片」→ 选择目标训练任务 → 复制到该任务 `dataset/images/`
- F2.13.10 顶部状态栏显示当前图集名 + F9/F8 热键状态;底部状态栏显示当前图集图片数 + 今日截图数
- F2.13.11 **磁盘布局**:每个图集独占一个子目录 `image_library_files/<album_id>/`(以 UUID 命名,稳定不随重命名变化);新截图/新导入都写入对应子目录;删除图集时连子目录一并清理
- F2.13.12 **打开当前图集目录**:顶部按钮「打开文件夹」用系统资源管理器跳转到当前图集子目录(无选中图集时退回到根目录 `image_library_files/`)
- F2.13.13 **升级兼容**:启动时一次性迁移 — 把位于根目录的旧图片按 DB 中其 album_id 移动到对应子目录并同步更新 `file_path`

**全局快捷键设计约束**:

- 热键监听在独立守护线程运行,应用关闭时随主进程退出
- 截图使用已有 `mss` 依赖,按所选矩形(绝对屏幕坐标)抓取
- 区域选择器复用 `gui.screen_area_selector.ScreenAreaSelector`(与识别/位移 Tab 共用);构造参数 `fixed_size=(w, h)` 切换为「固定尺寸跟随鼠标」模式,默认 `None` 为自由框选
- 热键依赖库:`keyboard==0.13.5`(已引入)
- 热键截图目标始终是 UI 当前选中的图集 id(`_current_album_id`)
- 跨线程:`keyboard` 回调在后台线程,通过 `pyqtSignal` 切回主线程才能弹出 `QWidget`(架构不变量 2)
- 固定尺寸常量 `ImageLibraryTab.FIXED_SIZE = (800, 600)`,改尺寸先改这里
- 热键冲突(与 WoW 按键重叠)由用户自行配置回避

**验收标准**:

- [x] WoW 全屏运行时按 F9 弹出框选覆盖层;松开鼠标后只保存所框矩形区域到当前图集
- [x] 按 F8 弹出 800×600 橙色矩形,随鼠标实时移动;左键点击保存该矩形到当前图集
- [x] F8 矩形贴近屏幕边缘时自动 clamp 在屏幕内,不越界
- [x] 切换图集后,F9/F8 截图目标随之切换
- [x] 任一模式按 Esc 取消 → 不产生任何图库记录与磁盘文件
- [x] 选择器已弹出时再按 F9/F8 不会重复弹出新的选择器
- [x] 删除图集 → 图集内所有图片(DB + 磁盘)同步删除
- [x] 首次启动无任何图集,F9/F8 仅日志告警,不创建截图
- [x] 缩略图网格按当前图集过滤,500 张内不明显卡顿

### 2.14 钓鱼标签页(FishingTab)— ✅ 已完成(M5)

**作为** WoW 玩家,**我希望** 按一个热键就启动死循环自动钓鱼,**以便** 完全无人值守完成钓鱼。

**整体设计**:全新 Tab,串联「预备等待 → 钓鱼前准备 → 抛竿 → 抛竿后等待 → 位移检测 → 触发后等待 → 右键拾取 → 钓鱼后处理 → 回到开头」死循环。位移检测复用 [§5.5 DisplacementTracker](#55-displacementtracker-算法);按键输入复用 `keyboard` 库字符串格式;点击复用 `pyautogui`。

**布局(自上而下)**:

```
┌── 识别参数 ─────────────────────────────────────────┐
│ 模型: [▼ wow_fish.pt]   置信度: ●─── 0.70           │
│ 计算设备: [▼ CPU]                                   │
│ 位移检测区域: [选择区域] [全屏]  (200,100) 800×400  │
└─────────────────────────────────────────────────────┘
┌── 钓鱼循环参数 ─────────────────────────────────────┐
│ 启动热键: [F11]    停止热键: [F12]                  │
│ 0. 预备等待:        [0.0] s                         │
│ 1. 钓鱼前准备 按键: [   ]    (空=跳过)              │
│ 2. 抛竿键:         [ 1 ]                            │
│ 3. 抛竿后等待:      [1.0] s   位移检测超时: [10.0] s│
│ 4. 触发后等待:      [1.0] s   (随后右键点击触发目标)│
│ 5. 钓鱼后处理 按键: [   ]    (空=跳过)              │
└─────────────────────────────────────────────────────┘
┌── 运行状态 / 日志 ──────────────────────────────────┐
│ 状态: 等待启动(按 F11 开始)                        │
│ 轮次 12  成功 9  超时 3  连续失败 1                 │
│ [日志窗口,显示每轮各阶段时间与触发坐标]            │
└─────────────────────────────────────────────────────┘
```

**功能点**:

- F2.14.1 **识别参数**(模型/置信度/设备/检测区域)同 [§2.9 DisplacementActionTab](#29-位移操作标签页displacementactiontab-已完成)
- F2.14.2 **位移检测参数**:**不暴露 UI 调整**,固定使用 [§2.8](#28-位移测试标签页displacementtesttab-已完成) 实测最优默认(`displacement_ratio=0.09` / `min_displacement_px=5` / `window_seconds=0.5` / `trigger_cooldown_s=1.0`,bbox 自适应阈值);若调参,先在位移测试 Tab 验证再改 SPEC 默认常量
- F2.14.3 **启动/停止热键**两个 QLineEdit,默认 `f11` / `f12`;**仅接受单键**(`keyboard` 库单键字符串如 `f1`/`q`/`numpad1`/`space`),**不支持组合键**(D1 用户拍板,简化校验);未运行时改后立即重新注册;两个热键不可相同;不可与图库 F8/F9 同键(技术约束:`keyboard` 库同键不能多源注册);**允许与 WoW 游戏内键位冲突**,用户自行回避(D2 用户拍板)
- F2.14.4 **0. 预备等待**:每轮循环开始前强制 `sleep N` 秒(0–10,默认 **5.0**);用途:跨轮节奏控制 / 给用户留退出窗口
- F2.14.5 **1. 钓鱼前准备**:**单键**字符串,默认空。每轮按一次,可放抛饵宏 / 切换装备宏;空=跳过
- F2.14.6 **2. 抛竿键**:**单键**字符串,默认 `-`,**必填**;每轮按一次
- F2.14.7 **3. 抛竿后等待 + 位移检测超时**:
  - 抛竿后等待:抛竿后强制 `sleep N` 秒(0.1–10,默认 **3.0**)再开始位移检测,等浮漂落水稳定
  - 位移检测超时:从位移检测开始算,N 秒(1–60,默认 **17.0**)内未触发则放弃本轮,**仍执行钓鱼后处理**(让"清理空菜单"类通用宏生效),然后下轮
- F2.14.8 **4. 触发后等待 + 右键拾取**:触发位移后 `sleep N` 秒(0.1–5,默认 1.0)再 `pyautogui.rightClick(target.center + monitor_area_offset)`;`target` = 触发列表里 `confidence` 最高的那个(对应 `good_models/wow_fish.pt` 单类别模型,单浮漂场景通常长度 = 1)。**双屏注意**:detection.center 是图像局部坐标,必须 + 选区偏移才是屏幕绝对坐标;副屏游戏需通过「选择区域」框选游戏窗口(`mss.monitors[1]` 全屏模式只截主显示器)
- F2.14.9 **5. 钓鱼后处理**:**单键**字符串,默认空。每轮按一次,可放分解装备 / 修耐久宏;空=跳过
- F2.14.10 **运行时 UI 锁定**:启动后所有参数控件 + 启停热键 QLineEdit 禁用(防误改);仅「停止」按钮可点
- F2.14.11 **状态显示**:实时显示当前阶段 + 计时,例如 `第 7 轮 — 步骤 3 抛竿后等待 0.6/1.0 s` / `第 7 轮 — 步骤 4 位移检测 5.4/10.0 s`
- F2.14.12 **统计**:总轮次 / 成功轮次(触发位移并点击) / 超时轮次 / 连续失败次数(>5 时高亮提示用户介入)
- F2.14.13 **停止**:按停止热键 或 点「停止钓鱼」→ 优雅退出当前步骤(最长等当前 sleep 或超时结束)→ 停 tracker、停识别线程、UI 解锁
- F2.14.14 **日志精简**(D5 用户拍板;考虑长时挂机 12+ 小时,避免日志爆炸):
  - **仅在以下情况打印一行**到 `logs/fisherman.log`:启动 / 停止 / 异常 / 超时(连续超时仅每轮打 1 行,不重复刷屏)/ 用户脚本错误
  - **正常轮次**的「抛竿 → 等待 → 检测 → 拾取 → 后处理」**不写文件日志**,完全靠 UI 状态显示和内存统计满足实时观察
  - **不写数据库**:初版仅内存统计,关闭 Tab / 重启程序后数据丢失;后续若需追溯成功率,再补 `fishing_logs` 表
  - 触发时的目标 `class_name` / `center` / `confidence` **只更新 UI**,不落盘
- F2.14.15 **实时预览**:UI 右下嵌入预览画面(替代日志窗,2026-05-25 调整)。识别管线在整个钓鱼期间常驻(原本仅 DETECTING 时启停),`ScreenRecognition.on_frame_result` 把每帧 BGR + detections 发回 UI,后台线程做 `draw_detections + cvtColor + QImage.scaled`,主线程仅 `setPixmap`,符合架构不变量 2。CPU 代价:YOLO 推理一直跑(~10 FPS),挂机时长时段 1 个核心持续负载,可接受;后续若需省电再加「实时预览」开关

**全局快捷键约束**:

- F11/F12 注册走 `keyboard.add_hotkey`,守护线程,程序退出随之释放
- 与图库 F8/F9 不冲突(UI 校验,冲突时拒绝注册并提示)
- 启动后**不拦截其他按键**(WoW 操作不受影响),只监听用户配置的停止键
- 跨线程:`keyboard` 回调走 `pyqtSignal` 切回主线程更新 UI,工作线程实际控制循环

**并发约束**:

- 钓鱼运行时若用户同时启动其他识别 Tab(测试/操作/位移),`pyautogui` 鼠标会被多源争抢
- M5 初版:**不强制互斥**,UI 顶部红字提示「钓鱼运行时请勿启动其他识别任务」;后续可加全局识别状态锁(backlog)
- 与训练任务的并发:训练通过 `task_scheduler` 串行化,钓鱼期间用户提交训练会被调度器排队等钓鱼停止后自动跑(若钓鱼始终不停,训练就一直等)— 行为可接受

**验收标准**:

- [ ] 按 F11 启动 → 状态变「第 1 轮 — 步骤 0 预备等待」+ UI 锁定
- [ ] 按 F12 / 点停止 → 当前步骤跑完后干净退出,无残留线程,UI 解锁
- [ ] 抛竿后超时未触发 → 跳过点击,执行钓鱼后处理(若有),进入下一轮
- [ ] 抛竿后触发位移 → 等待 N 秒 → 右键点击触发目标 center 屏幕绝对坐标
- [ ] 启动/停止热键改完(未运行时)立即生效;改成与图库冲突的键被 UI 拒绝
- [ ] 钓鱼前准备 / 钓鱼后处理为空时该步骤被跳过,不报错
- [ ] 连续 10 轮无意外中断(实测验收)
- [ ] WoW 全屏运行时热键仍能拦截到(`keyboard` 库已验证支持)

### 2.15 钓鱼独立 exe 打包(StandaloneFishing)— ⏳ 待开发(M6)

**作为** WoW 玩家,**我希望** 把钓鱼功能单独打包成 `.exe` 文件夹分发给朋友,**以便** 他们不需要安装 Python / 训练环境直接双击使用。

**整体设计**:复用 [§2.14 FishingTab](#214-钓鱼标签页fishingtab-已完成m5) + `fishing/fishing_loop.py`,去掉训练 / 图库 / 识别测试 / 设置等无关 Tab,新建极简入口 `fishing_main.py` 仅挂 FishingTab。打包工具用 PyInstaller(项目已用 `Fisherman.spec`),onedir 模式分发,zip 整个 `dist/fisherman_fishing/` 文件夹给最终用户。

**Scope 收口(2026-05-25 用户拍板)**:

| # | 决策 | 选择 |
|---|------|------|
| S1 | 模型来源 | **固定** `good_models/wow_fish.pt`(不允许用户外挂、不读 DB / `models/` / `training_result/`) |
| S2 | 位移检测区域选择 | **保留**(用 `gui/screen_area_selector.py`,跨虚拟屏) |
| S3 | 打包模式 | **onedir 单目录** + zip 分发(冷启动 ~2-3s vs onefile ~10-15s;杀软误报少) |
| S4 | exe 文件名 | `fisherman_fishing.exe` |
| S5 | 图标 / 启动闪屏 | 暂用 PyInstaller 默认图标 / 无闪屏(后续按需补) |

**功能点**:

- F2.15.1 **入口** `fishing_main.py`:极简 MainWindow,只挂 FishingTab + 状态栏。无菜单、无日志按钮、无其他 Tab
- F2.15.2 **模型加载固定**:FishingTab 在打包模式下不调 `model_manager.get_model_list()`,改为直接读 `<exe同目录>/good_models/wow_fish.pt`。检测路径:开发环境用 `os.path.dirname(__file__)`,exe 环境用 `sys._MEIPASS` 或 exe 同级
- F2.15.3 **解耦 ImageLibraryTab**:抽出 `fishing/constants.py` 存放「不可与 F8/F9 同键」的常量,FishingTab 改 import 此常量,**不再 import ImageLibraryTab**(避免链式拖入 image_library / db_manager / library_manager)
- F2.15.4 **解耦 model_manager / database**:FishingTab 不再 import `training_result.model_manager`;model_combo 在 standalone 模式下隐藏或锁死显示「wow_fish.pt」,模型路径硬编码
- F2.15.5 **PyInstaller spec** `fishing_standalone.spec`:
  - mode = onedir,exe name = `fisherman_fishing`
  - datas:`good_models/wow_fish.pt` → `good_models/`
  - hidden imports:`torch`、`ultralytics`、`cv2`、`mss`、`pyautogui`、`keyboard`、`PyQt5.sip`
  - excludes:`training`、`training_result`、`image_library`、`global_support.database`、`global_support.task_scheduler`、`gui.tabs.training_tab` 等所有无关模块,显著减小体积
- F2.15.6 **目录结构**:`dist/fisherman_fishing/` 内含 `fisherman_fishing.exe` + 几百个 dll/pyd + `good_models/wow_fish.pt`。整体大小目标 < 1 GB
- F2.15.7 **构建脚本** `build_standalone.bat`:封装 `uv run pyinstaller fishing_standalone.spec --noconfirm`,清理上次 `build/` + `dist/`
- F2.15.8 **README** `docs/standalone-build.md`:写清楚如何构建 / 如何分发 / 用户使用注意(F11/F12 不冲突 / 副屏游戏要选区域 / Windows Defender 误报对策)
- F2.15.9 **后台模式随包**(M7,D3 用户拍板=同步进 exe):后台钓鱼模式([§2.16](#216-钓鱼后台模式backgroundfishing--待开发m7))经共享的 FishingTab 自动进入独立 exe。打包要点:spec 的 `excludes` **不得**误删 `recognition.window_io`(纯 ctypes + numpy)与 `gui.window_region_selector`(PyQt5);二者无额外依赖,正常被 FishingTab import 链带入

**验收标准**:

- [ ] PyInstaller 构建无错误,产物在 `dist/fisherman_fishing/`
- [ ] dist 文件夹双击 `fisherman_fishing.exe` GUI 能启动
- [ ] 启动日志确认模型从 `good_models/wow_fish.pt` 加载成功
- [ ] 整个钓鱼闭环可用:F11 启动 → 抛竿 → 位移检测 → 右键拾取 → F12 停止
- [ ] 实时预览正常,无黑屏
- [ ] 区域选择跨屏正常(主屏/副屏都能选)
- [ ] 在**干净 Windows**(无 Python 环境的另一台机器)能跑通
- [ ] dist 整体大小 < 1 GB(zip 压缩后通常 ~300-500 MB)

**非目标**:

- ❌ 自动更新机制
- ❌ macOS / Linux 打包(SPEC §3.4 已声明未正式测试)
- ❌ 代码签名 / 公证(开发者朋友自用规模无需)
- ❌ 安装程序(NSIS / Inno Setup)— 用户直接解压 zip 用

**架构不变量校验**:

- [x] 不变量 5(uv.lock 锁定):PyInstaller 在 `uv venv` 内跑,使用锁定依赖
- [x] 不变量 6(CPU 推理):排除 `torch.cuda` 相关二进制(PyTorch CPU wheel 本来就不带 CUDA)
- [x] 不变量 7(logging 优先):新代码全 logging
- [x] 不变量 2(UI 线程安全):打包不改变线程模型,沿用 FishingTab 现有信号槽

### 2.16 钓鱼后台模式(BackgroundFishing)— ⏳ 待开发(M7)

**作为** WoW 玩家,**我希望** 钓鱼时游戏可以切到后台 / 被其他窗口遮挡,**以便** 挂机的同时用电脑做别的事,鼠标键盘不被占用。

**整体设计**:给 [§2.14 FishingTab](#214-钓鱼标签页fishingtab--已完成m5) 增加「操作模式」开关——前台(屏幕)模式 = M5 现状不变;后台(窗口)模式 = 按选定游戏窗口句柄抓帧 + PostMessage 投递键鼠,全程**不抢焦点、不动真实光标**。底层走 `recognition/window_io.py`(ctypes 直调 user32/gdi32,**零新依赖**,win32-only,非 win32 平台降级为空实现)。

**前后台模式对照**:

| 维度 | 前台模式(M5 现状) | 后台模式(M7 新增) |
|------|------|------|
| 捕获 | mss 屏幕区域(全屏 / 选区) | `window_io.capture_window(hwnd)`(PrintWindow,被遮挡也抓真实画面) |
| 键盘 | `pyautogui.press` | `window_io.post_key(hwnd, key)`(PostMessage) |
| 右键拾取 | `pyautogui.rightClick(屏幕绝对)` | `window_io.post_right_click(hwnd, 客户区)`(PostMessage) |
| 坐标系 | 屏幕绝对坐标 | 窗口客户区相对坐标 |
| 检测范围 | 全屏 / 屏幕选区 | 整个客户区 / 窗口内框选子区域 |
| 占用 | 游戏必须前台,鼠标被占用 | 游戏可后台,鼠标键盘自由 |

**功能点**:

- F2.16.1 **操作模式选择**:加「操作模式:前台(屏幕)/ 后台(窗口)」切换,默认**前台**(向后兼容);运行时锁定不可改
- F2.16.2 **游戏窗口选择**:后台模式显示「游戏窗口 [▼] [🔄刷新]」,下拉来自 `window_io.enum_windows()`(可见且有标题的顶层窗口),自动优先选中含「魔兽 / wow / warcraft」者;**存窗口标题**而非裸 hwnd —— 句柄随游戏重启变化,运行时按标题 `find_window()` 重新解析
- F2.16.3 **窗口内检测区域**(D2 用户拍板 = 可框选子区域):后台模式显示「检测区域 [窗口内框选] [整窗]」。框选走新对话框 `gui/window_region_selector.py`:抓一帧窗口画面 → 用户在画面上橡皮筋框矩形 → 返回**客户区相对坐标** (x,y,w,h);默认整窗。子区域用于减少误触发 + 缩小 YOLO 输入省 CPU
- F2.16.4 **抓帧后端切换**:窗口模式下 `ScreenRecognition` 捕获走 `window_io.capture_window(hwnd)`,设了子区域则裁剪;返回 BGR 与现状一致,下游推理 / 预览 / 位移检测全部复用,无感知
- F2.16.5 **后台投键**:`FishingLoop._press_key` 后台模式走 `window_io.post_key(hwnd, key)`;前台仍 `pyautogui.press`
- F2.16.6 **后台右键拾取**:`FishingLoop._do_pick_up` 后台模式走 `window_io.post_right_click(hwnd, cx, cy)`,坐标 = detection.center(子区域局部)+ 子区域偏移 = 客户区坐标(无标题栏偏移,见 [§5.5d](#55d-钓鱼后台模式-io-window_io));前台仍 `pyautogui.rightClick(屏幕绝对)`
- F2.16.7 **窗口失效处理**:运行中按标题解析不到 hwnd 或 `IsWindow` 为假(游戏关闭 / 重启)→ `on_error` 报「游戏窗口丢失」并停止循环,不静默空转
- F2.16.8 **实时预览**:后台模式预览显示抓到的窗口画面(被遮挡也是真实游戏画面),管线复用 [§2.14 F2.14.15](#214-钓鱼标签页fishingtab--已完成m5)
- F2.16.9 **鼠标自由**:后台右键经 PostMessage 投递,**不移动真实光标**,用户可同时操作电脑(本特性核心价值)

**已知边界**:

- 独占全屏 DX 游戏 PrintWindow 通常黑屏 → 需游戏切「窗口」/「窗口化全屏(无边框)」;UI 给提示
- 游戏后台会降帧甚至停渲 → WoW 需 `/console maxfpsbk 30` 保持后台出帧;UI / 文档提示
- win32-only;`window_io.is_supported()` 为假时禁用后台模式

**验收标准**:

- [ ] 后台模式选中 WoW 窗口,游戏切后台 / 被遮挡,预览仍显示真实游戏画面
- [ ] F11 启动、游戏在后台:抛竿(post_key)→ 位移检测 → 右键拾取(post_right_click)整套闭环成功
- [ ] 拾取时真实鼠标不动,用户可同时操作其他程序
- [ ] 窗口内框选子区域后,检测只在子区域、拾取落点正确(坐标对齐无竖直偏移)
- [ ] 游戏关闭后报「窗口丢失」并停止,无残留线程
- [ ] 前台模式行为与 M5 完全一致(无回归)

**架构不变量校验**:

- [x] 不变量 2(UI 线程安全):沿用 FishingTab 信号槽;window_io 调用不跨线程碰 QWidget
- [x] 不变量 6(CPU 推理):不涉及设备
- [x] 不变量 7(logging 优先):新代码全 logging
- [x] 不变量 8(opencv-headless):window_io 仅 numpy + ctypes,不引入 opencv-python
- [x] 不变量 5(uv.lock):零新依赖,不动锁文件

---

## 3. 非功能需求

### 3.1 性能

| 项 | 要求 | 当前状态 |
|----|------|---------|
| 屏幕截图速度 | mss.grab(),≥ 30 FPS @ 全屏 1920x1080 | ✅ 满足 |
| YOLO 推理 | yolov8n CPU,≥ 5 FPS | ✅ 满足 |
| UI 响应 | 任何后台操作不阻塞主线程 > 100ms | ✅ 通过信号槽切回主线程 |
| 训练吞吐 | 由 PyTorch CPU 决定,不在本项目优化范围 | N/A |

### 3.2 并发与线程模型

- **GUI 主线程**:PyQt5 事件循环,唯一 QWidget 操作线程
- **调度线程**:`TaskScheduler._scheduler_loop`(daemon)
- **训练线程**:`TrainingExecutor` 在调度器中执行
- **识别线程**:`ScreenRecognition.thread`(daemon)帧循环
- **标注并发**:`AnnotationManager` 内部 `ThreadPoolExecutor`(批量任务)

**约束**:所有后台 → UI 的回调**必须通过 Qt 信号槽**切回主线程。

### 3.3 错误边界

- 数据库层:统一捕获 `SQLAlchemyError`,在 `db_manager` 记日志后抛业务异常
- 训练/识别线程:内部捕获异常 → 通过回调通知 GUI;后台线程崩溃**不影响主程序**
- PyTorch 缺失:程序仍能启动,训练/识别按钮禁用并提示

### 3.4 兼容性

| 项 | 要求 |
|----|------|
| OS | Windows 10/11 64 位(主)、Linux/macOS(未正式测试) |
| Python | ≥ 3.8 |
| 内存 | ≥ 4 GB |
| 磁盘 | ≥ 2 GB |
| 运行时 | Visual C++ Redistributable 2015-2022(PyTorch 要求) |

### 3.5 可用性

- 全程 GUI 操作,无需编辑配置文件
- `启动_Fisherman.bat` 一键启动(检测依赖 + 启动应用)
- 错误提示走 UI 弹窗,不强制查日志

---

## 4. UI 结构

### 4.1 主窗口(MainWindow)

```
MainWindow (~160 行,仅做布局 + Tab 挂载)
├── 顶部菜单
├── QTabWidget(从左到右)
│   ├── ImageLibraryTab          — 图库(图集分组 + 截图采集 + 导入训练集)
│   ├── TrainingTab              — 训练集管理
│   ├── TrainingResultTab        — 模型版本管理
│   ├── RecognitionTestTab       — 识别测试(不触发点击)
│   ├── RecognitionActionTab     — 识别操作(触发点击/脚本)
│   ├── DisplacementTestTab      — 位移测试(目标位移超阈值才提示)
│   ├── DisplacementActionTab    — 位移操作(位移超阈值才执行脚本)
│   ├── FishingTab               — 钓鱼(死循环:抛竿 → 位移检测 → 右键拾取)
│   └── SettingsTab              — 环境信息
└── 底部状态栏 + "运行日志"按钮 → LogViewerDialog
```

### 4.2 对话框

- `DatasetDetailDialog`:容器,内嵌 `ImagesTab` + `detail_tabs/training/`
- `AnnotationWindow`:Qt 图形化标注器
- `LogViewerDialog`:日志查看
- `ScreenAreaSelector`:屏幕区域选择器(用于 ROI 配置)

### 4.3 已废弃但保留的组件

- `gui/tabs/recognition_tab.py`(旧版识别页,已被测试/操作两个 Tab 替代,**保留作参考**)

---

## 5. 技术架构

### 5.1 技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 语言 | Python | ≥ 3.8 |
| 包管理 | uv | 最新(astral) |
| GUI | PyQt5 | ≥ 5.15.0(Windows 锁 PyQt5-Qt5 ==5.15.2) |
| 深度学习 | PyTorch | ==2.3.0(CPU 版,便于打包) |
| | torchvision | ==0.18.0 |
| 目标检测 | Ultralytics YOLO | ≥ 8.0.0 |
| 图像处理 | OpenCV(headless) | ≥ 4.8.0(避开 Qt 冲突) |
| | Pillow | ≥ 10.0.0 |
| 屏幕截图 | mss | ≥ 9.0.0 |
| 自动化 | pyautogui | ≥ 0.9.50 |
| 数据库 | SQLAlchemy + SQLite | ≥ 2.0.0 |
| 数值 | numpy | < 2(YOLO 生态限制) |
| | pandas | ≥ 2.0.0 |
| | scipy | ≥ 1.10.0 |
| 系统信息 | psutil | ≥ 6.0.0 |
| 包索引 | 清华镜像 | https://pypi.tuna.tsinghua.edu.cn/simple |

### 5.2 分层架构

```
┌─────────────────────────────────────────────────────┐
│ 表示层 (Presentation)  gui/                          │
│   PyQt5 主窗口 + Tabs + Dialogs                      │
└─────────────────────────────────────────────────────┘
                       │ 信号 / 方法调用
                       ▼
┌─────────────────────────────────────────────────────┐
│ 业务层 (Business)                                    │
│   training/    训练管道(任务/数据集/标注/执行)        │
│   recognition/ 屏幕识别(截图/推理/点击)              │
│   training_result/  模型版本管理                     │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 支撑层 (Infrastructure)                              │
│   global_support/  数据库 / 任务调度 / 日志           │
│   sql/  建表 SQL                                     │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 存储层 (Storage)                                     │
│   SQLite (fisherman.db) | training_data/ | training_result/ │
│   models/ | logs/                                    │
└─────────────────────────────────────────────────────┘
```

### 5.3 模块清单(对外门面)

| 顶层包 | 职责 | 对外门面 |
|--------|------|----------|
| `gui/` | 主窗口 + Tabs + Dialogs | `gui.main_window.MainWindow` |
| `training/` | 训练生命周期管理 | `training.training_manager.TrainingManager` |
| `recognition/` | 屏幕监控与 YOLO 推理 | `recognition.screen_recognition.recognition_manager` |
| `recognition/` | 位移追踪(纯内存,无 DB) | `recognition.displacement_tracker.DisplacementTracker` |
| `training_result/` | 训练产物与模型版本 | `training_result.model_manager.ModelManager` |
| `image_library/` | 图库管理(截图存储 + 导入训练集) | `image_library.library_manager.LibraryManager` |
| `global_support/` | 数据库 / 任务调度 / 设备枚举 | `global_support.database.db_manager` + `global_support.task_scheduler.task_scheduler` + `global_support.device_resolver.get_available_devices` |

### 5.4 关键设计模式

| 模式 | 体现位置 |
|------|----------|
| Facade | `training_manager.TrainingManager`(聚合 task/annotation/training) |
| Singleton | `db_manager`、`task_scheduler`、`recognition_manager` |
| Strategy | `training/annotation/validation_strategies.py`(标注校验) |
| Template Method | `training/core/base_manager.py`(管理器基类) |
| Observer/Callback | YOLO 训练回调、识别 `on_recognition_result` |
| Factory | `task.creator.TaskCreator` |
| Pipeline Filter | `DisplacementTracker` 在识别回调层做位移过滤,与 `ScreenRecognition` 解耦 |

### 5.5 DisplacementTracker 算法

文件:`recognition/displacement_tracker.py`。纯内存对象,不写数据库。

**核心理念:相对位移(深度自适应)**

3D 场景下,真实世界的同一段运动在屏幕上的像素数取决于目标距离 — 近的目标 bbox 大、像素位移大,远的目标 bbox 小、像素位移小。**绝对像素阈值无法兼顾远近**。

本 tracker 把阈值绑定到目标自身大小:

```
threshold_px(per detection) = max(min_displacement_px, bbox_diagonal × displacement_ratio)
```

- `bbox_diagonal = hypot(bw, bh)` — 当前帧该检测的 bbox 对角线
- `displacement_ratio` — 用户调的「灵敏度」(默认 20%,即位移超过 bbox 对角线的 20% 触发)
- `min_displacement_px` — **绝对下限**,防远处 bbox 太小时阈值过小被 YOLO 检测抖动假阳(默认 5 px)

**追踪算法(每帧)**:

1. 遍历当前帧所有检测结果,取出 `(class_name, center, bbox)`
2. 对每个检测,在**同 class** 已有轨迹中找中心点欧氏距离最近的轨迹
3. 匹配半径 = `max(min_displacement_px × 4, threshold_px × 2)`,**也跟着 bbox 自适应**
4. 匹配成功 → 更新轨迹历史(写入 `ts, cx, cy, bw, bh`)
5. 匹配失败 → 创建新轨迹,本帧不触发(无历史可比)
6. 超过 `track_timeout_s`(默认 3 s)未被匹配的轨迹从状态中清除

**位移判定**:

```
past_center = 轨迹历史中时间戳最接近 (now - window_seconds) 的记录
threshold = max(min_displacement_px, current_bbox_diag × displacement_ratio)
if past_center 存在 and distance(current_center, past_center) > threshold:
    触发(返回字典中追加 displacement_px + threshold_px)
```

**可配置参数**:

| 参数 | 默认 | 范围 | UI 控件 |
|---|---|---|---|
| `displacement_ratio` | **0.09**(9%) | 5–50 % | 「灵敏度」滑块 |
| `min_displacement_px` | 5 | 1–30 px | 「最小阈值」滑块 |
| `window_seconds` | **0.5** | 0.5–10.0 s | 「时间窗口」滑块 |
| `trigger_cooldown_s` | 1.0 | 0–10 s | 「触发冷却」滑块 |
| `track_timeout_s` | 3.0 | — | 不暴露 |

**默认值调优历史**:9% / 0.5s 是 WoW 钓鱼场景实测最优组合 — 灵敏度太高(>15%)远距离漂动跳不出阈值,太低(<7%)近距离自然漂浮误触发;窗口太长(>1s)咬钩瞬间的快速回弹会被滑动平均掉,太短(<0.3s)YOLO 检测抖动会被放大成假阳。

**典型效果**:

| 场景 | bbox | 自动阈值(ratio=20%) | 8 px 位移 | 12 px 位移 |
|------|------|--------------------|---------|----------|
| 近距浮漂 | 80×80,diag≈113 | 22.6 px | ❌ | ❌(自然漂浮也不会误触发) |
| 中距浮漂 | 50×50,diag≈71 | 14.2 px | ❌ | ❌ |
| 远距浮漂 | 30×30,diag≈42 | **8.4 px** | ⚠ 临界 | ✅ 触发 |
| 极远浮漂 | 15×15,diag≈21 | min 5 px 兜底 | ✅ 触发 | ✅ 触发 |

**不变量约束**:禁止引入 `sort`/`deep_sort` 等外部追踪库(不变量 5 uv.lock 锁定);简单质心匹配 + bbox 自适应阈值已满足单目标 / 稀疏多目标场景。

### 5.6 数据模型

**SQLite 数据库**:`fisherman.db`(项目根)。全部主键为 UUID v4(`String(36)`)。

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `training_tasks` | 训练任务/数据集 | id, task_name, status, dataset_path, epochs, batch_size, mAP, loss |
| `training_logs` | 训练日志 | id, training_task_id (FK), log_level, log_message, log_time |
| `recognition_tasks` | 识别任务 | id, training_task_id (FK), status, confidence_threshold, click_cooldown |
| `recognition_logs` | 识别日志 | id, recognition_task_id (FK), log_level, log_message |
| `recognition_details` | 识别详情 | id, recognition_task_id (FK), timestamp, target_x/y, confidence, target_class |
| `model_versions` | 模型版本 | id, training_task_id (FK), model_path, version, is_default, file_size |
| `image_library_albums` | 图集分组 | id, name(UNIQUE), created_at |
| `image_library` | 图库条目 | id, album_id (FK, nullable=旧数据), file_path, source(`screenshot`/`import`), created_at |

**关系图**:

```text
TrainingTask (1) ──< (N) TrainingLog
TrainingTask (1) ──< (N) ModelVersion
TrainingTask (1) ──< (N) RecognitionTask
RecognitionTask (1) ──< (N) RecognitionLog
RecognitionTask (1) ──< (N) RecognitionDetail
ImageLibraryAlbum (1) ──< (N) ImageLibrary
```

**索引**:见 `sql/create_tables.sql`(单一权威),关键索引 `idx_training_task_status`、`idx_recognition_log_task`、`idx_model_version_default`。

**一致性约束**:
- 外键由 SQLAlchemy 关系维护,**当前无 `ON DELETE CASCADE`**,业务层级联清理
- `ModelVersion.is_default` 至多一条为 1,由 `ModelManager.set_default()` 同事务切换
- 状态字段为字符串枚举,由 `StatusTracker` 保证合法性

### 5.5b 模型来源聚合(ModelManager)

识别测试 / 识别操作 / 位移测试 / 位移操作 四个 Tab 的模型下拉框都通过 `model_manager.get_model_list()` 取数,后者扫描以下四个来源,在内存里合并去重(按绝对路径)。

| 来源 | 物理位置 | `version` 字段 | `dataset_name` 显示 | 是否随 git 仓库分发 |
|------|---------|--------------|------------------|:---:|
| **训练产出** | `training_result/<task>/weights/best.pt`(DB 注册) | `1.0` / `2.0` / ... | 训练集名 | ❌ |
| **手动导入** | `models/*.pt`(用户拖入) | `manual` | `手动导入` | ❌ |
| **内置预训练** | 项目根 `yolov8n.pt` / `yolo11n.pt` 等 | `builtin` | `内置预训练 (COCO 80类)` | ✅ |
| **精选模型** | `good_models/*.pt` | `curated` | `精选模型` | ✅ |

**精选模型(`good_models/`)的语义**:开发者人工挑选并入库的"开箱即用"模型。**全部 Tab 自动可见**,用户安装项目后无需任何训练即可直接用。当前已收录:`good_models/wow_fish.pt`(鱼漂识别)。

新增精选模型的流程:
1. 把 `.pt` 文件放进 `good_models/`
2. `git add good_models/<name>.pt`(`.gitignore` 已设例外允许)
3. commit + push,所有用户拉取代码即可使用

### 5.5c 钓鱼循环状态机(FishingLoop)

文件:`fishing/fishing_loop.py`(M5 新增,2026-05-25 落地)。纯内存对象,运行在单独工作线程,不写数据库。

**状态定义**:

```
IDLE          初始 / 已停止
PREPARE       步骤 0 + 1:预备等待 + 钓鱼前准备按键
CAST          步骤 2:抛竿键
WAIT_LAND     步骤 3a:抛竿后等待浮漂稳定
DETECTING     步骤 3b:位移检测中(超时 = 步骤 3 的超时时间)
TRIGGERED     步骤 4a:触发后等待
PICK_UP       步骤 4b:右键点击触发目标 center
POST_PROCESS  步骤 5:钓鱼后处理按键
TIMEOUT       检测超时,跳过点击直奔 POST_PROCESS
STOPPING      接收到 stop_flag,清理 tracker / recognition
```

**迁移图**:

```
                ┌─────────────────────────┐
                │ IDLE                    │
                └──────────┬──────────────┘
                  按 F11   │
                           ▼
              ┌────────────────────────┐
   ┌──────────│ PREPARE (sleep+keypress)│
   │          └────────────┬───────────┘
   │                       ▼
   │          ┌────────────────────────┐
   │          │ CAST (keypress)        │
   │          └────────────┬───────────┘
   │                       ▼
   │          ┌────────────────────────┐
   │          │ WAIT_LAND (sleep)      │
   │          └────────────┬───────────┘
   │                       ▼
   │          ┌────────────────────────┐
   │          │ DETECTING              │── 触发 ─────┐
   │          │   (start tracker)      │             │
   │          └────────────┬───────────┘             ▼
   │                       │           ┌──────────────────────┐
   │                       │超时       │ TRIGGERED (sleep)    │
   │                       │           └──────────┬───────────┘
   │                       ▼                      ▼
   │          ┌────────────────────────┐  ┌──────────────────┐
   │          │ TIMEOUT (stop tracker) │  │ PICK_UP          │
   │          └────────────┬───────────┘  │ (rightClick)     │
   │                       │              └────────┬─────────┘
   │                       └────────┬──────────────┘
   │                                ▼
   │          ┌──────────────────────────────────┐
   │          │ POST_PROCESS (keypress if set)   │
   │          └──────────────┬───────────────────┘
   │                         │
   │       stop_flag = true  │  否则回到 PREPARE
   └─────────────────────────┘     (next round)
                  ▼
   ┌────────────────────────┐
   │ STOPPING → IDLE        │
   └────────────────────────┘
```

**stop_flag 检查点**:每个 `sleep` 切成 0.05s 小步循环,每步检查 stop;`DETECTING` 阶段在 tracker 更新回调里检查。这样停止响应时间 ≤ 50ms。

**线程模型**:

- `FishingLoop` 起一个 daemon 工作线程跑状态机主循环
- 该线程内创建 `ScreenRecognition(...)` 实例 + `DisplacementTracker(...)`,在 `DETECTING` 阶段 start、`TRIGGERED`/`TIMEOUT`/`STOPPING` 阶段 stop
- 工作线程经 `pyqtSignal` 把「阶段变化」「轮次完成」「触发坐标」回写 UI(架构不变量 2)
- F11/F12 经 `keyboard` 全局守护线程注册,回调里只 set 一个 `start_event` / `stop_flag`,实际工作仍在 FishingLoop 线程做

**与 task_scheduler 的关系**:

钓鱼循环**不走 task_scheduler.submit()** — 它语义上不是「一次性重任务」,而是 UI-driven 的长循环,内部自己已经在串行启停识别管道。架构不变量 3「重资源串行」由 task_scheduler 在训练侧保证;钓鱼期间用户提交训练 → 训练入队 → 等钓鱼停止后自动跑(行为可接受)。

**架构不变量校验**:

- [x] 不变量 2(UI 线程安全):工作线程经 pyqtSignal 通知 UI
- [x] 不变量 3(重资源串行):钓鱼工作线程内的识别管道在 DETECTING 单段启动,与训练通过 task_scheduler 自然串行(不能并跑)
- [x] 不变量 6(设备显式化):钓鱼 Tab UI 暴露设备下拉,透传给 `ScreenRecognition`
- [x] 不变量 7(logging 优先):新代码全部走 logging,不使用 print

### 5.5d 钓鱼后台模式 IO（window_io）

文件:`recognition/window_io.py`(M7 新增,win32-only,ctypes 直调 user32/gdi32,**零新依赖**;非 win32 平台导出空实现,`is_supported()` 为假)。

**捕获(`capture_window`)**:`PrintWindow(hwnd, dc, PW_RENDERFULLCONTENT)` 让窗口自渲染一帧,与 z 序无关,被遮挡 / 部分最小化也能抓真实画面。**坐标对齐关键**:PrintWindow 按**窗口**原点渲染(含标题栏 / 边框),所以按整窗尺寸抓帧后,用 `ClientToScreen` 算出客户区相对窗口的偏移,裁剪出**纯客户区**;返回图 (0,0) == 客户区 (0,0),与 PostMessage 的客户区坐标严格对齐——否则竖直方向会差一个标题栏高度(M7 调试期实测踩坑)。返回 BGR ndarray,与 mss 路径同格式。

**输入**:

- `post_key(hwnd, key)`:`PostMessage(WM_KEYDOWN/UP)`,lParam 含 scancode(部分游戏校验);key 为单字符,经 `VkKeyScanW` + `MapVirtualKeyW` 解析 vk / 扫描码
- `post_right_click` / `post_left_click(hwnd, x, y)`:`WM_MOUSEMOVE` → `WM_xBUTTONDOWN(MK_x)` → `WM_xBUTTONUP`,lParam = 客户区 (x, y)
- 三者均**不抢焦点、不动真实光标**——这是后台模式「鼠标键盘自由」的来源

**坐标链(与前台对称)**:

- 后台:`detection.center`(在「喂给 YOLO 的帧」坐标系内 = 整窗客户区,或子区域裁剪) → + 子区域偏移(整窗则偏移 0) → 客户区坐标 → `post_right_click`
- 前台:`detection.center`(屏幕选区局部) → + `monitor_area` 屏幕偏移 → 屏幕绝对 → `pyautogui.rightClick`

**窗口句柄稳定性**:hwnd 随游戏重启变化,故 UI 存窗口**标题**,运行时用 `find_window(title)` 解析;解析不到 → 停循环报错(F2.16.7)。

### 5.6 关键目录结构

```
fisherman/
├── main.py                       入口
├── 启动_Fisherman.bat             Windows 启动器
├── pyproject.toml + uv.lock      依赖管理
├── fisherman.db                  SQLite(运行期产生)
├── yolov8n.pt                    YOLOv8 预训练权重(内置,COCO 80 类)
├── good_models/                  精选模型目录(随仓库分发,开箱即用)
│   └── wow_fish.pt               鱼漂识别精选模型
│
├── global_support/               全局支撑
├── gui/                          PyQt5 GUI
│   ├── tabs/                     主 Tab 集合
│   ├── detail_tabs/              Dialog 内嵌 Tab
│   └── *.py                      标注窗口/日志窗口/区域选择器
├── recognition/                  屏幕识别
├── training/                     训练管道
│   ├── task/ annotation/ training/  3 个子包
│   └── core/ utils/
├── training_result/              模型管理
├── sql/create_tables.sql         建表 SQL(单一权威)
│
└── 运行期目录(.gitignore)
    ├── training_data/{uuid}/dataset/{images,labels}
    ├── training_result/{name}/weights/best.pt
    ├── models/
    └── logs/fisherman.log
```

---

## 6. 当前状态与验收标准

### 6.1 模块完成度

| 模块 | 完成度 | 状态 |
|------|--------|------|
| global_support | ~92% | ✅ |
| gui | ~90% | ✅ |
| training | ~88% | ✅ |
| main.py | ~95% | ✅ |
| training_result | ~75% | 🚧 |
| recognition | ~65% | 🚧 |
| fishing | ~95% | ✅ M5 完结 2026-05-25 |

### 6.2 已知技术债

- 旧版 `gui/tabs/recognition_tab.py` 与新版并存,未清理
- 数据库无 `ON DELETE CASCADE`,删训练任务时业务层手动级联
- 训练/识别线程内有散落的 `print` 调试输出(应该走 logging)
- YOLO `runs/` 缓存目录与 `training_result/` 同步逻辑不明确

### 6.3 测试覆盖

| 测试脚本 | 用途 |
|---------|------|
| `simple_test.py` | 快速冒烟 |
| `test_modular_structure.py` | 模块结构校验 |
| `diagnose_pytorch.py` / `diagnose_pytorch_advanced.py` | PyTorch 环境诊断 |

**当前无 pytest 测试套件**,后续 P1 应建立。

### 6.4 健康检查清单

```bash
# 1. 依赖同步
uv sync

# 2. PyTorch 可用性
uv run python diagnose_pytorch.py

# 3. 启动应用
uv run python main.py
# 或双击 启动_Fisherman.bat
```

### 6.5 未来技术优化点(主动推迟,不是技术债)

下面是评估后**主动选择不做**的优化项,记录在此防止反复讨论。仅当触发条件出现时再回来考虑。

#### 6.5.1 截屏改用 WGC(Windows.Graphics.Capture)

**当前现状**:`recognition/screen_recognition.py` 用 `mss.grab()` 抓屏,5–15 ms/帧。

**WGC 是什么**:Windows 10+ 内置的现代截屏 API,OBS / Discord 等用的同一套。Python 接入有第三方包 `windows-capture`(PyPI)。

**期望收益**:

| 维度 | 现在(mss) | WGC | 增益 |
|------|---------|-----|------|
| 抓屏延迟 | 10 ms | **3 ms** | -7 ms |
| 端到端识别延迟 | 70 ms | ~58 ms | **-17%** |
| 锁窗口截图(HWND) | ❌ 只能按屏幕坐标矩形 | ✅ 即使窗口移动/被遮挡/最小化都能截到 | 功能性 |
| 排除自身覆盖物 | ❌ 自己画的红框会被回截 | ✅ 可排除 | 功能性 |

**为什么暂不做**:

- 钓鱼场景需求 ≤ 1 FPS,当前 CPU 推理已达 12–30 FPS,端到端速度**严重过剩**
- WGC 主要价值在「**功能性**」而非速度 — 当前用户使用模式还没遇到那些痛点
- 接入成本中等(0.5–1 天):事件驱动回调架构跟当前同步 grab 循环不一致,需重构
- 跨平台损失:mss 至少能跑 Linux/Mac,WGC 完全 Windows-only(虽然项目已是 Windows-only,但保留了未来可能性)

**何时回来做(触发条件,满足任一即应启动评估)**:

- [ ] 用户反馈「移动 WoW 窗口后识别区域错位」
- [ ] 实现实时识别框可视化(屏幕画框),需避免自身覆盖物被回截
- [ ] 多窗口/多角色挂机场景(M5 之后)
- [ ] 高 FPS 位移跟踪(M4)发现截屏成为新瓶颈

**实施路径(参考)**:

1. `pyproject.toml` 加 `windows-capture` 依赖并锁版本
2. `recognition/screen_recognition.py` 抽出 `CaptureBackend` 接口,实现 `MssBackend` 和 `WgcBackend` 两个后端
3. `SettingsTab` 加截屏后端切换开关(默认 WGC 可用则用 WGC,否则回退 mss)
4. 处理 WGC 回调线程到识别工作线程的桥接(可能用 `queue.Queue` 或 `threading.Event`)
5. 验证全屏独占模式下兼容性(WoW 经典服可能受影响)
6. 失败回退策略:WGC 初始化失败 / 三秒无帧 → 自动切 mss

---

## 7. 关键流程

### 7.1 训练流程(端到端)

```
新建训练集 → 创建 UUID 目录 + 入库
       ↓
导入图片 → 复制到 dataset/images/
       ↓
图形化标注 → 保存 YOLO .txt 到 dataset/labels/
       ↓
校验标注 → AnnotationValidator
       ↓
配置参数 → epochs/batch/imgsz/model_type
       ↓
TaskScheduler.submit → TrainingExecutor.train_by_name
       ↓
YOLOTrainer → ultralytics.YOLO.train()
       ↓
CallbackHandler → epoch/loss/mAP 回写 GUI + DB
       ↓
训练结束 → ResultSaver 复制权重 → model_versions 插入
       ↓
状态变 completed
```

### 7.2 识别流程

```
选择模型 + 区域 + 阈值 → RecognitionActionTab
       ↓
recognition_manager.start_recognition_task(cfg)
       ↓
ScreenRecognition 起后台线程
       ↓
帧循环:
  mss 截屏 → cv2.cvtColor → YOLO.predict
    → 过滤置信度 → 触发回调
    → 若冷却 OK:pyautogui.click + 写 recognition_details
       ↓
用户停止 → 线程 join → 状态归位
```

### 7.3 任务调度

- 优先级队列 + `threading.Condition` + `RLock`
- `max_concurrent_tasks = 1`(默认)
- 防止训练与识别同时抢 CPU

### 7.4 应用启动

```
启动_Fisherman.bat → uv sync → uv run python main.py
  ↓
main.py:
  - 尝试 import torch(失败仅警告)
  - setup_logging()
  - QApplication + MainWindow
       ↓
MainWindow.init_application():
  - db_manager.connect() + create_tables()
  - task_scheduler.start_scheduler()
  - 构建 Tabs
       ↓
进入 Qt 事件循环
```

### 7.5 应用关闭

```
MainWindow.closeEvent:
  - 逐 Tab.close() 停止内部线程
  - recognition_manager.stop_recognition_task()
  - task_scheduler.stop_scheduler()
  - 等线程 join → exit
```

---

## 8. 架构不变量(不可违反)

> 修改代码前必须检查,可能违反时**先与用户确认**:

1. **【MUST】单一真相源**:任何业务规则改动先改本 SPEC,再改代码
2. **【MUST】UI 线程安全**:跨线程更新 QWidget 必须通过 Qt 信号槽,禁止直接调用
3. **【MUST】重资源串行**:训练/识别任务必须经 `task_scheduler.submit()`,不绕过调度器
4. **【MUST】UUID 主键**:所有数据库主键 + 训练集目录名一律 UUID v4,禁止用名称
5. **【MUST】依赖锁定**:`uv.lock` 必须纳入版本控制,保证团队构建一致
6. **【MUST】设备选择显式化**:训练/推理使用的硬件设备必须由用户在任务发起时显式选择;系统**不自动降级**,设备不可用时报错提示用户;设备枚举走 `global_support/device_resolver.get_available_devices()`
7. **【SHOULD】logging 优先**:新代码禁止 `print`,统一走 logging 体系

---

## 9. 附录

### 9.1 术语表

| 术语 | 定义 |
|------|------|
| 训练集 | TrainingTask 的别名,GUI 中的展示名,对应 1 个 UUID 目录 + 1 行数据库记录 |
| 数据集 | 训练集内部的 `dataset/` 子目录,包含 images/ + labels/ |
| 模型版本 | 一次训练产出的 .pt 权重文件,对应 `model_versions` 表一行 |
| 默认模型 | 识别模块默认加载的模型,`model_versions.is_default=1` |
| 重任务 | 占用大量 CPU/GPU 的任务(训练/识别),受 TaskScheduler 串行化 |
| ROI | Region of Interest,用户指定的屏幕监控子区域 |

### 9.2 参考资料

- 原始设计文档(只读历史快照):[olddocs/原始设计文档/](../olddocs/原始设计文档/)
- 吸收摘要:[docs/olddocs-摘要.md](./olddocs-摘要.md)
- YOLOv8 文档:https://docs.ultralytics.com
- PyQt5 文档:https://www.riverbankcomputing.com/static/Docs/PyQt5/
- uv 文档:https://docs.astral.sh/uv/

### 9.3 变更日志

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-05-31 | v1.7 | M7 🚧 启动(设计阶段):新增 §2.16 BackgroundFishing(钓鱼后台模式)+ §5.5d window_io IO 后端 + 坐标链。FishingTab 加前台/后台操作模式开关:后台模式经 `recognition/window_io.py`(PrintWindow 抓帧 + PostMessage 投键投右键,零新依赖,win32-only)实现游戏后台 / 被遮挡也能钓鱼且不占鼠标。2 项决策拍板:检测范围 = 窗口内可框选子区域(D2)、同步进独立 exe(D3,§2.15 加 F2.15.9)。可行性已用 `帮助 → 后台 IO 测试` 面板 E2E 验证(抓帧 / 投键 / 投右键三项全过,坐标对齐 bug 已修) |
| 2026-05-25 | v1.6 | M6 🚧 启动(设计阶段):新增 §2.15 StandaloneFishing(钓鱼独立 exe 打包)。Scope 5 项 S1-S5 拍板:模型固定 `wow_fish.pt` / 保留区域选择 / onedir / `fisherman_fishing.exe` / 默认图标无闪屏。等用户审过设计后开工 `fishing_main.py` + `fishing_standalone.spec` |
| 2026-05-25 | v1.5 | M5 ✅ 完结:`fishing/fishing_loop.py` + `gui/tabs/fishing_tab.py` 落地并实测通过;默认值同步实测最优(预备 5s / 抛竿 `-` / 抛竿后 3s / 检测超时 17s);修双屏 click 偏移 bug(`+ monitor_area offset`);右下日志窗换为实时预览(识别管线常驻全程,后台线程图像处理 + 主线程 setPixmap);§2.14 ⏳ → ✅、§6.1 fishing 0% → ~95% |
| 2026-05-25 | v1.4 | M5 设计:新增 §2.14 FishingTab(死循环钓鱼:预备 → 前准备 → 抛竿 → 等待 → 位移检测 → 拾取 → 后处理)、§5.5c FishingLoop 状态机与线程模型、§4.1 Tab 列表加 FishingTab、§6.1 完成度加 fishing 行 |
| 2026-05-22 | v1.3 | M3 图库重构:§2.13 引入「图集」概念(左右两栏 UI + 图集 CRUD + 默认图集)、§4.1 ImageLibraryTab 提为第一个 Tab、§5.6 新增 `image_library_albums` 表 + `image_library.album_id` FK |
| 2026-05-22 | v1.2 | M3 图库功能:新增 §2.13 ImageLibraryTab 规格、§4.1 Tab 结构更新、§5.3 模块清单补充、§5.6 image_library 表 |
| 2026-05-22 | v1.1 | M2-前置2 位移感知:新增 §2.8 DisplacementTestTab、§2.9 DisplacementActionTab、§5.5 DisplacementTracker 算法 |
| 2026-05-19 | v1.0 | 初版。由 olddocs/原始设计文档/ 10 份文档 + 实际代码扫描合并产出 |
