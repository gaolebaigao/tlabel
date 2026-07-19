# TLabel Developer Guide

> **这份文档是给"未来的Agent session"看的。**
> 上下文溢出后新session醒来，读完这份文档就能独立开发，不会忘记之前的约定。
>
> 最后更新：2026-07-19 | 基线版本：v0.15.0

---

## 一、架构全景：三层漏斗

TLabel的核心定位是**触觉数据标注工具+标准**，采用"工具带标准"策略。
- **工具层**：提供可视化、阶段标注、质量检测、数据增强等实用功能，让用户"用得爽"
- **标准层**：通过工具使用自然扩散TLabel Format，成为事实标准
- **两个市场**：机器人研究（训练数据标注）+ 工业质检（跨传感器数据分析）
- **传感器覆盖**：视触觉传感器（GelSight/DIGIT等）+ 力/力矩传感器（ATI/Robotiq等）

一切功能设计围绕"让触觉数据好用、好标、好分析"展开。

```
输入（多种传感器数据包）      核心（统一标准层）           输出（多种下游生态）
─────────────────────       ──────────────────          ─────────────────────
GelSight ──┐                                              ├─ JSON / CSV / HDF5
DIGIT ─────┤                                              ├─ FTP-1/MTTS Zarr
PaXini ────┤                                              ├─ LeRobot Parquet
ToucHD ────┼──→ Adapter → 22维统一格式(tlabel_v2) ──→    ├─ RLDS（stub→正式）
VTouch ────┤              ↑                               ├─ ROS2 Bag（stub→正式）
YCB-Slide ─┤         TLabel Format Schema                 └─ 未来新格式...
UniVTAC ──┘          （传感器无关）                          ↑
                                                     Exporter Plugin Registry
                                                       （插件化注册，UI动态发现）
```

### 三层各自的职责

| 层 | 职责 | 代码位置 | 扩展方式 |
|----|------|---------|---------|
| **输入层（Adapter）** | 把各种传感器原始数据转成22维tlabel_v2 | `tlabel/adapters/` | 继承AdapterBase + register |
| **核心层（Schema）** | 定义22维统一格式、cascade规则、验证 | `tlabel/core/` + `tlabel/schema/` | RFC流程 |
| **输出层（Exporter）** | 把统一格式转成下游框架需要的格式 | `tlabel/export/` + `tlabel/converters/` | 继承ExporterBase + register |

---

## 二、关键文件索引

```
tlabel/
├── core/
│   ├── types.py          # TLabelData数据结构，22维特征定义
│   ├── loader.py         # tlabel.load() 入口，自动识别格式
│   └── registry.py       # 适配器注册表
├── adapters/             # 每种传感器一个文件（表驱动注册）
│   ├── base.py          # BaseAdapter 抽象基类
│   ├── gelsight.py      # GelSight Mini / DIGIT
│   ├── paxini_dataset.py # PaXini PXCap 数据集适配器
│   ├── paxini_gen3.py   # PaXini GEN3 实时传感器适配器
│   ├── daimon_dataset.py # Daimon DM-TacClaw 数据集适配器
│   ├── daimon_dm_tac.py # Daimon DM-Tac 实时传感器适配器（骨架）
│   ├── touchd.py        # ToucHD-Force
│   ├── vtouch.py        # 白虎-VTouch
│   ├── univtac.py       # UniVTAC
│   ├── ycb_slide.py     # YCB-Slide CMU DIGIT
│   ├── tacquad.py       # TacQuad AnyTouch
│   └── tlabel_format.py # 已有TLabel数据的直接加载
├── converters/           # 格式转换器（下游生态对接）
│   ├── ftp1.py           # FTP-1/MTTS Zarr导出
│   └── lerobot.py        # LeRobot Parquet导出
├── export/
│   ├── writer.py         # 基础导出：JSON/CSV/HDF5
│   └── registry.py       # Exporter Plugin Registry（v0.9.0）
├── predict/              # AI预标注引擎
│   ├── engine.py         # PredictEngine主类
│   ├── ml_engine.py      # 梯度提升ML
│   ├── hmm_detector.py   # HMM相位检测
│   └── post_process.py   # 后处理
├── quality/              # 数据质量评分
│   └── scorer.py         # QualityScorer（四维度）
├── batch/                # 多Episode批处理
│   └── processor.py      # BatchProcessor
├── viewer/               # Web UI面板
│   ├── panel.py          # Python入口，Jupyter集成
│   └── templates.py      # HTML/JS/CSS模板（Canvas渲染）
├── features_meta.py      # 22维特征元数据定义
└── schema/
    └── tlabel-schema.json # JSON Schema定义
```

---

## 三、核心设计原则（不可违反）

### 3.1 标准层原则
1. **22维特征空间是神圣的** —— 增删字段必须走RFC流程，不能直接在代码里改
2. **传感器无关** —— 核心层不知道传感器是什么，只知道22维向量
3. **Cascade联动规则** —— contact=0时7个字段自动归零，这个逻辑不能改
4. **向后兼容** —— 旧版本tlabel.json能被新版本load()正常读取

### 3.2 适配器层原则
1. **一个传感器一个文件** —— 不要把多个传感器塞到一个文件里
2. **适配器只负责"翻译"** —— 原始数据 → 22维tlabel_v2，不做质量判断
3. **必须有demo数据** —— 每个适配器都要有 `tlabel.demo('sensor_name')` 可调用
4. **必须有auto_detect支持** —— `tlabel.load()` 能自动识别该格式

### 3.3 导出层原则
1. **插件化注册** —— 新导出格式通过 `registry.register()` 注册，不改UI代码
2. **UI动态发现** —— Panel通过 `registry.list_formats()` 发现可用格式
3. **配置表单自动生成** —— 通过 `ExporterSpec.fields` 描述字段，UI自动渲染
4. **转换器 vs 导出器** —— `converters/` 是复杂的双向转换（如FTP-1 Zarr），`export/registry.py` 是轻量单向导出

### 3.4 可视化原则
1. **有真实图像就显示真实图像** —— GelSight等有图像数据的传感器，显示真实图像帧
2. **只有矩阵数据显示热图** —— 明确标注"Heatmap Visualization"，不假装是照片
3. **没有空间数据显示灰底** —— 灰底 + "该传感器无空间分辨率数据" + 显示有什么数据
4. **绝不误导用户** —— v0.9.0的伪GelSight可视化被移除就是因为"没图时假装有条"

---

## 四、开发前必做：确认最新版本（每次开发的第一步！）

> ⚠️ **绝对不要从本地代码猜版本。本地代码可能是几个月前的旧版本。**
> ⚠️ **绝对不要从GitHub tag猜版本。tag可能落后于实际发布版本。**
> ⚠️ **PyPI是唯一权威版本源。**

### 标准流程（每次开发前必须执行）

```bash
# 第一步：查PyPI最新版本（权威来源）
curl -s https://pypi.org/pypi/tlabel/json | python3 -c "import sys,json; d=json.load(sys.stdin); print('最新版本:', d['info']['version']); print('所有版本:', sorted(d['releases'].keys()))"

# 第二步：下载最新版本的完整源码
mkdir -p /tmp/tlabel-latest && cd /tmp/tlabel-latest
pip download tlabel==$(curl -s https://pypi.org/pypi/tlabel/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])") --no-deps -d .
# tar.gz就用tar xzf，whl就用unzip
```

### 为什么必须这样做？

| 信息来源 | 可靠度 | 历史教训 |
|----------|--------|---------|
| **PyPI** | ✅ 唯一权威 | — |
| GitHub tag | ⚠️ 可能落后 | tag v0.9.0 但实际是 0.10.2 |
| 本地代码 | ❌ 可能很旧 | 云电脑上是0.2.0，实际已经到0.10.2 |
| MEMORY.md | ⚠️ 看上次更新时 | 如果没人更新就会过时 |

### ⚠️ 历史教训：0.2.0事件

2026-07-01之前的某次开发，Agent在云电脑上找到了一份tlabel源码（0.2.0版本），以为是最新版，基于它开发了新功能并发布。实际上PyPI已经是0.9.0+了。导致：
- 新版本号从0.2.0开始，和实际版本线完全脱节
- 发布的内容覆盖了旧功能（UniVTAC适配器等）
- 版本线混乱，花了大量时间纠正

**永远不要重蹈覆辙。开发前，先查PyPI。**

---

## 五、开发SOP

### 4.1 新增传感器适配器

```
1. 创建 tlabel/adapters/{sensor_name}.py
2. 继承 AdapterBase，实现：
   - detect(file_path) → bool   # 判断是否是这种格式
   - load(file_path) → TLabelData  # 加载并转22维
3. 在 core/registry.py 的 _ADAPTER_MODULES 字典中加一行（表驱动注册）
   格式: "adapter_name": ("tlabel.adapters.module_name", "ClassName"),
4. 在 adapters/__init__.py 的 AVAILABLE_ADAPTERS 字典中添加描述
5. 添加 demo 数据生成函数（在 demo.py 的 AVAILABLE_SENSORS 列表中添加）
6. 在 core/loader.py 的 format 参数 docstring 和错误信息中添加
7. 更新 README 的传感器支持表
8. 版本号：MINOR bump（0.X.0）
```

> **v0.14起**: 适配器注册改为表驱动，只需在 `registry.py` 的 `_ADAPTER_MODULES` 加一行即可，
> 不再需要写 if-block。模块导入失败（缺少依赖）会被静默跳过。

### 4.2 新增导出格式

```
1. 创建 tlabel/export/{format_name}.py
2. 继承 ExporterBase，实现：
   - name: str
   - description: str
   - fields: List[ExportField]  # UI配置表单字段
   - export(data, output_path, **kwargs) → str
3. 调用 registry.register(YourExporter())
4. UI自动发现，不需要改panel.py或templates.py
5. 如果是复杂双向转换（如FTP-1 Zarr），放在 converters/ 目录
6. 版本号：MINOR bump
```

### 4.3 修改Schema（增删22维字段）

```
1. 复制 internal-docs/RFC-TEMPLATE.md
2. 填写提案：为什么加/改/删、影响范围、迁移方案
3. 保存为 internal-docs/rfc/{rfc-name}.md
4. 实现代码变更
5. 更新 schema/tlabel-schema.json
6. 更新 features_meta.py
7. 更新文档 docs/annotation-spec.md
8. 版本号：视影响 MAJOR 或 MINOR bump
```

### 4.4 修改Panel UI

```
1. panel.py 是Python入口（生成HTML）
2. templates.py 是前端代码（HTML/CSS/JS，1405行）
3. Canvas组件：
   - timeline_canvas: 时间轴 + 帧导航
   - radar_canvas: 22维雷达图
   - （未来）tactile_image_canvas: 触觉图像显示
4. 修改UI后必须测试：亮色/暗色模式、中英文切换
5. 版本号：PATCH bump（如果纯UI改动）
```

---

## 五、版本线约定

### 当前状态（2026-07-01）
- **PyPI最新稳定版**: v0.10.2
- **GitHub main分支**: 0.10.2（commit 3f27e34）
- **GitHub最新tag**: v0.9.0（⚠️ tag落后于实际版本，待补）

### 版本号规则
| 变更类型 | 版本变化 | 举例 |
|---------|---------|------|
| 修bug/文档/i18n | PATCH | 0.10.2 → 0.10.3 |
| 新增功能（不破坏旧API） | MINOR | 0.10.2 → 0.11.0 |
| 破坏性变更 | MAJOR | 0.10.2 → 1.0.0（v0.x阶段免MAJOR） |

### 双轨版本管理（2026-07-01 确定）

实际开发中会有两条并行的版本线，互不干扰：

| 轨道 | 用途 | 版本节奏 | 举例 |
|------|------|---------|------|
| **主线轨道** | Phase 2规划的核心功能（可视化、增强、ROS2等） | 按规划走，MINOR bump | 0.10.2 → 0.11.0 → 0.12.0 |
| **BD/适配器轨道** | 新数据包适配器、BD驱动的功能、社区需求 | 随来随发，PATCH bump | 0.10.2 → 0.10.3 → 0.10.4 |

**规则：**
- 主线功能和BD适配器**独立发布**，不按顺序排队
- BD来了→先出patch版本搞定→回来继续主线
- 如果BD适配器涉及较大新功能（不太常见），可以走MINOR bump，但不应阻塞主线
- 无论哪个轨道，发版前都必须执行"第四节：确认最新版本"流程
- PyPI版本号是线性递增的，两个轨道共用同一个版本号空间，不能冲突

### 发版流程
```
1. 更新 _version.py 版本号
2. 更新 CHANGELOG.md（按Keep a Changelog格式）
3. 运行全量测试
4. git commit（Conventional Commits格式）
5. 构建: python -m build
6. 发布PyPI: twine upload dist/*
7. 创建GitHub Release + tag
8. 验证: pip install tlabel==X.Y.Z
```

### ⚠️ 历史教训（必须避免）
- **0.2.0a8是alpha版，不是最新稳定版** —— 版本线是 0.1.0a → 0.2.0a/b → 0.3.0 → ... → 0.10.2
- **不要只看GitHub tag判断版本** —— tag v0.9.0落后于实际版本，以PyPI为准
- **版本号在三个地方要同步** —— _version.py + pyproject.toml + __init__.py

---

## 六、关键设计决策记录

### D1: 为什么伪GelSight可视化被移除？
- **背景**: v0.9.0实现了Canvas-based heatmap模拟GelSight图像
- **问题**: 当数据没有真实图像时，显示的是"假的"热力图，用户可能误以为是真实传感器图像
- **决策**: 移除伪可视化，改为灰底+"无图像数据"提示
- **未来方向**: 恢复时需要三级策略：真实图像 → 标注为"热图"的矩阵可视化 → 灰底提示

### D2: 为什么Exporter Plugin Registry和converters/并存？
- **export/registry.py**: 轻量单向导出（JSON/CSV/HDF5），UI集成
- **converters/**: 复杂双向转换（FTP-1 Zarr需要传感器选择、功能区映射等复杂配置）
- **原因**: Registry适合简单场景，converters适合需要精细控制的场景

### D3: 为什么22维不能随便加？
- **每个字段都有下游消费者** —— FTP-1/LeRobot/RLDS都依赖稳定的字段定义
- **加字段容易，删字段难** —— 一旦有数据集用了这个字段，就不能删
- **RFC流程保护的是下游兼容性**

### D4: 产品定位是"标准"不是"工具"
- **标准层**: 适配器 + Schema + 导出 → 这是核心，不能乱改
- **工具层**: AI预标注 + 质量评分 + 批处理 → 这是辅助，可以灵活迭代
- **可视化层**: Panel → 这是用户体验，目标是"让用户看到触觉数据"
- **三者关系**: 标准层是根，工具层和可视化层是帮用户用好标准的

---

## 七、Phase 2 功能规划（2026-07-01确定）

### 设计原则
> 有真实数据就显示真实数据，没有就不装。
> 让用户"进得来、看得到、出得去"。

### P0: 触觉图像序列可视化（v0.11.0）
- 有图像数据 → Canvas渲染真实图像帧序列
- 只有矩阵数据 → 热图可视化（明确标注）
- 无空间数据 → 灰底 + 说明
- 帧级播放控制：play/pause/speed/scrub
- 视频导出：`data.export_video("demo.mp4", fps=30)`

### P0: 数据增强工具（v0.12.0）
- 时序抖动（time_warp）
- 噪声注入（noise_inject）
- 随机裁剪（random_crop）
- 力缩放（force_scale）
- 帧丢弃（frame_dropout）
- API: `tlabel.augment(data, methods=[...])`

### P1: ROS2 bag适配器
- 输入：读取ROS2 bag文件提取触觉话题
- 输出：ROS2 Bag导出（从stub毕业）

### P1: RLDS正式实现
- 从stub毕业，对接Google DeepMind机器人数据标准

### P2: 多传感器并排对比视图
- Panel支持多数据源同时加载
- 时间轴同步

---

## 八、常见陷阱（踩过的坑不要再踩）

1. **版本号混乱** —— PyPI版本线是 0.1→0.2a→0.2b→0.3→...→0.10.2，不是从0.2.0a8开始的
2. **GitHub tag落后** —— 最新tag是v0.9.0但实际是0.10.2，以PyPI为准
3. **改schema不走RFC** —— 22维字段增删必须走RFC流程
4. **忘记i18n** —— 新增UI文本必须同时加中英文
5. **忘记暗色模式** —— 新增Canvas/HTML元素必须测试暗色模式
6. **Panel改了但没测试** —— 修改templates.py后必须test亮色/暗色/中英文四种组合
7. **适配器没demo** —— 每个适配器必须有 `tlabel.demo('name')` 可调用
8. **构建环境** —— 从PyPI下载源码用 `pip download tlabel==X.Y.Z --no-deps -d .` 然后 `tar xzf` 或 `unzip`

---

## 九、凭证信息

> ⚠️ 凭证信息不在仓库中维护，由 Agent 运行时从安全存储读取。
> GitHub Token / PyPI Token 等敏感信息请参见 Agent 内部 SECRET.md。

- **GitHub repo**: liesliy/tlabel

---

## 十、相关文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| RFC流程 | `internal-docs/RFC-README.md` | Schema变更的治理流程 |
| RFC模板 | `internal-docs/RFC-TEMPLATE.md` | RFC提案模板 |
| 版本规划 | `TLabel版本规划.md` | v0.4→v0.5→v1.0路线图 |
| 推广计划 | `TLabel推广计划（完整版）.md` | 四阶段推广策略 |
| 需求清单 | `TLabel需求清单.md` | 待开发需求列表 |
| 偏航分析 | `TLabel标准偏航分析_v0.8.0_20260628.md` | 功能vs定位审查 |
| 战略分析 | `TacEva与事实标准战略分析.md` | 竞品分析与应对策略 |
| 功能规划 | `internal-docs/TLabel功能规划与标准推广兼容性分析_20260629.md` | 功能全景+用户画像 |
| CHANGELOG | `CHANGELOG.md` | 版本变更记录 |
| 发版规范 | `TLabel发版规范与平台规则.md` | PyPI/GitHub发版SOP |
