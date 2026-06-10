# TouchLabel AI 🦞

<h3 align="center">Sensor-Agnostic Tactile Data Annotation Toolkit</h3>
<p align="center"><strong>load → review → export · Three steps to close the loop</strong></p>

<p align="center">
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/v/tlabel?color=e85d75" alt="PyPI"></a>
  <a href="https://pypi.org/project/tlabel/"><img src="https://img.shields.io/pypi/pyversions/tlabel" alt="Python"></a>
  <a href="https://github.com/liesliy/tlabel/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/tlabel" alt="License"></a>
  <a href="https://github.com/liesliy/tlabel/stargazers"><img src="https://img.shields.io/github/stars/liesliy/tlabel?style=social" alt="GitHub Stars"></a>
  <a href="https://pepy.tech/projects/tlabel"><img src="https://img.shields.io/pepy/dt/tlabel?color=blue" alt="Downloads"></a>
  <a href="README_CN.md">中文文档</a>
</p>

---

> 🎯 **Got tactile data from different sensors that refuse to talk to each other?**
> TLabel makes them speak the same language — load any format, annotate in a visual panel, export a unified schema.

---

## ⚡ 30-Second Demo

No data? No problem. Fire this up in Jupyter:

```python
import tlabel
data = tlabel.demo()    # ← built-in GelSight demo
data.review()           # ← interactive panel pops up
```

Or try other sensors:

```python
tlabel.demo('digit').review()    # DIGIT sensor
tlabel.demo('paxini').review()   # PaXini force sensor
tlabel.demo('daimon').review()   # Daimon DM-TacClaw
```

**What you'll see:** a color-coded timeline (🟢 contact / 🔴 slip / ⬜ idle), 22-dim radar chart, frame detail editor, and batch patching — all in one panel.

![TouchLabel AI Panel Demo](docs/demo_panel.gif)

---

## 🚀 Quick Start

```bash
pip install tlabel
```

```python
import tlabel

# Load — auto-detect sensor format, no config needed
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # PaXini
data = tlabel.load("daimon_data/")           # Daimon (directory or .parquet)

# Annotate — interactive Jupyter panel
data.review()          # Chinese UI
data.review(lang="en") # English UI

# Export — unified TLabel Format
data.export("output.json")   # TLabel Format v2 JSON
data.export("output.csv")    # flat CSV
```

That's it. Three lines, full loop. 🔁

---

## 🤔 Why TLabel?

| Pain | TLabel's Answer |
|------|-----------------|
| Every sensor spits out a different format | **One `load()` call, auto-detected** |
| Raw tactile data is unreadable numbers | **Visual panel: timeline + radar + details** |
| Fixing labels frame-by-frame is soul-crushing | **Batch patch + cascade rules, fix ranges in one click** |
| Your lab mate exported... something... | **Unified TLabel Format v2, 22 dimensions, no ambiguity** |
| "But we use DIGIT and they use PaXini" | **Sensor-agnostic. Load both, same schema, same tool.** |

---

## 📡 Supported Sensors

| Sensor | Format | Dimensions | Optical Flow | Status |
|--------|--------|:----------:|:------------:|:------:|
| **GelSight Mini** | `.pkl` | 22 | ✅ | ✅ Stable |
| **DIGIT** | `.pkl` | 22 | ✅ | ✅ Stable |
| **Daimon DM-TacClaw** | `.parquet` / dir | 22 (video) / 20 (no video) | ✅ / — | ✅ Stable |
| **PaXini PXCap** | `.h5` / `.hdf5` | 20 | — | ✅ Stable |

> Force-type sensors (PaXini) lack optical images → 20 dims. Image-type → full 22. Daimon gracefully degrades when no video is present. No errors, no surprises.

---

## 📦 Installation

```bash
# Just the core (numpy only, ~2s install)
pip install tlabel

# Per-sensor extras
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[daimon]     # Daimon → pyarrow + opencv-python

# I want it all
pip install tlabel[all]
```

---

## 🎨 Panel Features

- 🎨 **Color-coded timeline**: green = contact · red = slip · gray = idle — patterns jump out instantly
- 🕸 **22-dim radar chart**: see the full feature vector at a glance, bilingual labels
- ✏️ **Frame & batch patching**: fix one frame or a range, your call
- 🔗 **Cascade rules**: set `contact=0` → 7 related fields auto-zero + phase resets to `idle`
- 🌐 **Bilingual toggle**: 中文 / English, one click top-right
- 📤 **Export**: JSON / CSV, auto-detected by file extension

---

## TLabel Format v2 — 22 Dimensions

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

### Temporal Features (4-dim, v0.2.0)

| # | Key | Image-type | Force-type | Description |
|---|-----|:----------:|:----------:|-------------|
| 19 | `optical_flow_magnitude` | ✅ | — | Inter-frame motion magnitude (Farneback) |
| 20 | `optical_flow_direction` | ✅ | — | Optical flow angle (°) |
| 21 | `temporal_deformation_rate` | ✅ | ✅ | Rate of deformation change |
| 22 | `contact_transition` | ✅ | ✅ | Contact state transition probability |

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
├── demo.py               # Built-in demo data loader
└── export/
    └── writer.py         # JSON / CSV export + NumpyEncoder
```

---

## 💬 Feedback

Found a bug? Have an idea? Just want to say hi?

- 🐛 **Bug report** → [Open an Issue](https://github.com/liesliy/tlabel/issues)
- 💡 **Feature request** → [GitHub Discussions](https://github.com/liesliy/tlabel/discussions)
- 🌟 **Using tlabel in your research?** → We'd love to hear about it! Drop us a star ⭐

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Good first issues:**
- 🔌 Add a new sensor adapter (SynTouch? XELA? Your call.)
- 📊 Improve radar chart UI (dark mode, interactive hover)
- 🌐 Add more language support (日本語, 한국어)
- 🧪 Add integration tests for edge cases

---

## 📄 License

[MIT](LICENSE) © Niuzu Tech

---

<p align="center">
  <strong>If this saved you from manually labeling tactile data, a ⭐ would make our day!</strong>
</p>
