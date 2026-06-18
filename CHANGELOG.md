# Changelog

All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Bug4**: Contact prediction is continuous (regression) — 78+ unique values vs. binary 0/1

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
- Exports include:
  - `timestamps` dataset
  - `frame_indices` dataset
  - `is_first` / `is_last` episode boundary arrays
  - `tactile_features` matrix (all 22 dimensions)
  - `metadata` group with sensor_id, calibration, and schema info
- Requires `h5py` dependency (included in `[all]` extras)

#### Comprehensive Tutorials
- **`docs/tutorial-gelsight.md`**: Complete GelSight/DIGIT tutorial covering:
  - Prerequisites and environment setup
  - Data loading from `.pkl` files
  - Interactive review and correction workflow
  - Export options (JSON, CSV, HDF5)
  - Advanced tips and troubleshooting
- **`docs/tutorial-paxini.md`**: PaXini PXCap tutorial with:
  - HDF5 file structure explanation
  - Force-only sensor considerations (20 dims vs 22)
  - Calibration parameter extraction
- **`docs/tutorial-daimon.md`**: Daimon DM-TacClaw tutorial including:
  - LeRobot directory structure requirements
  - FFV1 video decoding with ffmpeg
  - Multi-modal data fusion (tactile + robot state)
  - Graceful degradation when videos are missing

#### Documentation Improvements
- Added **"5-Minute Quick Start"** section to README with complete installation → demo → correction → export flow
- New **"Loading Your Own Data"** section with sensor-specific instructions for GelSight, PaXini, and Daimon
- Troubleshooting table for common import errors with direct `pip install` solutions
- Links to all three step-by-step tutorials from main README

#### Error Message Enhancements
- **FileNotFoundError**: Now suggests using absolute paths
- **ValueError** (unknown format): Lists all supported formats with sensor type descriptions:
  ```
  • .pkl / .pickle  — GelSight Mini, DIGIT (vision-based tactile sensors)
  • .h5 / .hdf5     — PaXini PXCap (distributed force array)
  • .parquet        — Daimon DM-TacClaw (multimodal robot)
  • Directory       — Daimon LeRobot format (with info.json + parquet + videos)
  ```
- **ImportError**: Provides exact `pip install` command for missing dependencies

### 🔧 Changed

#### Schema Updates
- Extended `manipulation_phase` enum values from 6 to 11 states:
  - Original: `idle`, `initial_contact`, `stable_contact`, `slip`, `release`, `re_contact`
  - Added: `approach`, `retract`, `grasp`, `transport`, `hold`
- Relaxed `schema_version` pattern from strict `^0\.2\.0$` to flexible `^0\.[0-9]+\.[0-9]+$` for future minor releases

#### Dependency Updates
- Added `scipy>=1.7` to `[daimon]` optional dependencies (required for signal processing)
- Added `scipy>=1.7` and `pillow>=9.0` to `[all]` meta-package
- Updated version from `0.2.0a7` (alpha) to `0.2.0b1` (beta) — indicating improved stability

#### Documentation Fixes
- Fixed docstrings in `tlabel/export/writer.py`, `tlabel/viewer/panel.py`, and `tlabel/adapters/base.py` to correctly reference "22 dimensions" instead of outdated "18 dimensions"

### 🐛 Fixed

- Resolved schema mismatch between JSON Schema definition and adapter outputs for `manipulation_phase`
- Corrected all remaining references to "18-dim" in code comments and docstrings
- Improved error messages to guide users toward solutions rather than just stating problems

### 📦 Build & Release

- Updated `pyproject.toml` version to `0.2.0b1`
- Updated `tlabel/_version.py` to `0.2.0b1`
- Built wheel (`tlabel-0.2.0b1-py3-none-any.whl`) and source distribution (`tlabel-0.2.0b1.tar.gz`)
- Published to PyPI via twine

### 🔄 Migration Notes

**For existing users:**
- No breaking changes — all existing code continues to work
- New fields (`sensor_id`, `calibration_params`, `feature_names`, `is_first`, `is_last`) are optional and default to sensible values
- If you're exporting to LeRobot or RLDS, use the new converter functions instead of manual CSV/JSON parsing

**For new users:**
- Start with the 5-Minute Quick Start in README
- Use sensor-specific tutorials for detailed guidance
- Try the interactive browser demo at https://liesliy.github.io/tlabel/demo.html

---

## [0.2.0a7] - Previous Release

### Added
- Initial TLabel Format v2 implementation with 22 dimensions
- Support for GelSight, DIGIT, PaXini, and Daimon sensors
- Interactive Jupyter panel with timeline, radar chart, and batch patching
- Cascade rules for physical consistency
- AI-assisted pre-annotation engine
- JSON and CSV export support

---

## Upcoming Features (Planned)

### High Priority
- Web-based annotation tool deployment (tlabel-web)
- Dark mode for interactive panel
- Additional language support (日本語, 한국어)
- Integration tests for edge cases

### Medium Priority
- SynTouch and XELA sensor adapters
- Batch processing pipeline for multiple episodes
- Annotation quality metrics and validation checks
- Export to TFRecord for TensorFlow pipelines

### Low Priority
- Real-time annotation during data collection
- Collaborative annotation features
- Annotation history and version control
- Plugin system for custom feature extractors

---

For more information, visit:
- [GitHub Repository](https://github.com/liesliy/tlabel)
- [PyPI Package](https://pypi.org/project/tlabel/)
- [Documentation](https://github.com/liesliy/tlabel/tree/main/docs)
