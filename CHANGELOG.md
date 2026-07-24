# Changelog

All notable changes to TLabel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.17.1] - 2026-07-24

### 🐛 Bug Fixes

- **Panel rendering**: Fixed `TypeError: tv2.contact.toFixed is not a function` — `contact`/`slip_event` are booleans in Schema V2, not floats. JS template now displays ✅/—.
- **Panel null safety**: Added null guards for `force_magnitude` and optional fields.
- **Panel keyboard shortcuts**: Space/S key toggles now handle boolean values correctly.
- **Schema JSON**: Removed invalid `enum` constraint on `feature_names_v2` array.
- **HTML template**: Removed unnecessary `<!DOCTYPE html>` in Jupyter iframe.

### 🔧 Test Fixes

- Migrated all 6 test files from `tlabel_v2=` to `schema_v2=TLabelSchemaV2(...)` API.
- All **147 tests passing**.

---

## [0.17.0] - 2026-07-24

### ⚠️ Breaking Change — Schema V2 Only

Complete migration to **14-dim Schema V2** with **Compliance Levels (L1–L4)**. All legacy `tlabel_v2` (22-dim) compatibility code removed.

### Added
- `TLabelSchemaV2` dataclass — 14-dim structured tactile annotation with Compliance Level
- `DataAdapterBase.extract_schema()` / `SensorAdapterBase.extract_schema()` — standard interface
- `schema/tlabel-schema.json` v2.1.0 — JSON Schema specification
- `MIGRATION.md` — migration guide from v0.16 to v0.17

### Changed
- Three-layer architecture: Schema → Adapters → Downstream
- All 10 adapters migrated to `TLabelFrame(schema_v2=TLabelSchemaV2(...))`
- `PredictEngine` fully rewritten for Schema V2
- Quality scorer based on 14-dim Schema + Compliance Level
- Viewer panel radar chart updated to 14 dimensions
- CSV export: 14 columns (V2 expanded)

### Removed
- `TLabelFrame.tlabel_v2` property (legacy 22-dim format)
- All `_detect_schema_version()` auto-detection logic
- Legacy 22-column CSV export mode

---

## [0.16.0] - 2026-07-22

### 🎉 Open Platform Architecture

- **Dual-base adapter architecture**: `DataAdapterBase` (datasets) + `SensorAdapterBase` (live sensors)
- **Community contribution kit**: adapter templates, PR templates, CONTRIBUTING.md
- **CLI tools**: `tlabel validate`, `tlabel list`, `tlabel info`, `tlabel version`
- **External adapter registration** via `entry_points` auto-discovery
- **Data augmentation**: 5 methods (time_warp, noise_inject, crop, scale, dropout)
- **AI Pre-Annotation**: `PredictEngine` with HMM temporal smoothing

---

## [0.15.x] and earlier

Early development releases. See [GitHub releases](https://github.com/liesliy/tlabel/releases) for details.
