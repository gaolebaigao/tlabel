<div align="center">

# 🦞 TLabel

**统一的触觉数据标注标准与工具集**

加载任意传感器 · 统一格式标注 · 多框架导出

[![PyPI](https://img.shields.io/pypi/v/tlabel?color=e85d75&label=PyPI)](https://pypi.org/project/tlabel/)
[![Python](https://img.shields.io/pypi/pyversions/tlabel)](https://pypi.org/project/tlabel/)
[![License](https://img.shields.io/pypi/l/tlabel)](LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel?color=blue)](https://pepy.tech/projects/tlabel)
[![English](https://img.shields.io/badge/README-English-blue)](README.md)

</div>

---

## TLabel 是什么？

每个触觉传感器都有自己的数据格式。TLabel 定义了一套**统一的标注 Schema**（14 个语义维度，4 级合规等级），并提供**适配器**将各传感器格式自动转换为统一标准。

```
 GelSight .pkl ──┐                        ┌── JSON / CSV
 PaXini .h5 ─────┤   TLabel 适配器         ├── FTP-1 Zarr
 Daimon .parquet─┤   ─────────────────►   ├── LeRobot / RLDS
 VTouch .h5 ─────┤                        └── ROS2
 任意格式 ────────┘
```

类比：**触觉数据的 Unicode** —— 一套标准，所有传感器通用。

---

## 快速开始

```bash
pip install tlabel
```

```python
import tlabel

# 加载数据（自动识别传感器格式）
data = tlabel.load("path/to/data")

# 或体验内置 demo（无需任何文件）
data = tlabel.demo("gelsight")

# 查看标注元数据
print(data.describe())
# -> {'num_frames': 500, 'sensor': 'gelsight', 'compliance_level': 'L2', ...}

# 打开交互式标注面板（Jupyter）
data.review()

# 导出
data.export("output.json")
data.export_ftp1("out.zarr")
```

```bash
# CLI 命令
tlabel list                    # 查看所有已注册适配器
tlabel info gelsight           # 查看适配器详情
tlabel validate data.json      # Schema 合规性检查
```

### 安装可选依赖

```bash
pip install tlabel[gelsight]   # opencv-python
pip install tlabel[paxini]     # h5py
pip install tlabel[daimon]     # pyarrow + opencv-python
pip install tlabel[ftp1]       # zarr（FTP-1 导出）
pip install tlabel[all]        # 全部
```

---

## Schema V2 — 14 维度，4 级合规

TLabel Schema V2 定义了 **14 个语义维度**，通过 **合规等级（L1–L4）** 标注数据完整度：

| # | 维度 | 类型 | 要求 |
|---|------|------|------|
| 1 | `contact` | bool | ✅ 必填 |
| 2 | `contact_centroid` | [float × 2] | ✅ (有接触时) |
| 3 | `force_magnitude` | float | ✅ (L2+) |
| 4 | `slip_event` | bool | ✅ 必填 |
| 5 | `confidence` | float | ✅ 必填 |
| 6 | `compliance_level` | L1 / L2 / L3 / L4 | ✅ 必填 |
| 7 | `contact_region` | enum | 可选 |
| 8 | `force_vector` | [float × 3] | 可选 (L3+) |
| 9 | `torque_vector` | [float × 3] | 可选 |
| 10 | `slip_velocity` | [float × 2] | 可选 |
| 11 | `manipulation_phase` | enum | 可选 |
| 12 | `texture_class` | enum | 可选 |
| 13 | `object_deformation` | float | 可选 |
| 14 | `temperature` | float | 可选 |

**合规等级说明：**
- **L1** — 接触 + 滑动 + 置信度（最小标注集）
- **L2** — L1 + 力大小（力感知）
- **L3** — L2 + 力向量（完整 3D 接触力）
- **L4** — L3 + 所有可选字段（完整标注）

📖 完整规范 → [docs/annotation-spec.md](docs/annotation-spec.md) · Schema JSON → [schema/tlabel-schema.json](schema/tlabel-schema.json)

---

## 支持的传感器

### 数据集适配器（离线数据加载）

| 传感器 | 类型 | 格式 | 合规等级 |
|:-------|:-----|:-----|:--------:|
| GelSight Mini / DIGIT | 视觉式 | `.pkl` | L3 |
| Daimon DM-TacClaw | 多模态 | `.parquet` | L3 |
| PaXini PXCap | 力阵列 | `.h5` | L2 |
| UniVTAC | 视觉式 | `.hdf5` | L3 |
| TacQuad (AnyTouch) | 多传感器 | directory | L3 |
| VTouch | 视觉式 | `.h5` | L3 |
| YCB-Slide | 视觉式 | `.npy` | L3 |
| XELA uSkin (UniTac-NV) | 3轴 taxel 力阵列 | `.csv` | L1 |

### 实时传感器适配器（硬件直连）

| 传感器 | 类型 | 连接方式 | 合规等级 |
|:-------|:-----|:---------|:--------:|
| PaXini GEN3 | 力阵列 | SDK | L2 |
| Daimon DM-Tac | 视觉式 | USB / `.avi` | L3 |

---

## 架构

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Schema                                │
│  14 维语义标准 + 合规等级 (L1-L4)               │
├─────────────────────────────────────────────────┤
│  Layer 2: Adapters                              │
│  DataAdapterBase │ SensorAdapterBase             │
│  （7 个内置 + 社区可扩展）                       │
├─────────────────────────────────────────────────┤
│  Layer 3: Downstream                            │
│  特征派生 · 数据增强 · 导出                       │
│  PredictEngine · FTP-1 · LeRobot · RLDS · ROS2 │
└─────────────────────────────────────────────────┘
```

- **DataAdapterBase** — 继承此类添加文件型传感器支持（~30 分钟）
- **SensorAdapterBase** — 继承此类添加实时硬件支持
- 两者共享统一的导出管线

---

## 导出格式

| 格式 | 用途 | 用法 |
|------|------|------|
| JSON / CSV | 通用分析 | `data.export("out.json")` |
| FTP-1 Zarr | 基础模型训练 | `data.export_ftp1("out.zarr")` |
| LeRobot | LeRobot 框架 | `from tlabel.converters import tlabel_to_lerobot` |
| RLDS | RLDS/TFDS 管线 | `tlabel.converters.rlds` 模块 |
| ROS2 | 机器人运行时 | Stub（即将支持） |

---

## 核心能力

| 能力 | 说明 |
|------|------|
| 🤖 **AI 预标注** | `PredictEngine` 自动标注接触、滑动、操作阶段 |
| 📈 **数据增强** | 5 种方法（time_warp, noise, crop, scale, dropout） |
| 🌐 **交互面板** | 中英双语 Jupyter 标注面板 |
| 🔌 **开放平台** | 社区适配器通过 `entry_points` 自动发现 |

---

## 参与贡献

TLabel 天生可扩展。30 分钟即可添加你的传感器：

1. Fork [contrib/adapter-template/](contrib/adapter-template/)
2. 继承 `DataAdapterBase` 或 `SensorAdapterBase`
3. 提交 PR 或作为独立包发布

📖 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 引用

```bibtex
@software{tlabel2026,
  title  = {TLabel: A Sensor-Agnostic Tactile Data Annotation Toolkit and Format Standard},
  author = {Wu, Sheng and Luo, Xi},
  year   = {2026},
  url    = {https://github.com/liesliy/tlabel}
}
```

---

## 许可证

[MIT](LICENSE) © 2026 牛宿科技

---

<div align="center">

**如果 TLabel 对你的触觉数据工作有帮助，欢迎给个 ⭐**

[⭐ Star](https://github.com/liesliy/tlabel/stargazers) · [📦 PyPI](https://pypi.org/project/tlabel/) · [💬 Discord](https://discord.gg/2ab8EWaBM)

**技术服务：** 定制适配器开发 · 数据管线咨询 · 具身智能工具链
**联系：** 微信 `wxid_olqx5z6trmtn21` · 邮箱 `luoxi@touchlabelai.cn`

</div>
