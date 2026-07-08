<div align="center">

# 🦞 TouchLabel AI

### **The World's First Sensor-Agnostic Tactile Data Annotation Toolkit**

**Load any tactile sensor → Annotate visually → Export a unified schema**

[![PyPI](https://img.shields.io/pypi/v/tlabel?color=e85d75&label=PyPI)](https://pypi.org/project/tlabel/)
[![Python](https://img.shields.io/pypi/pyversions/tlabel?label=Python)](https://pypi.org/project/tlabel/)
[![License](https://img.shields.io/pypi/l/tlabel?label=License)](https://github.com/liesliy/tlabel/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel?color=blue&label=Downloads)](https://pepy.tech/projects/tlabel)
[![GitHub Stars](https://img.shields.io/github/stars/liesliy/tlabel?style=social)](https://github.com/liesliy/tlabel/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/liesliy/tlabel?label=Last%20Commit)](https://github.com/liesliy/tlabel/commits/main)
[![中文文档](https://img.shields.io/badge/文档-中文-blue)](README_CN.md)

![TLabel Panel Demo](docs/demo_panel_v050.png)

**GelSight · DIGIT · PaXini · Daimon — one tool, one format, all sensors**

[🚀 Quick Start](#-quick-start) · [🤖 AI Pre-Annotation](#-ai-pre-annotation) · [📊 Benchmark](#-benchmark) · [📖 Docs](#-supported-sensors) · [🤝 Contributing](#-contributing)

</div>

---

## 🆕 What's New

### v0.14.0 — Taxonomy System & Force-Inferred Primitive Prediction 🆕
**From visual-tactile images to force estimation to primitive annotation — fully automated pipeline.**
- 🧬 **Taxonomy System**: Configurable primitive taxonomy with 7 default physics-grounded primitives (reach, grasp, press, squeeze, wrap, wipe, lift) selected from T-Rex 22, with Cutkosky grasp subtypes (power/precision/lateral)
- 💪 **Force Estimation → Primitive Pipeline**: Auto-detect primitives from visual-tactile images (GelSight/DIGIT) even without force sensors — `force_estimator` infers force distributions, then rule engine maps to primitives
- 🎯 **Confidence & Source Tracking**: Every AI prediction carries `source` (ai_predicted / ai_predicted_estimated) + `confidence` score — transparent provenance
- 🔧 **Custom Primitive Registration**: `register_custom_primitive()` API for user-defined primitives with physical rules
- 📊 **Enhanced CSV Export**: New `primitive_source` and `primitive_confidence` columns for full metadata traceability
- 🎨 **Collapsible Prediction Panel**: In-panel taxonomy selector + prediction button + result statistics
- 📦 **Batch Patch Support**: Bulk primitive correction with primitive type + confidence controls

```python
import tlabel

# Load data and auto-predict primitives (uses default taxonomy)
data = tlabel.demo('gelsight')
data.predict_primitives()  # Auto-detect from force/contact patterns

# Use custom taxonomy with minimum confidence threshold
taxonomy = tlabel.get_default_taxonomy()
taxonomy.register(tlabel.PrimitiveRule(
    name='poke', min_force=0.1, max_deformation=0.15,
    contact_required=True, min_confidence=0.5
))
data.predict_primitives(taxonomy=taxonomy, min_confidence=0.4)

# Register custom primitives globally
tlabel.register_custom_primitive('poke',
    force_range=(0.1, 0.8), deformation_max=0.15,
    contact_required=True, confidence=0.5)

# Export with full metadata (source + confidence)
data.export("output.csv")  # includes primitive_source, primitive_confidence columns
```

### v0.13.0 — Motor Primitive Annotation System
**The world's first tactile primitive annotation toolkit — inspired by T-Rex (Li Fei-Fei, Jim Fan, Xu Danfei et al.).**
- 🏷️ **22 Motor Primitives**: wrap, lift, grasp, fold, cut, insert, press, wipe, peel, assemble, extract, twist, shake, dispense, disassemble, squeeze, pour, open, close, screw, unscrew, reach
- 📊 **Primitive Timeline Track**: Canvas-rendered color-coded primitive segments in the Panel, with frame-level detail badges
- 🤖 **AI Pre-Annotation**: `predict_primitives()` — heuristic inference from force/contact patterns (force rise→grasp/press, stable+motion→wrap/wipe, drop→squeeze, no contact→reach)
- 📈 **Structured Annotations**: `add_primitive(name, start_frame, end_frame)` API for time-interval primitive labeling
- 💾 **Export Support**: CSV export with `primitive_label` column; JSON export with `primitive_annotations` array
- 🔄 **Backward Compatible**: Old tlabel.json files load normally (no primitive_annotations → empty list)

```python
import tlabel

# Load demo with primitive annotations
data = tlabel.demo('primitives_demo')
data.review()  # See primitive timeline track in Panel

# Add primitive annotations programmatically
data.add_primitive('reach', start_frame=0, end_frame=10)
data.add_primitive('grasp', start_frame=10, end_frame=25)
data.add_primitive('lift', start_frame=25, end_frame=40)

# AI pre-annotation (heuristic-based)
data.apply_primitives()  # Auto-detect primitives from force/contact patterns

# Get primitive timeline
timeline = data.get_primitive_timeline()
# [('reach', 0, 10), ('grasp', 10, 25), ('lift', 25, 40)]
```

### v0.12.0 — Tactile Image Visualization & Data Augmentation
**Canvas-based tactile image playback, pure-numpy augmentation, and AnyTouch multi-sensor support.**
- 🎬 **Tactile Image Sequence Visualization**: Canvas-rendered playback with 3-level strategy (real image / heatmap / placeholder), play/pause/seek/speed controls, dark mode & i18n
- 📈 **Data Augmentation Module**: 5 methods (`time_warp`, `noise_inject`, `random_crop`, `force_scale`, `frame_dropout`), zero new deps (pure numpy), 3-level API
- 🔌 **TacQuad Adapter**: GeWu-Lab AnyTouch (ICLR 2025) — GelSight Mini, DIGIT, DuraGel + optional Tac3D force field
- 📦 `pip install tlabel[tacquad]`

```python
import tlabel

# Data augmentation — one-liner
data = tlabel.demo('gelsight')
augmented = tlabel.augment(data, methods=["time_warp", "noise_inject"], seed=42)

# TacQuad multi-sensor loading
data = tlabel.load("anytouch_dataset/", format="tacquad", sensor="digit")
```

### v0.10.2 — UniVTAC Adapter
**Cross-dataset tactile interoperability — UniVTAC benchmark support.**
- 🆕 **UniVTAC Adapter**: Load UniVTAC HDF5 datasets with auto-detection (dual GelSight Mini, 22 dims)
- 🔍 **Smart HDF5 Detection**: Auto-distinguishes PaXini vs UniVTAC by internal structure
- 📦 `pip install tlabel[univtac]`

### v0.8.0 — FTP-1 / MTTS Export
**Export labeled data directly to FTP-1's MTTS Zarr format for foundation model fine-tuning.**
- 🚀 **FTP-1 Converter**: `tlabel_to_ftp1()` / `batch_to_ftp1()` — one-click export to Zarr
- 🖐 **21 Functional Areas**: MTTS morphology-aware tactile token space (15 hand zones + 6 wrist torque channels)
- 📡 **7 Sensor Registry**: GelSight, GelSightMini, FreeTacMan, ViTaMIn, 3DViTac, Contactile, BinaryContact
- 🎨 **New Export Tab in Panel**: sensor selection, functional area picker with presets, export preview
- 📦 **Zarr backend**: append mode for multi-episode datasets, auto image resize to 224×224 + normalization

```python
from tlabel import demo
data = demo('gelsight')
data.export_ftp1("output.zarr",
    sensor_name="GelSightMini",
    functional_areas=[0, 1])  # thumb tip + index fingertip
```

### v0.5.0 — AI-Assisted Pre-Annotation
**Let the engine suggest labels, then you review and correct — human-in-the-loop, not black-box.**
- 🤖 **PredictEngine**: predict contact, slip, and manipulation phase automatically
- 📈 **Warm start with `fit()`**: learn from your partially labeled data — even 10% labels significantly boost accuracy
- 🎯 **Confidence threshold**: only apply predictions above your threshold, you stay in control
- 🔬 **HMM Phase Detection**: Hidden Markov Model for manipulation phase inference with Viterbi decoding
- 🧹 **Removed black-box pkl models**: no opaque pretrained weights — every prediction is interpretable

<details>
<summary><b>Previous releases</b></summary>

- **v0.13.1** — GBK encoding hotfix, primitive system stabilization
- **v0.12.4** — Fix gelsight_images demo JSON format
- **v0.12.3** — Dynamic version display in Panel
- **v0.12.0** — Tactile image visualization, data augmentation, TacQuad adapter
- **v0.11.2** — Fix Jupyter panel initialization timing
- **v0.10.3** — VTouch/YCB-Slide adapter registration, LeRobot export panel, PyPI fixes
- **v0.9.0** — Panel Phase 1 (5 UI features), Exporter Plugin Registry (7 formats)
- **v0.4.2** — Full i18n: bilingual Panel UI (中文/English), localized error messages, docs in both languages
- **v0.4.1** — Panel UI integration: Tab navigation, batch correction tool, export buttons directly in panel
- **v0.4.0** — Interactive Panel: color-coded timeline, 22-dim radar chart, frame detail editor
- **v0.2.0b1** — LeRobot integration, HDF5 export, enhanced metadata, comprehensive tutorials

</details>

---

## 🎯 Why TLabel?

> **Every tactile sensor spits out a different format. There's no universal annotation tool — until now.**

| The Problem | TLabel's Answer |
|:------------|:----------------|
| 4 different sensors → 4 different pipelines | **One `tlabel.load()` call, auto-detected** |
| Raw tactile data = unreadable numbers | **Visual Panel: timeline + radar chart + frame editor** |
| Fixing labels frame-by-frame is soul-crushing | **AI pre-annotation + batch patch + cascade rules** |
| "We use DIGIT, they use PaXini" — data doesn't mix | **Sensor-agnostic 22-dim schema, one format for all** |
| No standardized tactile labels exist | **TLabel Format v2 — the first unified specification** |
| Annotation tools assume vision, not touch | **Built for tactile from day one** |

**TLabel is the only tool that:**
- ✅ Supports 4+ tactile sensor families out of the box
- ✅ Provides a unified 22-dimension annotation schema
- ✅ Offers AI-assisted pre-annotation with human-in-the-loop
- ✅ Ships an interactive visual Panel for Jupyter
- ✅ Includes a cross-sensor benchmark ([TLabel-Bench](https://github.com/liesliy/tlabel-bench))

---

## 🚀 Quick Start

### Install

```bash
pip install tlabel
```

That's it. Core installs in seconds with just numpy as a dependency.

### Try the Demo (30 seconds)

```python
import tlabel

data = tlabel.demo()     # Built-in GelSight demo — no files needed
data.review()            # Interactive Panel pops up in Jupyter
```

**What you'll see:** a color-coded timeline (🟢 contact / 🔴 slip / ⬜ idle), 22-dim radar chart, frame detail editor, and batch patching — all in one panel.

Other sensors:
```python
tlabel.demo('digit').review()    # DIGIT sensor
tlabel.demo('paxini').review()   # PaXini force sensor
tlabel.demo('daimon').review()   # Daimon DM-TacClaw
```

👉 **[Try it live in your browser](https://liesliy.github.io/tlabel/demo.html)** — no install needed.

### Load Your Own Data

```python
import tlabel

# Auto-detect sensor format — no config needed
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # PaXini
data = tlabel.load("daimon_data/")           # Daimon (directory or .parquet)
data = tlabel.load("univtac_episode.hdf5")   # UniVTAC (dual GelSight Mini)
data = tlabel.load("anytouch_dataset/")      # TacQuad / AnyTouch (ICLR 2025)
```

### Annotate & Export

```python
# Interactive Jupyter panel (bilingual: 中文 / English)
data.review()           # Chinese UI
data.review(lang="en")  # English UI

# Export — unified TLabel Format v2
data.export("output.json")   # Full schema JSON
data.export("output.csv")    # Flat CSV for pandas/Excel
```

Full loop: **load → review → correct → export** 🔁

### Data Augmentation

```python
import tlabel

data = tlabel.demo('gelsight')

# Quick augment — default: time_warp + noise_inject
augmented = tlabel.augment(data)

# Fine-grained control
from tlabel.augment import AugmentEngine
engine = AugmentEngine(seed=42)
augmented = engine.augment(data, methods=["time_warp", "noise_inject", "random_crop"])

# Or via TLabelData method
augmented = data.augment(methods=["force_scale", "frame_dropout"], seed=42)
```

5 built-in methods: `time_warp`, `noise_inject`, `random_crop`, `force_scale`, `frame_dropout` — all pure numpy, zero new dependencies.

### Export to FTP-1 (Foundation Model Ready)

```bash
pip install tlabel[ftp1]   # installs zarr
```

```python
# Export labeled data → FTP-1 Zarr format
data.export_ftp1("output.zarr",
    sensor_name="GelSightMini",
    functional_areas=[0, 1])

# Batch export multiple episodes
from tlabel.converters import batch_to_ftp1
batch_to_ftp1(["ep1.json", "ep2.json"], "dataset.zarr",
    sensor_name="GelSightMini",
    functional_areas=[0, 1])

# Preset configurations
from tlabel.converters import DEFAULT_AREA_MAPPINGS
# "parallel_gripper": [0, 1]
# "three_finger": [0, 1, 2]
# "five_finger": [0, 1, 2, 3, 4]
# "dexterous_hand": list(range(15))
```

The exported Zarr files are directly compatible with [FTP-1](https://github.com/michaelyuancb/ftp1-policy) for fine-tuning the world's first general-purpose tactile foundation model.

---

## 🤖 AI Pre-Annotation

**New in v0.5.0** — Let the engine suggest labels, then you review and correct.

```python
from tlabel.predict import PredictEngine

engine = PredictEngine()

# Option 1: Cold start — no prior labels needed
results = engine.predict(data)

# Option 2: Warm start — learn from your partial annotations first
engine.fit(data)          # Extract statistics from labeled frames
results = engine.predict(data)

# Apply only high-confidence predictions (≥ 0.7)
applied = engine.apply(data, results, min_confidence=0.7)
print(f"Auto-filled {applied} fields")

# Review in Panel — correct any mistakes
data.review()
```

**What it predicts:**

| Dimension | Method | Confidence Range |
|:----------|:-------|:----------------:|
| `contact` | Rule-based (force + deformation + area) | 0.4 – 0.9 |
| `slip_event` | Rule-based (shear + delta + entropy) | 0.55 – 0.8 |
| `manipulation_phase` | HMM + Viterbi decoding | 0.55 – 0.65 |
| Missing dims (with `fit()`) | Statistical (mean from labeled frames) | ~0.4 |

> 💡 **Tip:** Use `fit()` on partially labeled data first — even 10–20% labeled frames significantly improve predictions. Predictions below your confidence threshold are simply skipped.

---

## 📡 Supported Sensors

| Sensor | Type | Format | Dims | Optical Flow | Status |
|:-------|:-----|:-------|:----:|:------------:|:------:|
| **GelSight Mini** | Vision-based | `.pkl` | 22 | ✅ | ✅ Stable |
| **DIGIT** | Vision-based | `.pkl` | 22 | ✅ | ✅ Stable |
| **Daimon DM-TacClaw** | Multimodal | `.parquet` / dir | 22 (video) / 20 (no video) | ✅ / — | ✅ Stable |
| **PaXini PXCap** | Force array | `.h5` / `.hdf5` | 20 | — | ✅ Stable |
| **UniVTAC** | Vision-based (Dual GelSight Mini) | `.hdf5` / `.h5` | 22 | ✅ | ✅ New |
| **TacQuad (AnyTouch)** | Vision-based multi-sensor | directory | 22 | ✅ | ✅ New |
| **VTouch** | Vision-based | `.pkl` | 22 | ✅ | ✅ New |

> Force-type sensors (PaXini) lack optical images → 20 dims. Image-type → full 22. Daimon gracefully degrades when no video is present. **No errors, no surprises.**

### FTP-1 Compatible Sensors

All sensors below can export directly to [FTP-1](https://github.com/michaelyuancb/ftp1-policy) MTTS Zarr format via `export_ftp1()`:

| Sensor | Type | Default Shape |
|:-------|:-----|:-------------:|
| GelSight / GelSightMini | image | (224, 224, 3) |
| FreeTacMan | image | (224, 224, 3) |
| ViTaMIn | image | (224, 224, 3) |
| 3DViTac | matrix | (12, 32) |
| Contactile | matrix | (12, 32) |
| BinaryContact | binary | (1,) |

### Per-Sensor Installation

```bash
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[daimon]     # Daimon → pyarrow + opencv-python
pip install tlabel[univtac]    # UniVTAC → h5py
pip install tlabel[tacquad]    # TacQuad / AnyTouch → (pure numpy)
pip install tlabel[vtouch]     # VTouch → opencv-python
pip install tlabel[ftp1]       # FTP-1/MTTS export → zarr
pip install tlabel[all]        # Everything
```

### Sensor Tutorials

- 📖 [GelSight / DIGIT Tutorial](docs/tutorial-gelsight.md)
- 📖 [PaXini PXCap Tutorial](docs/tutorial-paxini.md)
- 📖 [Daimon DM-TacClaw Tutorial](docs/tutorial-daimon.md)

---

## 🎨 Panel Features

- 🎬 **Tactile image sequence visualization**: Canvas-based playback with 3-level strategy (real image / heatmap / placeholder), play/pause/seek/speed controls, dark mode
- 🎨 **Color-coded timeline**: green = contact · red = slip · gray = idle — patterns jump out instantly
- 🕸 **22-dim radar chart**: see the full feature vector at a glance, bilingual labels
- ✏️ **Frame & batch patching**: fix one frame or a range, your call
- 🔗 **Cascade rules**: set `contact=0` → 7 related fields auto-zero + phase resets to `idle`
- 🤖 **Pre-annotation integration**: apply AI predictions, then review in the same panel
- 🌐 **Bilingual toggle**: 中文 / English, one click top-right
- 📤 **In-panel export**: JSON / CSV / FTP-1 Zarr with one click

---

## 📐 TLabel Format v2 — 22 Dimensions

The first unified tactile annotation schema. Every frame, every sensor, same 22 dimensions.

### Static Features (18-dim)

| # | Key | Description |
|---|-----|-------------|
| 1 | `contact` | Binary contact flag |
| 2 | `deformation_magnitude` | Surface deformation intensity |
| 3 | `force_magnitude` | Normal force magnitude |
| 4 | `force_peak` | Peak force in episode window |
| 5 | `force_direction` | Force vector angle (°) |
| 6 | `slip_entropy` | Uncertainty of slip detection |
| 7 | `slip_event` | Binary slip event flag |
| 8 | `texture_energy` | Surface texture frequency energy |
| 9 | `edge_density` | Contact edge pixel ratio |
| 10 | `contact_area` | Contact region area ratio |
| 11 | `centroid_x` | Contact centroid x-position |
| 12 | `normal_field_magnitude` | Normal pressure field magnitude |
| 13 | `normal_field_variance` | Normal field spatial variance |
| 14 | `shear_field_magnitude` | Shear stress magnitude |
| 15 | `shear_field_direction` | Shear direction angle (°) |
| 16 | `delta_force_normal` | Frame-to-frame ΔF_normal |
| 17 | `delta_force_shear` | Frame-to-frame ΔF_shear |
| 18 | `friction_cone_ratio` | Tangential/normal force ratio |

### Temporal Features (4-dim)

| # | Key | Image-type | Force-type | Description |
|---|-----|:----------:|:----------:|-------------|
| 19 | `optical_flow_magnitude` | ✅ | — | Inter-frame motion magnitude (Farneback) |
| 20 | `optical_flow_direction` | ✅ | — | Optical flow angle (°) |
| 21 | `temporal_deformation_rate` | ✅ | ✅ | Rate of deformation change |
| 22 | `contact_transition` | ✅ | ✅ | Contact state transition probability |

📖 **Full specification:** [annotation-spec.md](docs/annotation-spec.md) | [tlabel-format.md](docs/tlabel-format.md)

---

## 📖 API Quick Reference

```python
import tlabel

# ── Loading ──
data = tlabel.load(path)                     # Auto-detect sensor format
data = tlabel.load(path, format="gelsight")  # Force specific adapter

# ── Demo ──
data = tlabel.demo()                         # Built-in demo data
tlabel.list_demos()                          # See available sensors

# ── Properties ──
data.num_frames        # int — total frame count
data.duration_s        # float — episode duration
data.sensor_type       # str — sensor identifier
data.dimension_keys    # list — all dimension keys
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

# ── Augmentation ──
augmented = tlabel.augment(data)                   # Default augmentation
augmented = tlabel.augment(data, methods=["time_warp", "noise_inject"], seed=42)

# ── Pre-Annotation ──
from tlabel.predict import PredictEngine
engine = PredictEngine()
engine.fit(data)                                   # Warm start from partial labels
results = engine.predict(data)                     # Predict contact, slip, phase
engine.apply(data, results, min_confidence=0.7)    # Apply high-confidence only

# ── Review & Export ──
data.review()                    # Jupyter panel (Chinese)
data.review(lang="en")           # English
data.export("output.json")       # JSON (TLabel Format v2)
data.export("output.csv")        # CSV
data.export_ftp1("out.zarr")     # FTP-1 Zarr format
```

### Cascade Rules (contact → 0)

When `contact` is set to `0`, these fields are automatically zeroed:

| Auto-zeroed Field | Condition |
|:------------------|:----------|
| `force_magnitude` | always |
| `force_peak` | always |
| `slip_event` | always |
| `delta_force_normal` | always |
| `delta_force_shear` | always |
| `contact_area` | always |
| `contact_transition` | only if value > 0.5 |
| `manipulation_phase` → `"idle"` | if not already |

---

## 🏆 Benchmark

**[TLabel-Bench](https://github.com/liesliy/tlabel-bench)** — The first cross-sensor unified tactile annotation benchmark.

Same objects, different sensors, one format. TLabel-Bench provides cross-sensor annotations (material labels, episode segmentation, quality scores) for objects annotated with GelSight Mini, DIGIT, DMA, and more — all in the unified TLabel format.

```bash
git clone https://github.com/liesliy/tlabel-bench.git
cd tlabel-bench
bash scripts/download_data.sh
python evaluation/material_classification.py
```

If you're using TLabel in research, citing the benchmark helps demonstrate sensor-agnostic value 👇

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
│   ├── daimon.py         # Daimon DM-TacClaw (+ video decoding)
│   └── tacquad.py        # TacQuad / AnyTouch (ICLR 2025)
├── augment/
│   └── engine.py         # Data augmentation (time_warp, noise, crop, scale, dropout)
├── converters/
│   ├── lerobot.py        # LeRobot format converter
│   └── ftp1.py           # FTP-1/MTTS Zarr format converter
├── viewer/
│   ├── panel.py          # Jupyter _repr_html_ renderer
│   └── templates.py      # HTML + JS + CSS template engine
├── predict/
│   └── engine.py         # AI-assisted pre-annotation engine
├── demo.py               # Built-in demo data loader
└── export/
    └── writer.py         # JSON / CSV export + NumpyEncoder
```

---

## 📝 Citing TLabel

If you use TLabel in your research, please cite:

```bibtex
@software{tlabel2026,
  title = {TLabel: A Sensor-Agnostic Tactile Data Annotation Toolkit},
  author = {NiuZhu Tech},
  year = {2026},
  url = {https://github.com/liesliy/tlabel}
}
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Good first issues:**
- 🔌 Add a new sensor adapter (SynTouch? XELA? Your call.)
- 📊 Improve radar chart UI (dark mode, interactive hover)
- 🌐 Add more language support (日本語, 한국어)
- 🧪 Add integration tests for edge cases
- 🤖 Improve pre-annotation models (replace rules with lightweight ML?)

---

## 💬 Feedback

- 🐛 **Bug report** → [Open an Issue](https://github.com/liesliy/tlabel/issues)
- 💡 **Feature request** → [GitHub Discussions](https://github.com/liesliy/tlabel/discussions)
- 🌟 **Using TLabel in your research?** → We'd love to hear about it! Drop us a star ⭐

---

## 📄 License

[MIT](LICENSE) © NiuZhu Tech

---

<div align="center">

**If this saved you from manually labeling tactile data, a ⭐ would make our day!**

[⭐ Star on GitHub](https://github.com/liesliy/tlabel/stargazers) · [📦 Install from PyPI](https://pypi.org/project/tlabel/) · [🏆 Try the Benchmark](https://github.com/liesliy/tlabel-bench)

</div>


---

## 🤝 Need Help with Tactile Data?

We provide professional tactile data annotation and pipeline services:

- **Custom sensor adapter development** — integrate your tactile sensor with TLabel in days, not weeks
- **Data pipeline consulting** — design annotation workflows for your specific task (grasping, manipulation, slip detection, etc.)
- **Embodied AI tooling** — end-to-end data solutions from raw sensor output to model-ready datasets

**Contact us:**
- WeChat: `wxid_olqx5z6trmtn21`
- Email: `375720783@qq.com`
- Company: [NiuSu Tech / TouchLabel AI](https://github.com/liesliy/tlabel)


---

## 🤝 需要触觉数据方面的帮助？

我们提供专业的触觉数据标注和数据处理服务：

- **传感器适配器开发** — 几天内让你的触觉传感器接入 TLabel，而不是几周
- **数据流程咨询** — 为你的具体任务（抓取、操作、滑移检测等）设计标注工作流
- **具身智能数据方案** — 从原始传感器输出到模型可用数据集的端到端解决方案

**联系我们：**
- 微信: `wxid_olqx5z6trmtn21`
- 邮箱: `375720783@qq.com`
- 公司: [牛宿科技 / TouchLabel AI](https://github.com/liesliy/tlabel)
