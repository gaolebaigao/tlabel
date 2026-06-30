# Changelog

## [0.10.0] - 2026-06-29

### Added
- **YCB-Slide Adapter** (`tlabel/adapters/ycb_slide.py`) — CMU RPL MidasTouch (CoRL 2022) dataset support
  - Supports both **real** data (`synced_data.npy`) and **simulated** data (`tactile_data.pkl`)
  - Auto-detection: recognizes YCB-Slide directory structure (`synced_data.npy` or `tactile_data.pkl` patterns)
  - Extracts 22-dim TLabel v2 features from DIGIT tactile images (background subtraction, contact detection)
  - Preserves sensor/object poses (6-DoF: position + quaternion)
  - Manipulation phase inference (approach → stable_contact → slip → release)
  - `pip install tlabel[ycb_slide]` for sim data support (requires `dill`)
- Auto-detect YCB-Slide directories in `tlabel.load()` format detection
- Loader error messages now include `format='ycb_slide'` hint

### Usage
```python
import tlabel

# Auto-detect from directory
data = tlabel.load("dataset/real")

# Explicit format
data = tlabel.load("dataset/real", format="ycb_slide")

# Specific object + dataset
data = tlabel.load("dataset/real", format="ycb_slide", trajectory_id=0)
```

## [0.9.0] - 2026-06-29

### Added
- **Panel Phase 1 — 5 major UI/UX features**
  - Pseudo GelSight tactile image visualization (Canvas-based heatmap with radial gradient)
  - Keyboard shortcuts: Space=toggle, ←→=frame nav, ↑↓=label adjust
  - Timeline click-to-jump + drag-to-select for frame range editing
  - AI pre-annotation button with confidence threshold
  - Unified Export Center tab (replaces scattered export buttons)
- **Exporter Plugin Registry** (`tlabel/export/registry.py`, 760 lines)
  - `ExporterBase` abstract base class
  - `ExporterSpec` / `ExportField` self-describing metadata
  - `ExporterRegistry` with dynamic `register()` / `unregister()`
  - 7 built-in formats: JSON, CSV, HDF5, FTP-1, LeRobot, RLDS(stub), ROS2(stub)
  - `to_dict()` serialization for UI form rendering
  - `list_targets()` for format-specific metadata (e.g. sensor lists)
  - Fully backward compatible with legacy `export_data()` API

### Changed
- Version bump: 0.8.0 → 0.9.0
- Keywords: added MTTS-1, panel, visualization

## [0.8.0] - 2026-06-28

### Added
- **FTP-1/MTTS 格式导出** — 触觉基础模型通用数据接口
  - `tlabel/converters/ftp1.py` — 完整转换器，支持Zarr格式导出
  - `data.export_ftp1()` — 一行代码导出FTP-1兼容格式
  - 21个MTTS功能区定义（手部15 + 力矩6）
  - 7种已知传感器注册（GelSight/GelSightMini/FreeTacMan/ViTAMIn/3DViTac/Contactile/BinaryContact）
  - 4种功能区预设映射（夹爪/三指/五指/灵巧手）
  - 支持image/matrix/binary三种触觉模态
  - 自动图像缩放至224×224 + uint8/float32归一化
  - 支持追加模式（多Episode合并到同一Zarr）
  - `batch_to_ftp1()` — 批量导出工具
- **UI 新增"导出"Tab** — 面板新增🚀导出标签
  - FTP-1传感器选择器（7种传感器下拉）
  - 功能区映射可视化配置（21个可勾选槽位）
  - 3种预设按钮（夹爪/三指/五指）
  - 安装位置/组名选择器
  - 导出结果预览（含Python命令生成）
  - MTTS Zarr格式参考文档

### Changed
- Version bump: 0.7.0 → 0.8.0

### FTP-1 Zarr 输出格式
```
right_tactile_data_gripper:   (T, N, H, W, 3) uint8   # 触觉图像
right_tactile_area_gripper:   (T, N) int32             # 功能区ID
right_tactile_sensor_gripper: (T,) string              # 传感器名
right_tactile_type_gripper:   (T,) string              # image/matrix/binary
```

### 用法示例
```python
from tlabel import demo

data = demo('gelsight')
data.export_ftp1("output.zarr",
                  sensor_name="GelSightMini",
                  functional_areas=[0, 1],  # 拇指尖+食指尖
                  side="right")
```

## [0.6.2] - 2026-06-24

### Added
- `tlabel.demo('touchd')` — ToucHD-Force demo data (100 frames, simulated press sequence)
- `tests/release_regression.py` — Release regression test script (run before every release)
- ToucHD demo covers full phase sequence: idle -> initial_contact -> stable_contact -> slip -> release

### Fixed
- Fix missing `_version.py` in wheel package (v0.6.0 was incomplete)
- Fix missing submodules (batch/predict/quality/export/converters/viewer) in wheel


## [0.6.2] - 2026-06-24

### Added
- **ToucHD-Force adapter** (`tlabel/adapters/touchd.py`) - AnyTouch 2 (ICLR 2026)
  - 4 sensors: DIGIT, BioTip, GelSight, DuraGel
  - 3D contact force ground truth (Fx, Fy, Fz) with sensor-specific normalization
  - Action labels (press, slide, etc.) + left/right hand image selection
  - 22-dim TLabel v2 feature extraction + force-driven slip detection
  - Optical flow computation (Farneback) when cv2 available
  - Manipulation phase inference (idle -> initial_contact -> stable_contact -> slip -> release)
- Auto-detect ToucHD directories (via `all_data_direction.json`)
- `tlabel.load()` now supports `format="touchd"` with `sensor`, `obj_id`, `hand` params
- `pip install tlabel[touchd]` optional dependency group


All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2025-01-XX

### Fixed
- **i18n补全**：热力图和统计页面中文适配
  - 雷达图维度标签（22维特征）使用i18n国际化
  - 统计摘要表格（describe）的行名和列名支持中英文切换
  - 新增 `dim.*` 和 `stats.*` i18n key
- **深色模式数字不可读**：统计页和质量页在暗色模式下数字颜色修复
  - `renderDescribe()` 和 `renderQuality()` 根据 `isDark` 变量选择颜色
  - 切换暗色模式后自动重新渲染统计数据
- **Episode语义标注保存反馈优化**
  - 反馈持续时间从2秒延长至4秒
  - 反馈信息更详细，显示"Episode标注已保存（将随导出数据一起输出）"
  - 保存按钮点击后短暂禁用，防止重复点击

### Changed
- **QUICKSTART.md** 全面更新，使用 v0.5.0+ API
  - 新增 `tlabel.demo()` 快速体验
  - 更新数据加载方式为 `tlabel.load()`
  - 新增 AI 预标注（PredictEngine）说明
  - 更新 VTouch 数据格式支持说明

## [0.5.0] - 2024-12-XX

### Added
- **AI 预标注功能**（PredictEngine）
  - 基于规则的自动标注
  - 预测结果高亮显示（🤖 徽章）
  - 支持时序平滑和HMM解码
- **预测方法标签**
  - 面板显示当前使用的预测方法
  - 支持手动修正预测结果
- **自动标签摘要**
  - 显示自动标签统计信息
  - 支持批量应用和撤销

### Changed
- 优化雷达图渲染性能
- 改进时间轴点击响应
- 优化批量修正的用户体验

## [0.4.2] - 2024-11-XX

### Added
- **Episode 级语义标注**
  - 操作结果（成功/失败/中止/部分）
  - 操作类型（抓取/推动/拉取/轻触等）
  - 难度等级（简单/中等/困难）
  - 备注字段
- **数据质量评分仪表盘**
  - 4维度评估（物理一致性、时序平滑度、完整性、覆盖率）
  - 综合评分和等级显示
  - 质量警告提示
- **统计摘要表格**
  - 类似 pandas DataFrame.describe()
  - 支持 count, mean, std, min, 25%, 50%, 75%, max

### Changed
- 面板样式优化
- 暗色模式支持
- 中英文切换优化
