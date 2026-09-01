# TLabel

**A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

[![PyPI](https://img.shields.io/pypi/v/tlabel)](https://pypi.org/project/tlabel/)
[![Tests](https://github.com/liesliy/tlabel/actions/workflows/tests.yml/badge.svg)](https://github.com/liesliy/tlabel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Downloads](https://img.shields.io/pepy/dt/tlabel)](https://pepy.tech/projects/tlabel)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.22227847.svg)](https://doi.org/10.5281/zenodo.22227847)
[![中文文档](https://img.shields.io/badge/README-中文-red)](README_CN.md)

TLabel is the first cross-sensor tactile annotation schema with capability declarations and Compliance Level stratification. It enables heterogeneous tactile sensors — regardless of operating principle — to produce compatible 14-dimensional semantic annotations while preserving their unique strengths.

> **TL;DR** — The Unicode for tactile data: one standard schema, every sensor.

## Why TLabel?

Tactile datasets today ship as raw sensor signals without semantic annotations. Each sensor type demands its own ad-hoc processing, and results from different sensors cannot be compared or fused. TLabel addresses this by:

- **Standardizing annotations** at the semantic level — 14 dimensions covering spatial, mechanical, surface, dynamic, and meta perceptions
- **Declaring capabilities** — each sensor adapter explicitly states which dimensions it can and cannot annotate
- **Stratifying compliance** — Compliance Level (L1–L4) ensures every sensor participates at its appropriate information density
- **Enabling cross-sensor comparison** through a shared output format

## Quick Start

### Install

```bash
pip install tlabel
```

### Load and explore data

```python
import tlabel

# Load tactile data (auto-detects sensor format)
data = tlabel.load("path/to/sensor_data.pkl")

# Or try the built-in demo — no files needed
data = tlabel.demo("gelsight")

# Inspect annotation metadata
print(data.describe())
# -> {'num_frames': 500, 'sensor': 'gelsight', 'compliance_level': 'L2', ...}
```

### Interactive annotation (Jupyter)

```python
# Open the bilingual annotation panel (Chinese / English)
data.review()
```

### Export to training formats

```python
# JSON / CSV for analysis
data.export("output.json")

# FTP-1 Zarr for foundation model training
data.export_ftp1("output.zarr")

# LeRobot format
from tlabel.converters import tlabel_to_lerobot
tlabel_to_lerobot("annotations.json", "lerobot_episode/")
```

### CLI

```bash
tlabel list                       # List all registered adapters
tlabel info gelsight              # Adapter details & compliance level
tlabel validate data.json         # Schema compliance check
```

### Install optional dependencies

```bash
pip install tlabel[gelsight]      # GelSight / DIGIT (.pkl)
pip install tlabel[paxini]        # PaXini PXCap (.h5)
pip install tlabel[daimon]        # Daimon DM-TacClaw (.parquet)
pip install tlabel[ftp1]          # FTP-1 export (zarr)
pip install tlabel[all]           # Everything
```

## Schema V2 — 14 Dimensions, 4 Compliance Levels

TLabel Schema V2 defines **14 semantic dimensions**, with **Compliance Levels (L1–L4)** indicating annotation completeness:

| # | Dimension | Type | Required |
|---|-----------|------|----------|
| 1 | `contact` | bool | ✅ Required |
| 2 | `contact_centroid` | [float × 2] | ✅ Required (when contact) |
| 3 | `force_magnitude` | float | ✅ Required (L2+) |
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

### Compliance Levels

| Level | Name | Required Fields | Example Sensors |
|-------|------|----------------|-----------------|
| **L1** | Basic Tactile | contact, contact_centroid, slip_event, confidence | Single-point resistive, proximity |
| **L2** | Force-Aware | L1 + force_magnitude | Paxini, YCB-Slide, GelSight |
| **L3** | Full-Vector | L2 + force_vector | ToucHD, calibrated DM-TAC |
| **L4** | Rich-Semantic | L3 + all optional fields | BioTac, next-gen multimodal |

Capability declarations are the core innovation: each adapter declares which of the 14 semantic dimensions it can and cannot annotate. Only supported fields appear in the output. No forced alignment, no data fabrication.

## Supported Sensors

### Dataset Adapters (offline data loading)

| Sensor | Type | Format | Level |
|:-------|:-----|:-----|:-----:|
| GelSight Mini / DIGIT | Visuo-tactile | `.pkl` | L3 |
| Daimon DM-TacClaw | Multimodal | `.parquet` | L3 |
| PaXini PXCap | Force array | `.h5` | L2 |
| UniVTAC | Visuo-tactile | `.hdf5` | L3 |
| TacQuad (AnyTouch) | Multi-sensor | directory | L3 |
| VTouch | Visuo-tactile | `.h5` | L3 |
| YCB-Slide | Visuo-tactile | `.npy` | L3 |

### Real-time Sensor Adapters (hardware)

| Sensor | Type | Connection | Level |
|:-------|:-----|:-----------|:-----:|
| PaXini GEN3 | Force array | SDK | L2 |
| Daimon DM-Tac | Visuo-tactile | USB / `.avi` | L3 |

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Schema                                │
│  14 semantic dimensions + Compliance Level L1-L4│
├─────────────────────────────────────────────────┤
│  Layer 2: Adapters                              │
│  DataAdapterBase │ SensorAdapterBase             │
│  (7 built-in + community-extensible)            │
├─────────────────────────────────────────────────┤
│  Layer 3: Downstream                            │
│  Feature derivation · Augmentation · Export      │
│  PredictEngine · FTP-1 · LeRobot · RLDS · ROS2 │
└─────────────────────────────────────────────────┘
```

- **DataAdapterBase** — subclass to add file-based sensor support (~30 min)
- **SensorAdapterBase** — subclass to add real-time hardware support
- Both share the unified export pipeline

## Export Formats

| Format | Purpose | Usage |
|--------|---------|-------|
| JSON / CSV | General analysis | `data.export("out.json")` |
| FTP-1 Zarr | Foundation model training | `data.export_ftp1("out.zarr")` |
| LeRobot | LeRobot framework | `tlabel_to_lerobot(src, dst)` |
| RLDS | RLDS/TFDS pipeline | `converters.rlds` module |
| ROS2 | Robot runtime | Stub (coming soon) |

## Key Results

| Metric | Result |
|--------|--------|
| Schema | 14 semantic dimensions + Compliance Level (L1–L4) |
| Schema version | v2.1.0 |
| Hard errors across 750K+ observations | **0** |
| Cross-scenario generalization accuracy | **+7.93%** (p=0.029) |
| Slip-risk detection F1 | **+10.35%** (p<0.001) |
| Sensors validated | Daimon-Infinity (GelSight) + PaXini PXCap (6D Hall-effect) + DIGIT (visuo-tactile) |

## Documentation

| Document | Description |
|----------|-------------|
| [TLabel Format Spec](docs/tlabel-format.md) | Complete annotation schema specification |
| [Annotation Spec](docs/annotation-spec.md) | Annotation methodology and guidelines |
| [Design Document](docs/TLabel_Design_Document.md) | Core design decisions and architecture |
| [中文文档](README_CN.md) | Chinese version of this README |

## Contributing

TLabel is designed to be extensible. Add your sensor in ~30 minutes:

1. Fork [contrib/adapter-template/](contrib/adapter-template/)
2. Subclass `DataAdapterBase` or `SensorAdapterBase`
3. Submit a PR or publish as a standalone package

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Paper

**TLabel: A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

*Xi Luo, Sheng Wu* (Niuxu Tech)

[[PDF]](paper/tlabel-paper.pdf)

LaTeX source available in [`paper/`](paper/).

## Validation

TLabel has been validated on three sensors with fundamentally different physics:

| Sensor | Type | Episodes | Tasks | Hard Errors | Compliance Level |
|--------|------|----------|-------|-------------|-----------------|
| Daimon-Infinity | Vision-based GelSight | 94 | 6 | 0 | L2 |
| PaXini PXCap | 6D Hall-effect array | 15 | 7 | 0 | L2 |
| DIGIT | Visuo-tactile | 12 | 4 | 0 | L2 |

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

The TLabel Format specification is free to implement by anyone. We encourage the community to build adapters for additional sensors.

## Acknowledgments

TLabel builds on insights from the tactile sensing community, including [Open X-Embodiment](https://robotics-transformer-x.github.io/), [LeRobot](https://github.com/huggingface/lerobot), and [OpenTouch](https://opentouch.ai/).

---

<p align="center">
  <strong>TouchLabel AI</strong> — Tactile Data Annotation Infrastructure<br>
  <a href="https://github.com/liesliy/tlabel">GitHub</a> ·
  <a href="https://pypi.org/project/tlabel/">PyPI</a> ·
  <a href="https://discord.gg/2ab8EWaBM">Discord</a><br>
  <a href="https://www.niuxutech.com">Niuxu Tech</a> · Hangzhou, China
</p>
