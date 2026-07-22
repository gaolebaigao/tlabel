<div align="center">

# 🦞 TouchLabel AI

### **The World's First Sensor-Agnostic Tactile Data Annotation Toolkit**

**Load any tactile sensor → Annotate visually → Export a unified schema**

[![PyPI](https://img.shields.io/pypi/v/tlabel?color=e85d75&label=PyPI)](https://pypi.org/project/tlabel/)
[![Python](https://img.shields.io/pypi/pyversions/tlabel?label=Python)](https://pypi.org/project/tlabel/)
[![License](https://img.shields.io/pypi/l/tlabel?label=License)](https://github.com/liesliy/tlabel/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel?color=blue&label=Downloads)](https://pepy.tech/projects/tlabel)
[![GitHub Stars](https://img.shields.io/github/stars/liesliy/tlabel?style=social)](https://github.com/liesliy/tlabel/stargazers)
[![中文文档](https://img.shields.io/badge/文档-中文-blue)](README_CN.md)

**GelSight · DIGIT · PaXini · Daimon — one tool, one format, all sensors**

[🚀 Quick Start](#-quick-start) · [📡 Sensors](#-supported-sensors) · [🤝 Contributing](#-contributing)

</div>

---

> *Tactile data shouldn't be locked inside any single company's format. Just as RGB images don't belong to any camera manufacturer, tactile data deserves a unified "Unicode". That's what TLabel does — defining a universal language for tactile data, and giving it to everyone.*

---

## 🚀 Quick Start

```bash
pip install tlabel
```

```python
import tlabel

# Load data from any sensor — auto-detected
data = tlabel.load("path/to/your/data")

# Or try built-in demo (30 seconds)
data = tlabel.demo("gelsight")

# Review in Jupyter — interactive annotation panel
data.review()

# Export to unified format
data.export("output.json")      # JSON (tlabel_v2 schema)
data.export("output.csv")       # CSV
data.export_ftp1("out.zarr")    # FTP-1 Zarr (foundation model ready)
```

### CLI Tools

```bash
tlabel version               # Check version
tlabel list                  # List all registered adapters
tlabel info gelsight         # Adapter details & capabilities
tlabel validate your_data.json  # Validate tlabel_v2 schema compliance
```

---

## 🎯 What Does TLabel Do?

**Problem:** Every tactile sensor outputs different data formats. Switch sensors → rewrite code.

**Solution:** TLabel defines a unified 22-dimension feature space ([tlabel_v2](docs/annotation-spec.md)) and provides adapters that translate each sensor's native format into it.

```
GelSight .pkl ──┐                    ┌── JSON (tlabel_v2)
PaXini .h5 ─────┤   TLabel Adapter   ├── CSV
Daimon .parquet─┤   ──────────────►  ├── FTP-1 Zarr
VTouch .h5 ─────┤                    ├── LeRobot
Any format ─────┘                    └── ROS2 (stub)
```

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 🔌 **9 Built-in Adapters** | GelSight, DIGIT, PaXini, Daimon, ToucHD, UniVTAC, VTouch, YCB-Slide, TacQuad |
| 🏗️ **Open Platform** | `DataAdapterBase` + `SensorAdapterBase` — anyone can add sensor support in 30 min |
| 🛠️ **CLI Validation** | `tlabel validate` checks your data against the 22-dim schema |
| 🤖 **AI Pre-Annotation** | `PredictEngine` auto-labels contact, slip, and manipulation phases |
| 📈 **Data Augmentation** | 5 methods (time_warp, noise, crop, scale, dropout), pure numpy, zero extra deps |
| 📤 **Multi-Format Export** | JSON, CSV, FTP-1 Zarr, LeRobot, RLDS, ROS2 |
| 🌐 **Bilingual Panel** | Interactive Jupyter annotation panel (中/EN) |

### API at a Glance

```python
# Loading
data = tlabel.load(path)                     # Auto-detect format
data = tlabel.load(path, format="paxini")    # Force adapter

# Patching & Annotation
frame = data[0]
frame.patch("contact", 0)                    # Cascade rules auto-apply
data.batch_patch(10, 50, "slip_event", 1)   # Range patch

# AI Pre-Annotation
from tlabel.predict import PredictEngine
engine = PredictEngine()
engine.fit(data)                             # Learn from partial labels
results = engine.predict(data)
engine.apply(data, results, min_confidence=0.7)

# Augmentation
augmented = tlabel.augment(data, methods=["time_warp", "noise_inject"], seed=42)
```

📖 **Full API Reference** → [docs/API.md](docs/API.md) · **22-Dim Schema** → [docs/annotation-spec.md](docs/annotation-spec.md)

---

## 📡 Supported Sensors

| Sensor | Type | Format | Dims | Status |
|:-------|:-----|:-------|:----:|:------:|
| **GelSight Mini / DIGIT** | Vision-based | `.pkl` | 22 | ✅ Stable |
| **Daimon DM-TacClaw** | Multimodal | `.parquet` / dir | 22 | ✅ Stable |
| **Daimon DM-Tac** | Vision-based | `.avi` / USB | 22 | 🆕 Skeleton |
| **PaXini PXCap** | Force array | `.h5` | 20 | ✅ Stable |
| **PaXini GEN3** | Force array | SDK / `.paxini` | 18 | 🆕 New |
| **UniVTAC** | Vision-based | `.hdf5` | 22 | ✅ Stable |
| **TacQuad (AnyTouch)** | Multi-sensor | directory | 22 | ✅ Stable |
| **VTouch** | Vision-based | `.h5` | 22 | ✅ Stable |
| **YCB-Slide** | Vision-based | `.npy` / dir | 22 | ✅ Stable |

> Vision sensors → full 22 dims. Force-only sensors (PaXini) → 20 dims. **No errors, no surprises — just graceful degradation.**

```bash
# Per-sensor dependencies
pip install tlabel[gelsight]   # opencv-python
pip install tlabel[paxini]     # h5py
pip install tlabel[daimon]     # pyarrow + opencv-python
pip install tlabel[all]        # Everything
```

---

## 🆕 What's New

### v0.16.0 — Open Platform Architecture

TLabel is now an **open, extensible platform**:
- 🏗️ Dual-base architecture (`DataAdapterBase` / `SensorAdapterBase`)
- 🔌 External adapter registration via `entry_points` — third-party packages auto-discovered
- 🛠️ CLI tools: `tlabel validate / list / info / version`
- 📦 Community contribution kit: templates + PR templates + [CONTRIBUTING.md](CONTRIBUTING.md)

📖 **Full changelog** → [CHANGELOG_current.md](CHANGELOG_current.md)

---

## 🤝 Contributing

**TLabel is an open platform — anyone can extend it with new sensor support.**

| Way | Effort | Impact |
|-----|--------|--------|
| **Submit a PR** — use `contrib/adapter-template/`, inherit from `DataAdapterBase` or `SensorAdapterBase` | ~30 min | Your sensor works with the whole ecosystem |
| **Ship an independent package** — use `tlabel` entry_points for auto-discovery | ~1 hour | No PR needed, fully independent |
| **Other** — bug fixes, docs, tests, UI improvements | varies | Always welcome |

| Current Ecosystem | Count |
|-------------------|-------|
| Built-in adapters | 9 |
| Community adapters | 0 *(your name here?)* |

📖 **Get started** → [CONTRIBUTING.md](CONTRIBUTING.md) · **Adapter Template** → [contrib/adapter-template/](contrib/adapter-template/)

---

## 🏆 Benchmark

**[TLabel-Bench](https://github.com/liesliy/tlabel-bench)** — The first cross-sensor unified tactile annotation benchmark. Same objects, different sensors, one format.

---

## 📝 Citing TLabel

```bibtex
@software{tlabel2026,
  title = {TLabel: A Sensor-Agnostic Tactile Data Annotation Toolkit},
  author = {NiuZhu Tech},
  year = {2026},
  url = {https://github.com/liesliy/tlabel}
}
```

---

## 📄 License

[MIT](LICENSE) © NiuZhu Tech

---

<div align="center">

**If TLabel saved you from manually labeling tactile data, a ⭐ would make our day!**

[⭐ Star on GitHub](https://github.com/liesliy/tlabel/stargazers) · [📦 PyPI](https://pypi.org/project/tlabel/) · [🏆 Benchmark](https://github.com/liesliy/tlabel-bench) · [💬 Discord](https://discord.gg/2ab8EWaBM)

</div>

---

## 🤝 Need Help with Tactile Data?

We provide professional tactile data annotation and pipeline services:
- **Custom sensor adapter development** — integrate your sensor with TLabel in days
- **Data pipeline consulting** — annotation workflows for grasping, manipulation, slip detection
- **Embodied AI tooling** — end-to-end data solutions from raw sensor to model-ready datasets

**Contact:** WeChat `wxid_olqx5z6trmtn21` · Email `luoxi@touchlabelai.cn`
