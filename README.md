<div align="center">

# 🦞 TLabel

**A Unified Tactile Data Annotation Standard & Toolkit**

Load any sensor · Annotate in one format · Export everywhere

[![PyPI](https://img.shields.io/pypi/v/tlabel?color=e85d75&label=PyPI)](https://pypi.org/project/tlabel/)
[![Python](https://img.shields.io/pypi/pyversions/tlabel)](https://pypi.org/project/tlabel/)
[![License](https://img.shields.io/pypi/l/tlabel)](LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel?color=blue)](https://pepy.tech/projects/tlabel)
[![arXiv](https://img.shields.io/badge/arXiv-2507.xxxxx-b31b1b)](https://arxiv.org/abs/xxxx.xxxxx)
[![中文文档](https://img.shields.io/badge/文档-中文-blue)](README_CN.md)

</div>

---

## What is TLabel?

Every tactile sensor speaks a different language. TLabel defines a **single annotation schema** (14 semantic dimensions, 4 compliance levels) and provides **adapters** that translate each sensor's native format into it.

```
 GelSight .pkl ──┐                        ┌── JSON / CSV
 PaXini .h5 ─────┤   TLabel Adapter       ├── FTP-1 Zarr
 Daimon .parquet─┤   ─────────────────►   ├── LeRobot / RLDS
 VTouch .h5 ─────┤                        └── ROS2
 Any format ─────┘
```

Think of it as **Unicode for tactile data** — one schema, all sensors.

---

## Quick Start

```bash
pip install tlabel
```

```python
import tlabel

# Load data from any sensor (auto-detected)
data = tlabel.load("path/to/data")

# Or try built-in demo
data = tlabel.demo("gelsight")

# Interactive annotation panel (Jupyter)
data.review()

# Export
data.export("output.json")
data.export_ftp1("out.zarr")
```

```bash
# CLI
tlabel list                    # All registered adapters
tlabel info gelsight           # Adapter details
tlabel validate data.json      # Schema compliance check
```

---

## Schema V2 — 14 Dimensions, 4 Compliance Levels

TLabel Schema V2 defines **14 semantic dimensions** organized by mandatory/optional tiers, with **Compliance Levels (L1–L4)** indicating annotation completeness:

| # | Dimension | Type | Required |
|---|-----------|------|----------|
| 1 | `contact` | bool | ✅ Required |
| 2 | `contact_centroid` | [float × 2] | ✅ (if contact) |
| 3 | `force_magnitude` | float | ✅ (L2+) |
| 4 | `slip_event` | bool | ✅ Required |
| 5 | `confidence` | float | ✅ Required |
| 6 | `compliance_level` | L1 / L2 / L3 / L4 | ✅ Required |
| 7 | `contact_region` | enum | Optional |
| 8 | `force_vector` | [float × 3] | Optional (L3+) |
| 9 | `torque_vector` | [float × 3] | Optional |
| 10 | `slip_velocity` | [float × 2] | Optional |
| 11 | `manipulation_phase` | enum | Optional |
| 12 | `texture_class` | enum | Optional |
| 13 | `object_deformation` | float | Optional |
| 14 | `temperature` | float | Optional |

**Compliance Levels:**
- **L1** — Contact + slip + confidence (minimal annotation)
- **L2** — L1 + force_magnitude (force-aware)
- **L3** — L2 + force_vector (full 3D contact wrench)
- **L4** — L3 + all optional fields (complete annotation)

📖 Full spec → [docs/annotation-spec.md](docs/annotation-spec.md) · Schema JSON → [schema/tlabel-schema.json](schema/tlabel-schema.json)

---

## Supported Sensors

### Dataset Adapters (offline data loading)

| Sensor | Type | Format | Compliance |
|:-------|:-----|:-------|:----------:|
| GelSight Mini / DIGIT | Vision-based | `.pkl` | L3 |
| Daimon DM-TacClaw | Multimodal | `.parquet` | L3 |
| PaXini PXCap | Force array | `.h5` | L2 |
| UniVTAC | Vision-based | `.hdf5` | L3 |
| TacQuad (AnyTouch) | Multi-sensor | directory | L3 |
| VTouch | Vision-based | `.h5` | L3 |
| YCB-Slide | Vision-based | `.npy` | L3 |

### Real-time Sensor Adapters (live hardware)

| Sensor | Type | Connection | Compliance |
|:-------|:-----|:-----------|:----------:|
| PaXini GEN3 | Force array | SDK | L2 |
| Daimon DM-Tac | Vision-based | USB / `.avi` | L3 |

```bash
# Per-sensor dependencies
pip install tlabel[gelsight]   # opencv-python
pip install tlabel[paxini]     # h5py
pip install tlabel[daimon]     # pyarrow + opencv-python
pip install tlabel[all]        # Everything
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Schema                                │
│  14-dim semantic standard + Compliance Levels   │
├─────────────────────────────────────────────────┤
│  Layer 2: Adapters                              │
│  DataAdapterBase │ SensorAdapterBase             │
│  (7 built-in + community extensible)            │
├─────────────────────────────────────────────────┤
│  Layer 3: Downstream                            │
│  Feature derivation · Augmentation · Export     │
│  PredictEngine · FTP-1 · LeRobot · RLDS · ROS2 │
└─────────────────────────────────────────────────┘
```

- **DataAdapterBase** — inherit this to add file-based sensor support (~30 min)
- **SensorAdapterBase** — inherit this to add live hardware support
- Both share the same export pipeline

---

## Export Formats

| Format | Use Case | Command |
|--------|----------|---------|
| JSON / CSV | General analysis | `data.export("out.json")` |
| FTP-1 Zarr | Foundation model training | `data.export_ftp1("out.zarr")` |
| LeRobot | LeRobot framework | `data.export_lerobot("out/")` |
| RLDS | RLDS/TFDS pipeline | `data.export_rlds("out/")` |
| ROS2 | Robot runtime | Stub (coming soon) |

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Pre-Annotation** | `PredictEngine` auto-labels contact, slip, manipulation phases |
| 📈 **Data Augmentation** | 5 methods (time_warp, noise, crop, scale, dropout) |
| 🌐 **Interactive Panel** | Bilingual Jupyter annotation panel (中/EN) |
| 🔌 **Open Platform** | Community adapters via `entry_points` auto-discovery |

---

## Contributing

TLabel is extensible by design. Add your sensor in ~30 minutes:

1. Fork from [contrib/adapter-template/](contrib/adapter-template/)
2. Inherit `DataAdapterBase` or `SensorAdapterBase`
3. Submit a PR or ship as an independent package

📖 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Citation

```bibtex
@software{tlabel2026,
  title  = {TLabel: A Sensor-Agnostic Tactile Data Annotation Toolkit and Format Standard},
  author = {Wu, Sheng and Luo, Xi},
  year   = {2026},
  url    = {https://github.com/liesliy/tlabel}
}
```

---

## License

[MIT](LICENSE) © 2026 NiuZhu Tech

---

<div align="center">

**If TLabel helps your tactile data workflow, consider giving us a ⭐**

[⭐ Star](https://github.com/liesliy/tlabel/stargazers) · [📦 PyPI](https://pypi.org/project/tlabel/) · [💬 Discord](https://discord.gg/2ab8EWaBM)

**Services:** Custom adapter development · Data pipeline consulting · Embodied AI tooling
**Contact:** WeChat `wxid_olqx5z6trmtn21` · Email `luoxi@touchlabelai.cn`

</div>
