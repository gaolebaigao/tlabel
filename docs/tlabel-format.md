# TLabel Format Specification

> ⚠️ **DEPRECATED — This document describes the legacy v0.8.0 format (22-dim tlabel_v2).**
> 
> **Current version: TLabel Schema V2 (14-dim)** — see [`docs/annotation-spec.md`](annotation-spec.md) for the up-to-date specification.
> 
> This document is kept as a historical reference only. New projects should use Schema V2.
> 
> **Key changes in Schema V2 (v0.17+):**
> - 22 dimensions → 14 dimensions
> - `format: tlabel_v2` → `format: tlabel_schema_v2`
> - New fields: `compliance_level`, `contact_centroid`, `force_vector`, `torque_vector`, `slip_velocity`, `temperature`
> - Removed fields: `deformation_magnitude`, `force_peak`, `force_direction`, `slip_entropy`, `texture_energy`, `edge_density`, `contact_area`, `normal_field_*`, `shear_field_*`, `delta_force_*`, `friction_cone_ratio`, `optical_flow_*`, `temporal_deformation_rate`, `contact_transition`
> - Migration guide: `MIGRATION.md` in the tlabel repository

---

## Legacy Document (v0.8.0)

---

## Overview

TLabel Format is a **sensor-agnostic tactile annotation schema** designed to unify the output of diverse tactile sensors into a common representation. Rather than forcing all sensors into a single raw-data format, TLabel operates at the **annotation level**: each sensor adapter declares which semantic dimensions it can annotate, producing compatible but heterogeneous output.

### Design Principles

1. **Capability Declaration**: Each adapter explicitly declares which dimensions it supports. Unsupported dimensions are omitted — never fabricated.
2. **Semantic-Level Unification**: TLabel unifies at the annotation level (contact, slip, deformation), not at the raw signal level.
3. **Schema-Versioned**: All files carry a `schema_version` field, enabling backward-compatible evolution.
4. **Pixel-Space Honesty**: Features are computed in pixel space. Names that imply force (e.g. `force_magnitude`) are being deprecated in favor of honest names (e.g. `deformation_magnitude`). Calibration via `sensor_profile` bridges the gap to physical units.

---

## Top-Level Structure

```json
{
  "schema_version": "0.8.0",
  "format": "tlabel_v2",
  "tlabel_dimensions": 22,
  "feature_names": ["contact", "deformation_magnitude", ...],
  "feature_metadata": { ... },
  "sensor": { ... },
  "sensor_id": "left_gripper",
  "sensor_profile": { ... },
  "calibration": { ... },
  "episode": { ... },
  "capabilities": { ... },
  "frames": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | ✅ | Semver format `X.Y.Z` |
| `format` | string | ✅ | Always `"tlabel_v2"` |
| `tlabel_dimensions` | int | ✅ | Number of annotation dimensions (currently 22) |
| `feature_names` | string[] | ✅ | Ordered list of all 22 dimension keys |
| `feature_metadata` | object | ✅ | Per-feature metadata (computation, semantics, units) — see §Feature Metadata |
| `sensor` | object | ✅ | Sensor identification — see §Sensor Info |
| `sensor_id` | string | ❌ | Instance identifier (e.g. `"left_gripper"`, `"finger_2"`) |
| `sensor_profile` | object | ❌ | Physical properties for calibration — see §Sensor Profile |
| `calibration` | object | ❌ | Force-deformation calibration parameters |
| `episode` | object | ✅ | Episode-level metadata — see §Episode Info |
| `capabilities` | object | ✅ | Dimension support declaration — see §Capabilities |
| `frames` | array | ✅ | Array of frame annotations — see §Frame Structure |

---

## Sensor Info

Identifies the sensor hardware and the adapter that processed the data.

```json
{
  "sensor": {
    "sensor_name": "GelSight Mini",
    "sensor_type": "vision_based",
    "manufacturer": "GelSight Inc.",
    "model": "Mini",
    "resolution": "320x240",
    "frame_rate": 30,
    "adapter_name": "gelsight",
    "adapter_version": "0.8.0"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sensor_name` | string | ✅ | Product name |
| `sensor_type` | string | ✅ | One of: `"vision_based"`, `"distributed_array"`, `"hybrid"` |
| `manufacturer` | string | ❌ | Manufacturer name |
| `model` | string | ❌ | Model identifier |
| `resolution` | string | ❌ | Sensor resolution |
| `frame_rate` | number | ❌ | Frames per second |
| `adapter_name` | string | ✅ | TLabel adapter identifier |
| `adapter_version` | string | ✅ | Adapter version (semver) |

---

## Sensor Profile (v0.7+)

Physical properties of the sensor's elastomer and optical system. Enables cross-sensor comparability and unit calibration. **All fields are optional** — `null` is valid.

```json
{
  "sensor_profile": {
    "sensor_type": "gelsight_mini",
    "manufacturer": "GelSight Inc.",
    "model": "Mini",
    "elastomer": {
      "material": "dragon_skin_10",
      "modulus_pa": 690000,
      "thickness_mm": 3.0,
      "friction_coefficient": 0.5,
      "source": "manufacturer_spec"
    },
    "optical": {
      "light_source": "led_ring",
      "led_wavelength_nm": 470
    },
    "calibration": {
      "method": "literature",
      "reference_doi": "10.1109/LRA.2020.3045678",
      "pixel_to_force_coefficient": 0.0012,
      "pixel_to_force_unit": "N/pixel"
    },
    "notes": "Calibration from Wu et al. 2021"
  }
}
```

### Elastomer Properties

| Field | Type | Description |
|-------|------|-------------|
| `material` | string | Material name (e.g. `"dragon_skin_10"`, `"eco_flex_00-30"`) |
| `modulus_pa` | number | Young's modulus in Pascals — critical for deformation→force conversion |
| `thickness_mm` | number | Elastomer thickness in mm |
| `friction_coefficient` | number | Coefficient of friction |
| `source` | string | Provenance: literature DOI, `"self_calibrated"`, `"manufacturer_spec"`, `"unknown"` |

### Calibration Parameters

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | `"literature"`, `"self_calibrated"`, `"manufacturer_spec"`, `"none"` |
| `reference_doi` | string | DOI of calibration reference |
| `pixel_to_force_coefficient` | number | Linear conversion coefficient |
| `pixel_to_force_unit` | string | Unit of conversion (default: `"N/pixel"`) |

---

## The 22 Annotation Dimensions

### Category 1: Deformation (IDs 1-5)

| # | Key | Unit | Calib? | Computation |
|---|-----|------|--------|-------------|
| 1 | `contact` | dimensionless | No | Binary: 1.0 if contact detected, else 0.0 |
| 2 | `deformation_magnitude` | arbitrary_unit | Yes | `sqrt(mean(R² + G² + B²))` of background-subtracted differential image |
| 3 | `force_magnitude` | arbitrary_unit | Yes | **DEPRECATED (v0.7)** — alias of `deformation_magnitude`. Use `deformation_magnitude_peak` |
| 4 | `force_peak` | arbitrary_unit | Yes | `max(|gray|)` where gray = mean(R,G,B) of differential |
| 5 | `force_direction` | degree | Yes | `arctan2(weighted_mean_gy, weighted_mean_gx)` intensity-weighted gradient direction |

### Category 2: Gradient (IDs 6-9)

| # | Key | Unit | Calib? | Computation |
|---|-----|------|--------|-------------|
| 6 | `slip_entropy` | dimensionless | No | Shannon entropy of grayscale deformation distribution (32 bins) |
| 7 | `slip_event` | dimensionless | No | `min(var(gradient_angle)/100, 1.0)` — angular variance heuristic |
| 8 | `texture_energy` | arbitrary_unit | No | `mean(gray²)` of differential image |
| 9 | `edge_density` | dimensionless | No | Fraction of pixels with gradient above 90th percentile |

### Category 3: Force Semantic (IDs 10-18)

| # | Key | Unit | Calib? | Computation |
|---|-----|------|--------|-------------|
| 10 | `contact_area` | dimensionless | Yes | `mean(|gray| > 2·std(gray))` — fraction above 2σ threshold |
| 11 | `centroid_x` | dimensionless | No | Column-wise center of mass of deformation, normalized [0,1] |
| 12 | `normal_field_magnitude` | arbitrary_unit | Yes | RMS of RGB differential (pixel-space, not actual force) |
| 13 | `normal_field_variance` | arbitrary_unit | No | `var(‖∇gray‖)` — spatial variance of gradient magnitude |
| 14 | `shear_field_magnitude` | arbitrary_unit | Yes | `sqrt(mean(|R_gx|)² + mean(|G_gy|)²)` from channel-separated gradients |
| 15 | `shear_field_direction` | degree | Yes | `arctan2(mean(|G_gy|), mean(|R_gx|))` in image coordinates |
| 16 | `delta_force_normal` | arbitrary_unit | Yes | Frame-to-frame Δ in `normal_field_magnitude` |
| 17 | `delta_force_shear` | arbitrary_unit | Yes | Frame-to-frame Δ in `shear_field_magnitude` |
| 18 | `friction_cone_ratio` | dimensionless | Yes | `shear_magnitude / normal_magnitude` (clamped max 10.0) |

### Category 4: Temporal (IDs 19-22)

| # | Key | Unit | Calib? | Computation |
|---|-----|------|--------|-------------|
| 19 | `optical_flow_magnitude` | pixel/frame | No | `mean(magnitude)` of Farneback dense optical flow |
| 20 | `optical_flow_direction` | degree | No | `mean(angle)` of Farneback dense optical flow |
| 21 | `temporal_deformation_rate` | arbitrary_unit/s | Yes | `|deformation_t - deformation_{t-1}| / dt` |
| 22 | `contact_transition` | dimensionless | No | `min(1.0, |contact_t - contact_{t-1}| + |Δcontact_area|·5)` |

### Replacement Dimension

| # | Key | Unit | Calib? | Computation |
|---|-----|------|--------|-------------|
| 3' | `deformation_magnitude_peak` | arbitrary_unit | Yes | Same as `deformation_magnitude`, transparently named |

---

## Frame Structure

```json
{
  "frame_idx": 0,
  "timestamp_s": 0.0,
  "is_first": true,
  "is_last": false,
  "tlabel_v2": {
    "contact": 1.0,
    "deformation_magnitude": 0.234,
    "...(all 22 dimensions)...": 0.0
  },
  "manipulation_phase": "stable_contact",
  "confidence": 0.95,
  "sensor_specific": {},
  "patches": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `frame_idx` | int | ✅ | Original frame number from source data |
| `timestamp_s` | float | ✅ | Timestamp in seconds |
| `is_first` | bool | ✅ | True if first frame in episode |
| `is_last` | bool | ✅ | True if last frame in episode |
| `tlabel_v2` | object | ✅ | The 22-dimension annotation values |
| `manipulation_phase` | string | ✅ | Phase label — see valid values below |
| `confidence` | float | ✅ | Annotation confidence [0, 1] |
| `sensor_specific` | object | ❌ | Sensor-specific raw data (if preserved) |
| `patches` | array | ❌ | Modification history — see §Patch & Cascade |

### Valid Manipulation Phases

| Phase | Description |
|-------|-------------|
| `idle` | No contact |
| `initial_contact` | First contact detected |
| `stable_contact` | Sustained contact |
| `slip` | Slip event in progress |
| `release` | Contact releasing |
| `re_contact` | Re-contact after release |
| `approach` | Approaching object |
| `retract` | Withdrawing from object |
| `grasp` | Active grasping |
| `transport` | Moving object |
| `hold` | Maintaining grip |

---

## Episode Info

```json
{
  "episode": {
    "episode_id": "ep_001",
    "task": "grasp_cube",
    "object": "wooden_cube_5cm",
    "num_frames": 150,
    "duration_s": 5.0,
    "stats": {
      "contact_frames": 120,
      "contact_ratio": 0.8,
      "slip_frames": 5,
      "slip_ratio": 0.033,
      "modified_frames": 0
    },
    "episode_label": {
      "outcome": "success",
      "manipulation_type": "grasp",
      "difficulty": "medium"
    }
  }
}
```

### Episode Label (v0.4+)

| Field | Valid Values | Description |
|-------|-------------|-------------|
| `outcome` | `success` / `partial` / `failure` / `inconclusive` | Task result |
| `manipulation_type` | `grasp` / `pinch` / `poke` / `slide` / `push` / `pull` / `tap` / `lift` / `place` / `other` | Manipulation type |
| `difficulty` | `easy` / `medium` / `hard` | Task difficulty |

---

## Capabilities

```json
{
  "capabilities": {
    "contact": true,
    "contact_region": false,
    "force_magnitude": true,
    "deformation_magnitude_peak": true,
    "force_direction": true,
    "slip_event": true,
    "slip_direction": false,
    "manipulation_phase": true,
    "texture": false,
    "whole_hand_coordination": false,
    "object_deformation": false
  }
}
```

`contact` is **required** (must be `true`). All other capabilities are optional.

---

## Patch & Cascade System (v0.3+)

### Patch Record

```json
{
  "field": "contact",
  "old_value": 0.0,
  "new_value": 1.0,
  "cascade": [
    {"field": "force_magnitude", "old_value": 0.0, "new_value": 0.15},
    {"field": "manipulation_phase", "old_value": "idle", "new_value": "initial_contact"}
  ]
}
```

### Cascade Rules

| Trigger | Condition | Cascade Actions |
|---------|-----------|-----------------|
| `contact` → 0 | Contact released | Zero: `force_magnitude`, `force_peak`, `slip_event`, `delta_force_normal`, `delta_force_shear`, `contact_area`, `contact_transition`; phase → `idle` |
| `slip_event` > 0.5 + no contact | Slip without contact | Set `contact` → 1.0; if phase = `idle`, upgrade to `slip` |
| `force_magnitude` > 0 + no contact | Force without contact | Set `contact` → 1.0 |

---

## Export Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| JSON | `.json` | Human-readable, full metadata |
| CSV | `.csv` | pandas/R analysis, flat table |
| HDF5 | `.h5` / `.hdf5` | Scientific computing, large datasets |
| FTP-1 Zarr | `.zarr` | FTP-1 foundation model fine-tuning |
| LeRobot | directory | HuggingFace LeRobot ecosystem |

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.8.0 | 2026-06-28 | FTP-1/MTTS Zarr export; 21 functional areas; 7 sensor registry |
| 0.7.0 | 2026-06-23 | `sensor_profile` + `feature_metadata`; `force_magnitude` deprecated → `deformation_magnitude_peak` |
| 0.6.0 | 2026-06-18 | Unit standardization; physical quantity semantics |
| 0.5.0 | 2026-06-10 | AI pre-annotation engine; HMM phase detection; temporal post-processing |
| 0.4.0 | 2026-06-05 | Interactive Panel UI; Episode labels; Quality scoring; Batch processing |
| 0.3.0 | 2026-06-01 | Patch & cascade system; batch correction |
| 0.2.0 | 2026-05-27 | Initial format specification; capability declaration system |
