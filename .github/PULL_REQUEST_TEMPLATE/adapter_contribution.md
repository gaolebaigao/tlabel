---
name: "New Adapter"
about: "Contribute a new sensor or dataset adapter"
title: "adapter: "
labels: ["adapter", "needs-review"]
---

## Adapter Information

- **Adapter name**: (e.g., `my_sensor`)
- **Type**: 
  - [ ] Data Adapter (`DataAdapterBase`) — parsing offline dataset files
  - [ ] Sensor Adapter (`SensorAdapterBase`) — real-time sensor SDK
- **Sensor/Dataset name**: 
- **Manufacturer**: 
- **Source URL**: (link to dataset download or sensor product page)

## Implementation Checklist

- [ ] Adapter class inherits from `DataAdapterBase` or `SensorAdapterBase`
- [ ] Implements required methods: `name`, `load()`, `get_capabilities()`, `get_sensor_info()`
- [ ] (Sensor only) Implements `connect()`, `disconnect()`, `stream_frames()`, `is_connected()`
- [ ] Registered in `tlabel/core/registry.py` `_ADAPTER_MODULES` dict
- [ ] Output conforms to tlabel_v2 22-dim schema
- [ ] Sample data included (≤10MB) in `tests/data/` or data download script
- [ ] Unit tests pass: `pytest tests/test_adapter_<name>.py -v`
- [ ] Schema validation passes: `tlabel validate tests/data/<sample>`
- [ ] README or docstring explains sensor/dataset specifics

## Testing

```bash
# Run adapter tests
pytest tests/test_adapter_<name>.py -v

# Validate sample data
tlabel validate tests/data/<sample_file_or_dir>

# Full test suite
pytest tests/ -v
```

## Capabilities (22-dim)

List the tlabel_v2 dimensions your adapter can produce:

| Dimension | Supported | Notes |
|-----------|-----------|-------|
| contact | ✅/❌ | |
| deformation_magnitude | ✅/❌ | |
| force_peak | ✅/❌ | |
| ... | ... | ... |

(Or paste output of `tlabel info <name>`)

## Sample Data

- Format: (e.g., `.h5`, `.parquet`, directory)
- Size: (e.g., 2.3 MB)
- Source: (e.g., "Downloaded from https://... / Recorded with GelSight Mini")
- License: (e.g., "CC-BY-4.0 / MIT / Same as upstream dataset")

## Additional Notes

Any sensor-specific quirks, known limitations, or setup instructions for reviewers.
