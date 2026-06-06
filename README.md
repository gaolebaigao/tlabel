# TouchLabel AI 🦞

<h3 align="center">传感器无关的触觉数据标注工具</h3>
<p align="center"><strong>load → review → export · 三步闭环</strong></p>

<p align="center">
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/v/tlabel?color=e85d75" alt="PyPI"></a>
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/pyversions/tlabel" alt="Python"></a>
  <a href="https://github.com/liesliy/tlabel/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/tlabel" alt="License"></a>
</p>

![TouchLabel AI Panel Demo](docs/demo_panel.gif)

---

## 🚀 Quick Start

```bash
pip install tlabel
```

```python
import tlabel

# 1️⃣ 加载 — 自动识别传感器格式
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # PaXini
data = tlabel.load("daimon_data/")           # Daimon (目录或 .parquet)

# 2️⃣ 标注 — Jupyter 交互面板
data.review()          # 中文界面
data.review(lang="en") # English

# 3️⃣ 导出
data.export("output.json")   # TLabel Format v2 JSON
data.export("output.csv")    # CSV 平面表
```

<details>
<summary>📥 用 Demo 数据试一下</summary>

```bash
pip install tlabel
python -c "
import json, urllib.request
from tlabel.core.types import TLabelFrame, TLabelData

url = 'https://raw.githubusercontent.com/liesliy/tlabel/main/examples/data/demo_gelsight.json'
raw = json.loads(urllib.request.urlopen(url).read())
frames = [TLabelFrame(f['frame_idx'], f['timestamp_s'], f['tlabel_v2'], f.get('manipulation_phase','idle'), f.get('confidence',1.0)) for f in raw['frames']]
data = TLabelData(frames, raw['sensor'], raw['episode'], raw['capabilities'])
data.review()
"
```

</details>

---

## 📡 Supported Sensors

| Sensor | Format | Dimensions | Optical Flow | Status |
|--------|--------|:----------:|:------------:|:------:|
| **GelSight Mini** | `.pkl` | 22 | ✅ | ✅ Stable |
| **DIGIT** | `.pkl` | 22 | ✅ | ✅ Stable |
| **Daimon DM-TacClaw** | `.parquet` / dir | 22 | ✅ (video) / 20 (no video) | ✅ Stable |
| **PaXini PXCap** | `.h5` / `.hdf5` | 20 | — | ✅ Stable |

> **22 维 vs 20 维**：力觉型传感器（PaXini）无光学图像，不支持光流特征；图像型传感器全量 22 维。
> Daimon 在无视频文件时自动降级为 20 维。

---

## 📦 Installation

```bash
# 基础安装（仅 numpy）
pip install tlabel

# 按传感器装可选依赖
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[daimon]     # Daimon → pyarrow + opencv-python

# 一步到位
pip install tlabel[all]
```

---

## 🎨 Panel Features

- 🎨 **彩色时间轴**：绿=接触 · 红=滑移 · 灰=无接触
- 🕸 **22维雷达图**：TLabel Format v2 全维度可视化，中英文标注
- ✏️ **帧修正 & 批量 patch**：选中区间一键修改，联动规则自动清除关联字段
- 🔗 **Cascade 联动**：`contact=0` 时自动归零 7 个力/滑移/面积字段 + `manipulation_phase→idle`
- 🌐 **中英文切换**：面板右上角一键切换
- 📤 **导出**：JSON / CSV，后缀自动判断格式

---

## TLabel Format v2 — 22 Dimensions

### Static Features (18-dim)

| # | Key | 中文 | Description |
|---|-----|------|-------------|
| 1 | `contact` | 接触状态 | Binary contact flag |
| 2 | `deformation_magnitude` | 形变幅度 | Surface deformation intensity |
| 3 | `force_magnitude` | 力度 | Normal force magnitude |
| 4 | `force_peak` | 力峰值 | Peak force in episode window |
| 5 | `force_direction` | 力方向 | Force vector angle (°) |
| 6 | `slip_entropy` | 滑移熵 | Uncertainty of slip detection |
| 7 | `slip_event` | 滑移事件 | Binary slip event flag |
| 8 | `texture_energy` | 纹理能量 | Surface texture frequency energy |
| 9 | `edge_density` | 边缘密度 | Contact edge pixel ratio |
| 10 | `contact_area` | 接触面积 | Contact region area ratio |
| 11 | `centroid_x` | 质心X | Contact centroid x-position |
| 12 | `normal_field_magnitude` | 法向场幅度 | Normal pressure field magnitude |
| 13 | `normal_field_variance` | 法向场方差 | Normal field spatial variance |
| 14 | `shear_field_magnitude` | 剪切场幅度 | Shear stress magnitude |
| 15 | `shear_field_direction` | 剪切场方向 | Shear direction angle (°) |
| 16 | `delta_force_normal` | 法向力变化 | Frame-to-frame ΔF_normal |
| 17 | `delta_force_shear` | 剪切力变化 | Frame-to-frame ΔF_shear |
| 18 | `friction_cone_ratio` | 摩擦锥比 | Tangential/normal force ratio |

### Temporal Features (4-dim, v0.2.0)

| # | Key | 中文 | Image-type | Force-type | Description |
|---|-----|------|:----------:|:----------:|-------------|
| 19 | `optical_flow_magnitude` | 光流幅度 | ✅ | — | Inter-frame motion magnitude (Farneback) |
| 20 | `optical_flow_direction` | 光流方向 | ✅ | — | Optical flow angle (°) |
| 21 | `temporal_deformation_rate` | 形变速率 | ✅ | ✅ | Rate of deformation change |
| 22 | `contact_transition` | 接触转换 | ✅ | ✅ | Contact state transition probability |

---

## 📖 API Quick Reference

```python
import tlabel

# ── Loading ──
data = tlabel.load(path)                     # Auto-detect sensor format
data = tlabel.load(path, format="gelsight")  # Force specific adapter

# ── Properties ──
data.num_frames        # int — total frame count
data.duration_s        # float — episode duration
data.sensor_type       # str — sensor identifier
data.dimension_keys    # list — all dimension keys for this sensor
data.modified_count    # int — frames with manual patches

# ── Frame Access ──
frame = data[0]                          # Index access
frame = data.get_frame(42)               # By frame_idx
frame.contact                            # Contact value
frame.slip_event                         # Slip event value
frame.is_modified                        # Has patches?

# ── Patching ──
frame.patch("contact", 0)                         # Single frame (cascade=True)
frame.patch("contact", 0, cascade=False)           # No cascade
data.batch_patch(10, 50, "contact", 0)             # Range patch
data.batch_patch(10, 50, "slip_event", 1)          # With cascade

# ── Review & Export ──
data.review()                    # Jupyter panel (Chinese)
data.review(lang="en")           # English
data.export("output.json")       # JSON (TLabel Format v2)
data.export("output.csv")        # CSV
```

### Cascade Rules (contact → 0)

When `contact` is set to `0`, these fields are automatically zeroed:

| Auto-zeroed Field | Condition |
|-------------------|-----------|
| `force_magnitude` | always |
| `force_peak` | always |
| `slip_event` | always |
| `delta_force_normal` | always |
| `delta_force_shear` | always |
| `contact_area` | always |
| `contact_transition` | only if value > 0.5 |
| `manipulation_phase` | → `"idle"` (if not already) |

---

## 🗂 Project Structure

```
tlabel/
├── core/
│   ├── types.py          # TLabelFrame / TLabelData containers
│   ├── loader.py         # Auto-detect & dispatch loading
│   └── registry.py       # Adapter registry
├── adapters/
│   ├── base.py           # BaseAdapter interface
│   ├── gelsight.py       # GelSight Mini / DIGIT
│   ├── paxini.py         # PaXini PXCap
│   └── daimon.py         # Daimon DM-TacClaw (+ video decoding)
├── viewer/
│   ├── panel.py          # Jupyter _repr_html_ renderer
│   └── templates.py      # HTML + JS + CSS template engine
└── export/
    └── writer.py         # JSON / CSV export + NumpyEncoder
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Good first issues:**
- 🔌 Add a new sensor adapter (e.g., SynTouch, XELA)
- 📊 Improve radar chart UI (dark mode, interactive hover)
- 🌐 Add more language support (日本語, 한국어)
- 🧪 Add integration tests for edge cases

---

## 📄 License

[MIT](LICENSE) © Niuzu Tech (牛宿科技)

---

<p align="center">
  <strong>Star us ⭐ if it helps your research!</strong>
</p>
