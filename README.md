# TLabel

**A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data**

[![Paper](https://img.shields.io/badge/Paper-Figshare-blue)](https://doi.org/10.6084/m9.figshare.32527053)
[![Format Spec](https://img.shields.io/badge/Spec-TLabel_Format_v2-green)](docs/tlabel-format.md)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What is TLabel?

TLabel is the first cross-sensor tactile annotation schema with **capability declarations**. It enables heterogeneous tactile sensors — regardless of operating principle — to produce compatible semantic annotations while preserving their unique strengths.

### The Problem

Tactile datasets today ship as raw sensor signals (video frames, HDF5 arrays, custom blobs) without semantic annotations. Each sensor type demands its own ad-hoc processing, and results from different sensors cannot be compared or fused.

### The Solution

TLabel Format defines **10 semantic dimensions** for tactile annotation. Each sensor adapter declares which dimensions it can and cannot annotate via a `capabilities` dictionary, and only outputs supported fields.

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  GelSight   │───▶│  Adapter     │───▶│ TLabel JSON │
│  (images)   │    │  (capabilities)│   │ (unified)   │
└─────────────┘    └──────────────┘    └─────────────┘
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  PaXini     │───▶│  Adapter     │───▶│ TLabel JSON │
│  (vectors)  │    │  (capabilities)│   │ (unified)   │
└─────────────┘    └──────────────┘    └─────────────┘
```

## Quick Start

### Installation

```bash
git clone https://github.com/liesliy/tlabel.git
cd tlabel
pip install -r requirements.txt
```

### Annotate a Dataset

```python
from tlabel.adapters import GelSightAdapter, PaxiniAdapter

# GelSight (vision-based)
adapter = GelSightAdapter(
    data_path="path/to/daimon-infinity/",
    capabilities=["contact_detection", "force_level", "slip_detection", 
                  "slip_direction", "texture", "3d_shape", "shear_force"]
)
annotations = adapter.annotate()
adapter.save(annotations, "output_gelsight.json")

# PaXini (6D Hall-effect array)
adapter = PaxiniAdapter(
    data_path="path/to/paxini-hdf5/",
    capabilities=["contact_detection", "force_level", "slip_detection",
                  "whole_hand_coord"]
)
annotations = adapter.annotate()
adapter.save(annotations, "output_paxini.json")
```

### Validate Annotations

```python
from tlabel.validation import validate_annotations

report = validate_annotations("output_gelsight.json")
print(f"Hard errors: {report.hard_errors}")  # Should be 0
print(f"Anomaly rate: {report.anomaly_rate:.2%}")
print(f"Grade: {report.grade}")  # A/B/C/D
```

## 10 Semantic Dimensions

| # | Dimension | Description | Scope |
|---|-----------|-------------|-------|
| 1 | `contact_detection` | Contact state classification | All sensors |
| 2 | `force_level` | Multi-level force classification | All sensors |
| 3 | `slip_detection` | Object slip detection | Most sensors |
| 4 | `slip_direction` | Slip direction vector | Vision-based |
| 5 | `texture` | Surface texture classification | Vision-based |
| 6 | `3d_shape` | Local surface shape | Vision-based |
| 7 | `shear_force` | Tangential force component | Vision-based |
| 8 | `whole_hand_coord` | Multi-region coordination | Arrays |
| 9 | `vibration` | High-freq oscillation (>200Hz) | Reserved |
| 10 | `temperature` | Thermal contact info | Reserved |

## Validated Sensors

| Sensor | Type | Episodes | Observations | Hard Errors | Anomaly Rate |
|--------|------|----------|-------------|-------------|-------------|
| Daimon-Infinity (GelSight) | Vision-based | 94 | 370K+ | **0** | 2.91% |
| PaXini PXCap (6D Hall) | Distributed array | 15 | 219K+ | **0** | 0.14% |

### Downstream Benefits

Adding TLabel annotations to raw features:
- **+7.93%** cross-scenario generalization accuracy (p<0.01)
- **+10.35%** slip-risk F1 score (p<0.001)

## Output Format

Each annotation is a JSON object:

```json
{
  "schema_version": "2.0",
  "sensor_info": {
    "type": "gelsight",
    "model": "Daimon-Infinity",
    "spatial_layout": "5_fingertips"
  },
  "capabilities": {
    "contact_detection": true,
    "force_level": true,
    "slip_detection": true,
    "slip_direction": true,
    "whole_hand_coord": false
  },
  "frames": [
    {
      "frame_id": 0,
      "contact_state": "contact",
      "force_level": "medium",
      "slip_detected": false,
      "phase": "grasp",
      ...
    }
  ]
}
```

## Project Structure

```
tlabel/
├── README.md
├── requirements.txt
├── docs/
│   └── tlabel-format.md          # Full specification
├── adapters/
│   ├── gelsight_adapter.py       # GelSight/Daimon adapter
│   └── paxini_adapter.py         # PaXini 6D Hall adapter
├── validation/
│   └── validate.py               # 8-item consistency checker
├── downstream/
│   └── evaluate.py               # Downstream task evaluation
└── examples/
    └── sample_output.json        # Example annotation
```

## Adding a New Sensor

To add support for a new tactile sensor:

1. Create an adapter class that inherits from `BaseAdapter`
2. Implement `compute_capabilities()` — declare which of the 10 dimensions your sensor supports
3. Implement `annotate_frame()` — map raw sensor signals to TLabel semantic fields
4. Run validation — ensure zero hard errors

```python
from tlabel.adapters import BaseAdapter

class MySensorAdapter(BaseAdapter):
    def compute_capabilities(self):
        return {
            "contact_detection": True,
            "force_level": True,
            "slip_detection": True,
            # ... declare what your sensor can do
        }
    
    def annotate_frame(self, raw_frame):
        return {
            "contact_state": self._detect_contact(raw_frame),
            "force_level": self._classify_force(raw_frame),
            # ...
        }
```

## Citation

If you use TLabel in your research, please cite:

```bibtex
@article{luo2026tlabel,
  title={TLabel: A Unified Annotation Framework for Cross-Sensor Tactile Manipulation Data},
  author={Luo, Xi},
  journal={figshare},
  year={2026},
  doi={10.6084/m9.figshare.32527053}
}
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contact

Xi Luo — [luoxi@touchlabelai.cn](mailto:luoxi@touchlabelai.cn)

Niuxu Tech — Hangzhou, China
