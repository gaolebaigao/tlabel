# TLabel

**A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

[![PyPI](https://img.shields.io/pypi/v/tlabel)](https://pypi.org/project/tlabel/)
[![Tests](https://github.com/liesliy/tlabel/actions/workflows/tests.yml/badge.svg)](https://github.com/liesliy/tlabel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TLabel is the first cross-sensor tactile annotation schema with capability declarations and Compliance Level stratification. It enables heterogeneous tactile sensors — regardless of operating principle — to produce compatible 14-dimensional semantic annotations while preserving their unique strengths.

## Why TLabel?

Tactile datasets today ship as raw sensor signals without semantic annotations. Each sensor type demands its own ad-hoc processing, and results from different sensors cannot be compared or fused. TLabel addresses this by:

- **Standardizing annotations** at the semantic level — 14 dimensions covering spatial, mechanical, surface, dynamic, and meta perceptions
- **Declaring capabilities** — each sensor adapter explicitly states which dimensions it can and cannot annotate
- **Stratifying compliance** — Compliance Level (L1–L4) ensures every sensor participates at its appropriate information density
- **Enabling cross-sensor comparison** through a shared output format

## Key Results

| Metric | Result |
|--------|--------|
| Schema | 14 semantic dimensions + Compliance Level (L1–L4) |
| Schema version | v2.1.0 |
| Hard errors across 750K+ observations | **0** |
| Cross-scenario generalization accuracy | **+7.93%** (p=0.029) |
| Slip-risk detection F1 | **+10.35%** (p<0.001) |
| Sensors validated | Daimon-Infinity (GelSight) + PaXini PXCap (6D Hall-effect) + DIGIT (visuo-tactile) |

## Quick Start

### Install

```bash
pip install tlabel
```

### Use a TLabel adapter

```python
from tlabel.adapters import DaimonInfinityAdapter, PaxiniAdapter

# Load adapter with capability declarations
adapter = DaimonInfinityAdapter(sensor_config)

# Check what this sensor can annotate
print(adapter.capabilities)
# -> {'contact': True, 'contact_centroid': True, 'contact_region': True,
#     'force_magnitude': True, 'force_vector': False, 'torque_vector': False,
#     'slip_event': True, 'slip_velocity': True, 'manipulation_phase': True,
#     'texture_class': True, 'object_deformation': True, 'temperature': False,
#     'confidence': True}

# Check compliance level
print(adapter.compliance_level)
# -> 'L2'

# Annotate an episode
annotations = adapter.annotate(episode_data)
```

### Read TLabel annotations

```python
from tlabel import TLabelReader

reader = TLabelReader("path/to/annotations.tlabel.json")
for frame in reader.frames():
    print(frame.contact, frame.contact_centroid, frame.force_magnitude,
          frame.slip_event, frame.confidence, frame.compliance_level)
```

## TLabel Format

Each TLabel annotation file follows this structure:

```json
{
  "schema_version": "2.1.0",
  "sensor_info": { ... },
  "capabilities": {
    "contact": true,
    "contact_centroid": true,
    "contact_region": true,
    "force_magnitude": true,
    "force_vector": false,
    "torque_vector": false,
    "slip_event": true,
    "slip_velocity": true,
    "manipulation_phase": true,
    "texture_class": true,
    "object_deformation": true,
    "temperature": false,
    "confidence": true
  },
  "episodes": [ ... ]
}
```

Capability declarations are the core innovation: each adapter declares which of the 14 semantic dimensions it can and cannot annotate. Only supported fields appear in the output. The Compliance Level (L1–L4) mechanism ensures that sensors with different physical capabilities can all participate at their appropriate information density — no forced alignment, no data fabrication.

### Compliance Levels

| Level | Name | Required Fields | Example Sensors |
|-------|------|----------------|-----------------|
| **L1** | Basic Tactile | contact, contact_centroid, slip_event, confidence | Single-point resistive, proximity |
| **L2** | Force-Aware | L1 + force_magnitude | Paxini, YCB-Slide, GelSight |
| **L3** | Full-Vector | L2 + force_vector | ToucHD, calibrated DM-TAC |
| **L4** | Rich-Semantic | L3 + all optional fields | BioTac, next-gen multimodal |

See [docs/tlabel-format.md](docs/tlabel-format.md) for the full specification.

## Documentation

| Document | Description |
|----------|-------------|
| [TLabel Format Spec](docs/tlabel-format.md) | Complete annotation schema specification (14 dimensions + Compliance Level) |
| [Annotation Spec](docs/annotation-spec.md) | Annotation methodology and guidelines |
| [Design Document](docs/TLabel_Design_Document.md) | Core design decisions and architecture |

## Paper

**TLabel: A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

*Xi Luo* (Niuxu Tech)

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
  <a href="https://www.niuxutech.com">Niuxu Tech</a> · Hangzhou, China
</p>
