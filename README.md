# TLabel

**A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

[![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/submit/7651949)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TLabel is the first cross-sensor tactile annotation schema with capability declarations. It enables heterogeneous tactile sensors to produce compatible semantic annotations while preserving their unique strengths.

## Why TLabel?

Tactile datasets today ship as raw sensor signals without semantic annotations. Each sensor type demands its own ad-hoc processing, and results from different sensors cannot be compared or fused. TLabel addresses this by:

- **Standardizing annotations** at the semantic level (contact, force, slip, manipulation phases)
- **Declaring capabilities** - each sensor adapter explicitly states which dimensions it can and cannot annotate
- **Enabling cross-sensor comparison** through a shared output format

## Key Results

| Metric | Result |
|--------|--------|
| Hard errors across 590K+ observations | **0** |
| Cross-scenario generalization accuracy | **+7.93%** (p=0.029) |
| Slip-risk detection F1 | **+10.35%** (p<0.001) |
| Sensors validated | Daimon-Infinity + PaXini PXCap + GelSight + DIGIT |

## Cross-Sensor Validation

TLabel enables semantic alignment across sensors with fundamentally different physics:

| TLabel Dimension | Daimon | PaXini | GelSight | DIGIT |
|:---|:---:|:---:|:---:|:---:|
| contact | Yes | Yes | Yes | Yes |
| force_magnitude | Yes | Yes | Yes | Yes |
| slip_event | Yes | Partial | Yes | Yes |
| manipulation_phase | Yes | Yes | Yes | Yes |
| **Core coverage** | **8/11** | **6/11** | **5/11** | **5/11** |

**4 core dimensions achieved full cross-sensor coverage** - contact, force_magnitude, slip_event, and manipulation_phase are annotated across all four sensor types, demonstrating that TLabel unifies semantic interpretation regardless of sensing modality.

## Quick Start

### Read TLabel annotations

```python
from tlabel import TLabelReader

reader = TLabelReader("path/to/annotations.tlabel.json")
for frame in reader.frames():
    print(frame.contact, frame.force_magnitude, frame.slip_event)
```

### Use a TLabel adapter

```python
from tlabel.adapters import DaimonInfinityAdapter, PaxiniAdapter

adapter = DaimonInfinityAdapter(sensor_config)
print(adapter.capabilities)
annotations = adapter.annotate(episode_data)
```

## TLabel Format

Each TLabel annotation file follows this structure:

```json
{
  "schema_version": "0.2.0",
  "sensor_info": { ... },
  "capabilities": {
    "contact": true,
    "force_magnitude": true,
    "slip_event": true,
    "manipulation_phase": true,
    "texture": true,
    "whole_hand_coordination": false,
    "object_deformation": false
  },
  "episodes": [ ... ]
}
```

Capability declarations are the core innovation: each adapter declares which semantic dimensions it can and cannot annotate. Only supported fields appear in the output. This means a vision-based sensor and a Hall-effect array produce the same format with different coverage - no forced alignment, no data fabrication.

See [docs/tlabel-format.md](docs/tlabel-format.md) for the full specification.

## Documentation

| Document | Description |
|----------|-------------|
| [TLabel Format Spec](docs/tlabel-format.md) | Complete annotation schema specification |
| [Annotation Spec](docs/annotation-spec.md) | Annotation methodology and guidelines |

## Paper

**TLabel: A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

*Xi Luo* (Niuxu Tech)

[[arXiv]](https://arxiv.org/submit/7651949) | [[PDF]](paper/tlabel-paper.pdf)

LaTeX source available in [`paper/`](paper/).

### Citation

```bibtex
@article{luo2026tlabel,
  title={TLabel: A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data},
  author={Luo, Xi},
  journal={arXiv preprint},
  year={2026}
}
```

## Validation

TLabel has been validated on four sensors with fundamentally different physics:

| Sensor | Type | Key Capability |
|--------|------|---------------|
| Daimon-Infinity | Vision-based GelSight | 8/11 dimensions - widest coverage |
| PaXini PXCap | 6D Hall-effect array | Multi-finger coordination |
| GelSight (Meta) | Vision-based elastomer | Force estimation from optical flow |
| DIGIT (Meta) | Vision-based compact | Slip detection from displacement |

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

The TLabel Format specification is free to implement by anyone. We encourage the community to build adapters for additional sensors.

## Acknowledgments

TLabel builds on insights from the tactile sensing community, including [Open X-Embodiment](https://robotics-transformer-x.github.io/), [LeRobot](https://github.com/huggingface/lerobot), and [OpenTouch](https://opentouch.ai/).

---

<p align="center">
  <strong>TouchLabel AI</strong> - Tactile Data Annotation Infrastructure<br>
  <a href="https://www.niuxutech.com">Niuxu Tech</a> · Hangzhou, China
</p>
