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

![TouchLabel AI Panel Demo](docs/demo_panel.gif)

---

<p align="center">
  <b>If TouchLabel helps your research, please consider giving us a ⭐ on GitHub — it means a lot!</b>
</p>

---

## 🚀 Quick Start

```bash
pip install tlabel
```

```python
import tlabel

# 1️⃣ Load — auto-detect sensor format
data = tlabel.load("gelsight_force.pkl")     # GelSight / DIGIT
data = tlabel.load("paxini_episode.h5")      # PaXini
data = tlabel.load("daimon_data/")           # Daimon (directory or .parquet)

# 2️⃣ Annotate — interactive Jupyter panel
data.review()          # Chinese UI
data.review(lang="en") # English UI

# 3️⃣ Export
data.export("output.json")   # TLabel Format v2 JSON
data.export("output.csv")    # CSV flat table
```

<details>
<summary>📥 Try with demo data</summary>

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
| **Daimon DM-TacClaw** | `.parquet` / dir | 22 (video) / 20 (no video) | ✅ / — | ✅ Stable |
| **PaXini PXCap** | `.h5` / `.hdf5` | 20 | — | ✅ Stable |

> Force-type sensors (PaXini) lack optical images and don't support optical flow features, yielding 20 dimensions. Image-type sensors output all 22 dimensions. Daimon gracefully degrades to 20 dims when no video file is present.

---

## 📦 Installation

```bash
# Minimal (numpy only)
pip install tlabel

# Per-sensor optional dependencies
pip install tlabel[gelsight]   # GelSight / DIGIT → opencv-python
pip install tlabel[paxini]     # PaXini → h5py
pip install tlabel[daimon]     # Daimon → pyarrow + opencv-python

# Everything
pip install tlabel[all]
```

---

## 🎨 Panel Features

- 🎨 **Color-coded timeline**: green = contact · red = slip · gray = no contact
- 🕸 **22-dim radar chart**: full TLabel Format v2 visualization with bilingual labels
- ✏️ **Frame & batch patching**: select a range, modify in one click
- 🔗 **Cascade rules**: setting `contact=0` auto-zeroes 7 related fields + resets `manipulation_phase→idle`
- 🌐 **Bilingual toggle**: Chinese / English, one click in the top-right corner
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

[MIT](LICENSE) © Niuzu Tech

---

<p align="center">
  <strong>Star us ⭐ if it helps your research!</strong>
</p>

