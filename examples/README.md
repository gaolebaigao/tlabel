# Examples

## Demo Data

Synthetic datasets for quick testing — no real sensor hardware needed.

| File | Sensor | Frames | Dimensions | Description |
|------|--------|:------:|:----------:|-------------|
| `demo_gelsight.json` | GelSight Mini | 150 | 14 | Grasp-hold-release with optical flow |
| `demo_paxini.json` | PaXini PXCap | 120 | 14 | Grasp demo (subset of 14-dim Schema V2) |

### Usage

```python
import json
from tlabel.core.types import TLabelFrame, TLabelData, TLabelSchemaV2

with open("examples/data/demo_gelsight.json") as f:
    raw = json.load(f)

frames = [
    TLabelFrame(
        frame_idx=f["frame_idx"],
        timestamp_s=f["timestamp_s"],
        schema_v2=TLabelSchemaV2(**f["schema_v2"])
    )
    for f in raw["frames"]
]
data = TLabelData(frames, raw["sensor"], raw["episode"], raw["capabilities"])
data.review()
```

## Generate Your Own Demo Data

```bash
python examples/generate_demo_data.py
```

This creates synthetic 14-dim Schema V2 demo files in `examples/data/`.
