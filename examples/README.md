# Examples

## Demo Data

Synthetic datasets for quick testing — no real sensor hardware needed.

| File | Sensor | Frames | Dimensions | Description |
|------|--------|:------:|:----------:|-------------|
| `demo_gelsight.json` | GelSight Mini | 150 | 22 | Grasp-hold-release with optical flow |
| `demo_paxini.json` | PaXini PXCap | 120 | 20 | Grasp demo without optical flow |

### Usage

```python
import json
from tlabel.core.types import TLabelFrame, TLabelData

with open("examples/data/demo_gelsight.json") as f:
    raw = json.load(f)

frames = [
    TLabelFrame(f["frame_idx"], f["timestamp_s"], f["tlabel_v2"],
                f.get("manipulation_phase", "idle"), f.get("confidence", 1.0))
    for f in raw["frames"]
]
data = TLabelData(frames, raw["sensor"], raw["episode"], raw["capabilities"])
data.review()
```

## Generate Your Own Demo Data

```bash
python examples/generate_demo_data.py
```

This creates synthetic 22-dim (GelSight) and 20-dim (PaXini) demo files in `examples/data/`.
