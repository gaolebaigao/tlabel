# Changelog

All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.0] - 2026-06-21

### 🎉 Major Highlights

This release introduces **AI-Assisted Pre-Annotation** with a redesigned `PredictEngine` — predict contact, slip, and manipulation phase automatically, then review and correct in the interactive Panel. Human-in-the-loop, not black-box.

### ✨ Added

#### AI Pre-Annotation (PredictEngine Redesign)
- `PredictEngine` with rule-based + HMM prediction for contact, slip, and manipulation phase
- **HMM Phase Detection**: Hidden Markov Model with Viterbi decoding for manipulation phase inference
- **Warm start with `fit()`**: learn from partially labeled data — even 10–20% labels significantly boost accuracy
- **Confidence-based filtering**: `apply(data, results, min_confidence=0.7)` — only apply high-confidence predictions
- `engine.summary(results)` — prediction statistics overview
- `engine.fit(data)` → `engine.predict(data)` workflow for semi-supervised annotation

#### Panel Integration
- Pre-annotation results viewable and correctable directly in the Panel
- AI predictions shown with confidence indicators

### 🔧 Changed

- **Removed black-box pkl models**: deleted opaque pretrained weights with no training data source or documentation. Every prediction is now interpretable — rules + HMM, no hidden parameters
- `PredictEngine` API streamlined: `predict()` → `apply()` → `review()` three-step workflow
- Time-series post-processing for smoother phase predictions

### 🐛 Fixed

- Phase prediction discontinuity: HMM Viterbi decoding eliminates erratic frame-to-frame phase switches
- Confidence calibration: rule-based predictions now report calibrated confidence ranges

---

## [0.4.2] - 2026-06-20

### 🎉 Major Highlights

**Full internationalization (i18n)** — the Panel UI, error messages, and documentation now support both Chinese and English seamlessly.

### ✨ Added

- Complete bilingual Panel UI: toggle between 中文/English with one click
- Localized error messages and installation hints for all sensor adapters
- English documentation for all sensor tutorials
- Panel language state persists within session

### 🔧 Changed

- `review(lang="en")` / `review(lang="zh")` for explicit language selection
- Default Panel language follows system locale, falls back to Chinese

---

## [0.4.1] - 2026-06-20

### 🎉 Major Highlights

**Panel UI integration** — bringing annotation, correction, and export into one cohesive interactive experience.

### ✨ Added

- Tab navigation in Panel: Overview / Annotation / Correction tabs
- Batch correction tool integrated in Panel: select frame range → set values → apply
- Export buttons directly in Panel (JSON / CSV)
- In-panel batch operations with visual feedback

### 🔧 Changed

- Panel layout reorganized for clearer workflow: view → annotate → correct → export
- Improved frame detail display with editable fields

---

## [0.4.0] - 2026-06-20

### 🎉 Major Highlights

**Interactive Visual Panel** — the first Jupyter-native annotation interface for tactile data. See your data, don't just read numbers.

### ✨ Added

- Color-coded timeline: green = contact · red = slip · gray = idle — patterns jump out instantly
- 22-dim radar chart: full feature vector at a glance, bilingual labels
- Frame detail editor: inspect and edit individual frame values
- `_repr_html_()` for automatic Jupyter rendering
- `data.review()` entry point for explicit Panel launch

### 🔧 Changed

- `TLabelData` now renders as interactive Panel in Jupyter (was plain text repr)
- Template engine for Panel HTML+JS+CSS generation

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
- Added `sensor_id` and `calibration_params` fields to `TLabelData.__init__()` for downstream traceability
- Added `feature_names` list to `TLabelData` — all 22 dimension keys in order
- Episode boundary markers: `is_first` and `is_last` boolean flags on `TLabelFrame`

#### LeRobot Integration
- Bidirectional converters: `tlabel.adapters.lerobot.TLabelLeRobotConverter`
  - `to_lerobot(data, output_dir)` — export TLabel data to LeRobot format (parquet + metadata)
  - `from_lerobot(data_dir)` — load LeRobot format data into TLabelData
- Supports Daimon DM-TacClaw LeRobot datasets out of the box

#### HDF5 Export
- `data.export("output.hdf5")` — scientific computing standard format
- Compatible with MATLAB, SciPy, and h5py workflows
- Stores all 22 dimensions + metadata as HDF5 datasets and attributes

#### Documentation & Tutorials
- Comprehensive sensor tutorials:
  - `docs/tutorial-gelsight.md` — GelSight Mini / DIGIT step-by-step guide
  - `docs/tutorial-paxini.md` — PaXini PXCap step-by-step guide
  - `docs/tutorial-daimon.md` — Daimon DM-TacClaw step-by-step guide
- 5-Minute Quick Start section in README
- Troubleshooting table for common errors

#### Error Messages
- Clear `ImportError` messages with exact `pip install` commands
- Format detection errors now show supported formats and file extensions
- Missing file errors suggest checking paths and using absolute paths

### 🔧 Changed

- `TLabelFrame` now includes `is_first` and `is_last` properties
- Export format auto-detected by file extension (.json, .csv, .hdf5)
- README reorganized with Quick Start first, details later

### 🐛 Fixed

- HDF5 export handles numpy types correctly (NumpyEncoder)
- LeRobot converter handles missing optional fields gracefully
- Format detection more robust for edge-case filenames
