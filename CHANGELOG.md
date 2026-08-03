# Changelog

All notable changes to the TLabel project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.18.0] - 2026-08-03

### Added
- **Image shape detection** (`detect_image_shape()`): Each adapter now reports its native tactile image dimensions `(H, W, C)`. Supports GelSight (240×320×3), PaXini (8×8×1), ToucHD, VTouch, and LeRobot converter integration with `image_shape`/`adapter` parameters
- **Annotation module** (`core/annotation.py`): Schema-aware annotation toolkit — `validate_annotations()`, `annotate_from_taxonomy()` (primitive auto-labeling from taxonomy rules), `annotate_events_from_data()` (event detection from signal patterns: contact_onset/loss, slip, force_spike, stable_grip), `clear_annotations()`, `get_annotation_summary()` with timeline view. `TLabelData` convenience methods: `.annotate_from_taxonomy()`, `.annotate_events_auto()`, `.validate_annotations()`, `.clear_annotations()`, `.get_annotation_summary()`
- **Tactile visualization** (`viewer/tactile_vis.py`): Rich visualization suite — `contact_heatmap()` (pseudo-color deformation overlay), `force_vector_field()` (quiver plot), `contact_region_overlay()` (centroid + region highlight), `composite_view()` (all-in-one from TLabelFrame), `frame_animation()` (GIF/HTML), `text_summary()` (text fallback). Three-tier degradation: Level 1 (numpy+image) → Level 2 (numpy only) → Level 3 (pure text)

### Fixed
- `contact_heatmap()` now accepts scalar intensity values (auto-broadcasts to full image)
- `force_vector_field()` now accepts list/tuple input (auto-converts to numpy array)
- `text_summary()` handles 2D force vectors (force_vector with only x,y components)

### Tests
- 52 unit tests passing (22 detect_image_shape + 30 annotation/visualization)
- 18 integration tests on real UniVTAC HDF5 data (schema_v2, 57+55 frames, GelSight Mini sensors)

## [0.17.2] - 2026-07-25

### Fixed
- **DEV-004**: Added missing `import math` in `tlabel/core/taxonomy.py` — `_resolve_field_value()` used `math.sqrt()` but math was only imported inside `evaluate_rule()`, causing `NameError`
- **DEV-005**: Lazy-load predict/quality/batch/augment modules via `__getattr__` — prevents eager sklearn/joblib import, reducing `import tlabel` time from ~1.06s to ~0.1s in full-extras environments
- **DEV-001**: `TLabelFrame.contact` and `TLabelFrame.slip_event` now return `bool` (matching TLabelSchemaV2 design) instead of `float`
- **DEV-002**: Added `_check_ml_deps()` helper in `tlabel/predict/__init__.py` with helpful `pip install tlabel[ml]` hint when ML dependencies are missing

## [0.17.1] - 2026-07-24

### Changed
- Documentation overhaul: aligned all docs to 14-dimensional Schema V2
- Updated README, annotation-spec, tlabel-format to reflect Compliance Level (L1-L4)

### Removed
- `examples/tacquad_benchmark/` directory (moved to [tlabel-bench](https://github.com/liesliy/tlabel-bench))

## [0.17.0] - 2026-07-24

### ⚠️ Breaking Changes
- **Schema V2 Only**: Removed all legacy `tlabel_v2` format support
- Schema expanded from 12 to **14 dimensions**: added `force_magnitude` (Required at L2+) and `compliance_level` (Required, L1-L4)
- `force_vector` downgraded from Required to **Optional (L3+)**
- Introduced **Compliance Level** system (L1 Basic → L4 Rich-Semantic)
- Introduced **dual base class architecture**: `DataAdapterBase` + `SensorAdapterBase`

### Added
- 7 public dataset adapters + 2 real-time sensor adapters
- CLI tools: `tlabel validate`, `tlabel info`, `tlabel export`
- JSON, CSV, HDF5 export support
- `compliance_level` auto-declaration per adapter

### Migration
- See [MIGRATION.md](MIGRATION.md) for v0.16 → v0.17 migration guide
- All code must use Schema V2 path; legacy format detection removed

## [0.16.0] - 2026-07-23

### Added
- Open architecture with dual base classes (`DataAdapterBase` + `SensorAdapterBase`)
- 7 dataset adapters (Daimon, PaXini, YCB-Slide, DM-TAC, etc.)
- CLI interface
- CSDN tutorial published

## [0.15.0] and earlier

Earlier versions used a feature-vector-centric design (18/22-dimensional). These have been superseded by the Schema V2 architecture introduced in v0.17.0.
