<div align="center">

# 🦞 TouchLabel AI

### **全球首个传感器无关的触觉数据标注工具**

**加载任意触觉传感器 → 可视化标注 → 导出统一标准**

[![PyPI](https://img.shields.io/pypi/v/tlabel?color=e85d75&label=PyPI)](https://pypi.org/project/tlabel/)
[![Python](https://img.shields.io/pypi/pyversions/tlabel?label=Python)](https://pypi.org/project/tlabel/)
[![License](https://img.shields.io/pypi/l/tlabel?label=License)](https://github.com/liesliy/tlabel/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel?color=blue&label=Downloads)](https://pepy.tech/projects/tlabel)
[![GitHub Stars](https://img.shields.io/github/stars/liesliy/tlabel?style=social)](https://github.com/liesliy/tlabel/stargazers)
[![English](https://img.shields.io/badge/Docs-English-blue)](README.md)

**GelSight · DIGIT · 帕西尼 · 戴盟 — 一个工具，一种格式，全部传感器**

[🚀 快速上手](#-快速上手) · [📡 传感器](#-支持的传感器) · [🤝 贡献](#-贡献)

</div>

---

> ⚠️ **v0.17.0 破坏性更新** — 仅支持 Schema V2。旧版 22 维 `tlabel_v2` 格式已移除，所有数据统一使用 14 维 Schema V2 + Compliance Level (L1-L4)。详见 [MIGRATION.md](MIGRATION.md) 迁移指南。

---

> *触觉数据不应该被锁在任何一家公司的格式里。正如 RGB 图像不属于任何相机厂商，触觉数据也应该有统一的"Unicode"。TLabel 做的就是这件事——定义触觉数据的通用语言，然后把它交给所有人。*

---

## 🚀 快速上手

```bash
pip install tlabel
```

```python
import tlabel

# 加载任意传感器数据——自动识别格式
data = tlabel.load("path/to/your/data")

# 或试试内置演示（30秒体验）
data = tlabel.demo("gelsight")

# 在 Jupyter 中打开交互式标注面板
data.review()

# 导出为统一格式
data.export("output.json")      # JSON（tlabel_v2 标准）
data.export("output.csv")       # CSV
data.export_ftp1("out.zarr")    # FTP-1 Zarr（基础模型就绪）
```

### CLI 命令行工具

```bash
tlabel version               # 查看版本
tlabel list                  # 列出所有已注册适配器
tlabel info gelsight         # 查看适配器详情与能力
tlabel validate your_data.json  # 校验 tlabel_v2 schema 兼容性
```

---

## 🎯 TLabel 做什么？

**问题：** 每个触觉传感器的数据格式都不一样。换传感器 = 重写代码。

**解决方案：** TLabel 定义了统一的 22 维特征空间（[tlabel_v2](docs/annotation-spec.md)），通过适配器将每种传感器的原始数据翻译进来。

```
GelSight .pkl ──┐                    ┌── JSON（tlabel_v2）
PaXini .h5 ─────┤   TLabel 适配器     ├── CSV
Daimon .parquet─┤   ──────────────►  ├── FTP-1 Zarr
VTouch .h5 ─────┤                    ├── LeRobot
任意格式 ────────┘                    └── ROS2（开发中）
```

### 核心能力

| 功能 | 说明 |
|------|------|
| 🔌 **9个内置适配器** | 7个数据集适配器（文件加载）+ 2个实时适配器（SDK/USB）——开放社区扩展 |
| 🏗️ **开放平台** | `DataAdapterBase`（数据集）+ `SensorAdapterBase`（实时传感器）——任何人可贡献 |
| 🛠️ **CLI 校验** | `tlabel validate` 一键检查数据是否符合 22 维 schema |
| 🤖 **AI 预标注** | `PredictEngine` 自动标注接触、滑移、操作阶段 |
| 📈 **数据增强** | 5种方法（time_warp/noise/crop/scale/dropout），纯 numpy 零依赖 |
| 📤 **多格式导出** | JSON、CSV、FTP-1 Zarr、LeRobot、RLDS、ROS2 |
| 🌐 **双语面板** | 交互式 Jupyter 标注面板（中/英切换） |

### API 速览

```python
# 加载
data = tlabel.load(path)                     # 自动识别格式
data = tlabel.load(path, format="paxini")    # 指定适配器

# 标注修正
frame = data[0]
frame.patch("contact", 0)                    # 联动规则自动生效
data.batch_patch(10, 50, "slip_event", 1)   # 批量区间修正

# AI 预标注
from tlabel.predict import PredictEngine
engine = PredictEngine()
engine.fit(data)                             # 从部分标签热启动
results = engine.predict(data)
engine.apply(data, results, min_confidence=0.7)

# 数据增强
augmented = tlabel.augment(data, methods=["time_warp", "noise_inject"], seed=42)
```

📖 **完整 API** → [docs/API.md](docs/API.md) · **22维 Schema** → [docs/annotation-spec.md](docs/annotation-spec.md)

---

## 📡 支持的适配器

TLabel 提供两种适配器——加载已有数据，或连接实时硬件。

### 数据集适配器 — 加载已有触觉数据

> 基类：`DataAdapterBase` · 输入：文件路径 · 场景：公开数据集研究、历史数据处理

| 传感器 | 类型 | 文件格式 | 维度 | 状态 |
|:-------|:-----|:---------|:----:|:----:|
| **GelSight Mini / DIGIT** | 视触觉 | `.pkl` | 22 | ✅ 稳定 |
| **Daimon DM-TacClaw** | 多模态 | `.parquet` / dir | 22 | ✅ 稳定 |
| **PaXini PXCap** | 力阵列 | `.h5` / `.hdf5` | 20 | ✅ 稳定 |
| **UniVTAC** | 视触觉 | `.hdf5` | 22 | ✅ 稳定 |
| **TacQuad (AnyTouch)** | 多传感器 | directory | 22 | ✅ 稳定 |
| **VTouch** | 视触觉 | `.h5` | 22 | ✅ 稳定 |
| **YCB-Slide** | 视触觉 | `.npy` / dir | 22 | ✅ 稳定 |

### 实时传感器适配器 — 连接硬件设备

> 基类：`SensorAdapterBase` · 输入：SDK / USB / 数据流 · 场景：实验室机器人、产线、实时标注

| 传感器 | 类型 | 连接方式 | 维度 | 状态 |
|:-------|:-----|:---------|:----:|:----:|
| **PaXini GEN3** | 力阵列 | SDK（实时流） | 18 | 🆕 新增 |
| **Daimon DM-Tac** | 视触觉 | USB / `.avi` / `.bag` | 22 | 🆕 骨架 |

### 我该贡献哪种适配器？

- **我有采集好的数据文件** → 继承 `DataAdapterBase`，实现文件解析
- **我有一台物理传感器** → 继承 `SensorAdapterBase`，实现 SDK/流连接
- 两种适配器共享同一套导出管线——注册后 `tlabel.load()` 自动识别

> 视觉传感器 → 完整 22 维。力传感器（PaXini）→ 20 维。**无报错，优雅降级。**

```bash
# 按传感器安装依赖
pip install tlabel[gelsight]   # opencv-python
pip install tlabel[paxini]     # h5py
pip install tlabel[daimon]     # pyarrow + opencv-python
pip install tlabel[all]        # 全部安装
```

---

## 🆕 更新亮点

### v0.16.0 — 开放平台架构

TLabel 正式成为**开放、可扩展的平台**：
- 🏗️ 双基类架构（`DataAdapterBase` / `SensorAdapterBase`）
- 🔌 外部适配器注册：`entry_points` 自动发现，第三方包即装即用
- 🛠️ CLI 工具：`tlabel validate / list / info / version`
- 📦 社区贡献工具包：模板 + PR模板 + [CONTRIBUTING.md](CONTRIBUTING.md)

📖 **完整更新日志** → [CHANGELOG_current.md](CHANGELOG_current.md)

---

## 🤝 贡献

**TLabel 是一个开放平台——任何人都可以为它扩展传感器支持。**

| 参与方式 | 耗时 | 价值 |
|----------|------|------|
| **提交 PR** — 使用 `contrib/adapter-template/`，继承基类实现 3 个方法 | ~30分钟 | 你的传感器接入整个生态 |
| **发布独立包** — 通过 `tlabel` entry_points 自动发现 | ~1小时 | 无需PR，完全独立 |
| **其他** — Bug修复、文档、测试、UI改进 | 不定 | 永远欢迎 |

| 当前生态 | 数量 |
|----------|------|
| 内置适配器 | 9 |
| 社区适配器 | 0 *（等你来填？）* |

📖 **开始贡献** → [CONTRIBUTING.md](CONTRIBUTING.md) · **适配器模板** → [contrib/adapter-template/](contrib/adapter-template/)

---

## 🏆 基准测试

**[TLabel-Bench](https://github.com/liesliy/tlabel-bench)** — 首个跨传感器统一触觉标注基准。同样物体、不同传感器、一种格式。

---

## 📝 引用TLabel

```bibtex
@software{tlabel2026,
  title = {TLabel: A Sensor-Agnostic Tactile Data Annotation Toolkit},
  author = {NiuZhu Tech},
  year = {2026},
  url = {https://github.com/liesliy/tlabel}
}
```

---

## 📄 许可证

[MIT](LICENSE) © 牛宿科技

---

<div align="center">

**如果TLabel帮你省下了手动标注触觉数据的时间，给个⭐让我们开心一下！**

[⭐ GitHub加星](https://github.com/liesliy/tlabel/stargazers) · [📦 PyPI](https://pypi.org/project/tlabel/) · [🏆 基准测试](https://github.com/liesliy/tlabel-bench) · [💬 Discord](https://discord.gg/2ab8EWaBM)

</div>

---

## 🤝 需要触觉数据方面的帮助？

我们提供专业的触觉数据标注和处理服务：
- **传感器适配器开发** — 几天内让你的传感器接入 TLabel
- **数据流程咨询** — 为抓取、操作、滑移检测等任务设计标注工作流
- **具身智能数据方案** — 从原始传感器到模型可用数据的端到端方案

**联系我们：** 微信 `wxid_olqx5z6trmtn21` · 邮箱 `luoxi@touchlabelai.cn`
