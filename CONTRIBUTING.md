# Contributing to TLabel

Thank you for your interest in contributing to TLabel! As an open tactile data standard, TLabel relies on community contributions — especially new sensor adapters.

## How to Contribute

### Reporting Issues
- Use [GitHub Issues](https://github.com/liesliy/tlabel/issues) for bug reports and feature requests
- For Schema change proposals, please open a discussion first — Schema changes follow an RFC process

### Contributing a New Sensor Adapter

This is the most valuable type of contribution! If you have a tactile sensor not yet supported by TLabel, you can write an adapter.

#### Steps

1. **Fork** this repository
2. **Read** the [Design Document](docs/DESIGN.md) to understand the three-layer architecture and Schema V2 definition
3. **Implement** your adapter by subclassing `SensorAdapterBase`:

```python
from tlabel.adapters import SensorAdapterBase

class MySensorAdapter(SensorAdapterBase):
    """Adapter for MySensor tactile sensor."""
    
    sensor_name = "MySensor"
    sensor_type = "vision_based"  # or "distributed_array" or "hybrid"
    compliance_level = "L2"  # L1/L2/L3/L4 based on your sensor's capabilities
    
    def extract(self, raw_data) -> dict:
        """Map raw sensor data to TLabel Schema V2 fields."""
        result = {
            "contact": ...,           # Required (bool)
            "contact_centroid": ...,  # Required if contact (nullable)
            "slip_event": ...,        # Required (bool)
            "confidence": ...,        # Required (float 0-1)
            "compliance_level": self.compliance_level,  # Required
            "force_magnitude": ...,   # Required at L2+
            # Optional fields — set to null if unsupported
            "force_vector": None,
            "torque_vector": None,
            "slip_velocity": None,
            "texture_class": None,
            "object_deformation": None,
            "temperature": None,
            "manipulation_phase": None,
            "contact_region": None,
        }
        return result
```

4. **Add tests** in `tests/adapters/test_my_sensor.py`
5. **Update examples**: add a demo JSON in `examples/` showing your adapter's output
6. **Submit a Pull Request** with:
   - Adapter implementation
   - Tests (at least: schema compliance, capability declaration, null handling)
   - Brief description of your sensor and how the adapter works

#### Key Rules

- **Unsupported fields must be `null`, not `0`** — zero is a valid measurement; null means "not measurable"
- **`compliance_level` must match your sensor's actual capabilities** — don't claim L3 if you can only provide L2
- **Follow Schema V2 field names exactly** — no custom fields in the core annotation
- **One adapter per sensor type** — if your sensor is similar to an existing one, consider extending the existing adapter

### Schema Changes

TLabel's Schema (Layer 1) is intentionally stable. Changes require:
1. Open a GitHub Discussion proposing the change
2. Community review period (minimum 2 weeks)
3. If accepted, an RFC document is drafted
4. Schema version is bumped (semver)

### Code Style
- Python: follow existing style, use type hints
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/) format
- All PRs must pass CI (lint + tests across Python 3.9-3.12)

## Questions?
Open a [GitHub Discussion](https://github.com/liesliy/tlabel/discussions) or contact us at luoxi@touchlabelai.cn.
