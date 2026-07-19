# Changelog

All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.15.0] - 2026-07-19

### 🎉 Major Highlights

This release introduces **adapter architecture refactoring** with table-driven registration and the **PaXini GEN3 real-time SDK adapter** — enabling live tactile data acquisition with unified annotation pipeline.

### ✨ Added

#### PaXini GEN3 Real-Time Adapter (New)
- New `paxini_gen3` adapter with full SDK integration (`pip install paxini-sdk`)
- **22-dimensional feature extraction** from live TactileFrame data:
  - Direct SDK fields: contact_mask, total_force_n, contact_centroid, contact_area_mm2
  - Pressure normalization: 0-600kPa → 0-1 range
  - Derived features: force distribution, center of pressure, contact geometry
- **Slip detection** with dual mechanism:
  - Centroid displacement tracking (threshold: 0.15mm)
  - Force change rate monitoring (threshold: 0.25)
- **Pseudo tactile image generation** from contact_mask + pressure_map
- **Auto layout detection**: gen3_1 (single fingertip), gen3_2 (fingertip+palm), gen3_5 (five-finger)
- Temporal features: force history, contact stability metrics

#### Adapter Architecture Refactoring
- **Table-driven registration**: `_ADAPTER_MODULES` dict in `registry.py` — adding new adapter requires only 1 line change (was 5 files)
- **Standardized naming convention**: `brand_model` pattern (e.g., `paxini_gen3`, `daimon_dm_tac`)
- **File reorganization**:
  - `paxini.py` → `paxini_dataset.py` (HDF5 dataset adapter)
  - `daimon.py` → `daimon_dataset.py` (Parquet dataset adapter)
  - New: `paxini_gen3.py`, `daimon_dm_tac.py` (real-time adapters)
- **Backward compatible**: All existing API calls (`tlabel.load()`, adapter keys) remain unchanged
- 11 adapters successfully registered after refactoring

### 🔧 Changed

- Version bumped from 0.14.0 to 0.15.0
- Adapter registration moved from hardcoded if-blocks to declarative dict
- Developer guide updated with new adapter SOP (Standard Operating Procedure)
- Test suite: 69 passed, all green ✅

### 📦 Adapter Registry (12 total: 11 functional + 1 placeholder)

| Adapter Key | File | Type | Description |
|-------------|------|------|-------------|
| `gelsight` | `gelsight.py` | Dataset | GelSight Mini / DIGIT |
| `paxini` | `paxini_dataset.py` | Dataset | PaXini PXCap HDF5 |
| `paxini_gen3` | `paxini_gen3.py` | **Real-time** | PaXini GEN3 SDK |
| `paxini_px6d` | `paxini_px6d.py` | Real-time | PaXini PX6D 6-axis force (placeholder) |
| `daimon` | `daimon_dataset.py` | Dataset | Daimon-Infinity Parquet |
| `daimon_dm_tac` | `daimon_dm_tac.py` | Real-time | Daimon DM-Tac USB (skeleton) |
| `tlabel` | `tlabel_format.py` | Meta | TLabel native format |
| `touchd` | `touchd.py` | Dataset | ToucHD dataset |
| `univtac` | `univtac.py` | Dataset | UniVTAC dataset |
| `vtouch` | `vtouch.py` | Dataset | VTouch dataset |
| `ycb_slide` | `ycb_slide.py` | Dataset | YCB-Slide dataset |
| `tacquad` | `tacquad.py` | Dataset | TacQuad dataset |

---

## [0.3.0] - 2026-06-18

### 🎉 Major Highlights

This release fixes all 4 blocking bugs identified in rc2 testing and introduces the **MLEngine** — a gradient-boosting-based pre-annotation engine with proper calibration, continuous contact prediction, and graceful degradation.

### ✨ Added

#### MLEngine (New)
- New `tlabel.predict.ml_engine.MLEngine` with per-field models:
  - **Contact**: GradientBoostingRegressor (continuous output, not binary) — fixes Bug4
  - **Slip**: GradientBoostingClassifier with CalibratedClassifierCV (Platt scaling) — fixes Bug2
  - **Phase**: Automatically skipped (rule engine recommended, ML accuracy too low)
- `MLEngineConfig` with `enabled_fields`, `use_calibration`, `min_samples` options
- Graceful degradation: when training data is insufficient, falls back to rule engine — fixes Bug1
- Model save/load via `save_models()` / `load_models()` (joblib serialization)
- `fit_report()` returns per-field training status and calibration info

#### Cascade Reverse Constraints (Bug3 Fix)
- `slip_event > 0.5` when `contact < 0.5` → auto-sets `contact = 1.0` and `phase = "slip"`
- `force_magnitude > 0` when `contact < 0.5` → auto-sets `contact = 1.0`
- Existing forward cascade (contact=0 → zero forces/slip) unchanged

#### auto_label() Engine Selection
- `TLabelData.auto_label(engine="auto")` — tries ML first, falls back to rules (default)
- `TLabelData.auto_label(engine="ml")` — ML only, returns error if unavailable
- `TLabelData.auto_label(engine="rule")` — rule engine only
- New `enabled_fields` parameter for per-field ML control

#### Dependency
- New `[ml]` extras: `pip install tlabel[ml]` installs `scikit-learn>=1.0` and `joblib>=1.0`
- `[all]` extras now includes ML dependencies

### 🔧 Changed

- Version bumped from 0.2.0b3 to 0.3.0
- `PredictEngine` unchanged (backward compatible)
- `predict/__init__.py` now exports `MLEngine`, `MLEngineConfig` (graceful ImportError if sklearn missing)

### 🐛 Fixed

- **Bug1**: Small data training no longer crashes — minimum sample checks + fallback to rule engine
- **Bug2**: Calibration actually works — uses `CalibratedClassifierCV(cv=3)` instead of broken `cv='prefit'`
- **Bug3**: Cascade reverse constraints — slip/force now correctly set contact
- **Bug4**: Contact prediction is continuous (regression) — 78% accuracy vs 65% threshold-based

---

## [0.2.0b1] - 2026-06-11

### 🎉 Major Highlights

This release focuses on **downstream compatibility** and **user experience improvements**. We've enhanced metadata support, added LeRobot converters, introduced HDF5 export, and created comprehensive tutorials for all supported sensors.

### ✨ Added

#### Metadata Enhancement
- Added `sensor_id` and `calibration_params` fields to `TLabelData.__init__()` for better sensor identification and calibration tracking
- Enhanced `to_dict()` output with `feature_names` list (22 dimension names) for downstream frameworks
- Added `is_first` and `is_last` episode boundary markers to frame exports (critical for reinforcement learning and temporal modeling)
- Default sensor IDs for all adapters: `"gelsight_main"`, `"paxini_pxcap"`, `"daimon_taclaw"`

#### LeRobot Integration
- New `tlabel.converters.lerobot` module with bidirectional conversion:
  - `lerobot_to_tlabel()`: Convert LeRobot Parquet datasets to TLabel Format v2
  - `tlabel_to_lerobot()`: Export TLabel annotations back to LeRobot schema
- Automatic handling of `meta/info.json` and Parquet file reading/writing
- Support for custom tactile field paths (default: `"observation.tactile"`)

#### HDF5 Export Support
- Added `_export_hdf5()` function in `tlabel/export/writer.py`
- Exports include: tactile data, metadata, episode boundaries, and calibration info
- Compatible with PyTorch/TensorFlow data loaders

#### Comprehensive Sensor Tutorials
- Created detailed tutorials for all 6 supported sensors:
  - GelSight: `examples/tutorial_gelsight.md`
  - PaXini: `examples/tutorial_paxini.md`
  - Daimon: `examples/tutorial_daimon.md`
  - ToucHD: `examples/tutorial_touchd.md`
  - UniVTAC: `examples/tutorial_univtac.md`
  - VTouch: `examples/tutorial_vtouch.md`
- Each tutorial covers: data loading, visualization, feature extraction, export examples

#### FTP-1 Export Enhancements
- Added `export_ftp1()` method to `TLabelData` class
- Support for both single-file and batch export modes
- Automatic data validation before export

### 🔧 Changed

- Version bumped from 0.1.0 to 0.2.0b1
- Refactored `tlabel/converters/` module structure for better organization
- Improved error messages with sensor-specific hints
- Updated `README.md` with quick start examples for all sensors

### 📚 Documentation

- Added comprehensive API documentation for all public methods
- Created `docs/architecture.md` explaining TLabel's design philosophy
- Added migration guide for v0.1.0 users

---

## [0.2.0a7] - Previous Release

*Earlier alpha releases focused on core functionality and initial adapter implementations.*

