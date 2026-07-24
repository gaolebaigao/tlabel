# TLabel Annotation Specification

**Version:** 2.1.0  
**Schema:** V2 (14 dimensions)  
**Status:** Active  
**Last Updated:** 2026-07-24

---

## Overview

This document describes the TLabel Schema V2 annotation standard. It covers the 14 semantic dimensions, Compliance Levels (L1–L4), cascade rules, and the patch mechanism.

> Schema V2 replaces the legacy 22-dimension `tlabel_v2` format (removed in v0.17.0).

## Schema V2 Structure

```
┌──────────────────────────────────────────────┐
│  Required Fields                             │
│  contact · contact_centroid · slip_event     │
│  confidence · compliance_level               │
├──────────────────────────────────────────────┤
│  Force Fields (L2+)                          │
│  force_magnitude · force_vector · torque     │
├──────────────────────────────────────────────┤
│  Optional Fields                             │
│  contact_region · slip_velocity              │
│  manipulation_phase · texture_class          │
│  object_deformation · temperature            │
└──────────────────────────────────────────────┘
```

---

## Dimension Definitions

### 1. `contact` — bool · Required

Whether the sensor is in physical contact with an object.

**Vision-based sensors (GelSight, Daimon, VTouch):**
- Method: Pixel deviation from baseline (no-contact reference frame)
- Threshold: `mean(|diff_image|) > threshold`
- Output: `true` / `false`

**Force-array sensors (PaXini):**
- Method: Taxel activation count exceeds minimum
- Threshold: `sum(active_taxels) > min_taxels`
- Output: `true` / `false`

### 2. `contact_centroid` — [float × 2] · Required (if contact=true)

Center of mass of the contact region in normalized sensor coordinates [0, 1].

- X: `weighted_avg(col_index, weights=|diff|) / image_width`
- Y: `weighted_avg(row_index, weights=|diff|) / image_height`

### 3. `contact_region` — enum · Optional

Semantic label for which part of the sensor is in contact.

Values: `center` | `tip` | `side` | `edge` | `palm` | `finger` | `full_surface`

### 4. `force_magnitude` — float · Required (L2+)

Scalar measure of contact intensity.

**Vision-based sensors:**
- Computation: `sqrt(mean(R² + G² + B²))` of background-subtracted differential image
- Physical meaning: RMS of RGB pixel-level deformation intensity
- Unit: arbitrary_unit (pixel intensity, not calibrated Newtons)

**Force-array sensors:**
- Computation: `sum(active_taxel_values)`
- Unit: sensor-native (depends on calibration)

> ⚠️ For vision-based sensors, this is NOT calibrated force in Newtons. Use `sensor_profile.elastomer.modulus_pa` for calibration.

### 5. `force_vector` — [float × 3] · Optional (L3+)

3D contact force estimate [fx, fy, fz] in sensor frame.

**Vision-based sensors:**
- fx, fy: derived from shear field (channel-separated spatial gradients)
- fz: derived from normal deformation magnitude
- Requires elastomer calibration for physical units

### 6. `torque_vector` — [float × 3] · Optional

3D torque estimate [τx, τy, τz] in sensor frame.

- Computed from force_vector × contact_centroid offset
- Requires known sensor geometry

### 7. `slip_event` — bool · Required

Whether the contact is currently slipping.

**Vision-based sensors:**
- Computation: gradient angle variance of differential image
- `slip_event = true` if `var(gradient_angle) > threshold`
- High angular variance → multi-directional displacement → slip

**Force-array sensors:**
- Computation: temporal variance of taxel activation pattern

### 8. `slip_velocity` — [float × 2] · Optional (if slip_event=true)

Estimated slip direction and speed [vx, vy] in sensor coordinates.

- Vision-based: derived from Farneback optical flow between consecutive frames
- Unit: pixel/frame (or mm/s with calibration)

### 9. `manipulation_phase` — enum · Optional

Current manipulation state.

Values: `idle` | `approaching` | `initial_contact` | `stable_grasp` | `manipulating` | `slip` | `release`

### 10. `texture_class` — enum · Optional

Perceived surface texture category.

Values: `smooth` | `rough` | `ridged` | `granular` | `compliant` | `slippery` | `unknown`

### 11. `object_deformation` — float · Optional

Estimated deformation of the contacted object.

- Vision-based: peak deformation intensity `max(|gray|)` of differential image
- Unit: arbitrary_unit

### 12. `temperature` — float · Optional

Surface temperature at contact point (requires thermal sensor).

- Unit: °C
- Only available for sensors with thermal capability

### 13. `confidence` — float · Required

Annotation confidence score [0.0, 1.0].

- 1.0: high confidence (strong signal, clear contact)
- 0.5: moderate (weak signal, ambiguous)
- 0.0: no confidence / not annotated

### 14. `compliance_level` — enum · Required

Schema compliance level of this frame.

| Level | Meaning | Required Fields |
|-------|---------|-----------------|
| **L1** | Minimal | contact + slip_event + confidence |
| **L2** | Force-aware | L1 + force_magnitude |
| **L3** | Full wrench | L2 + force_vector |
| **L4** | Complete | L3 + all optional fields populated |

---

## Compliance Level Assignment

Each adapter declares a `default_compliance_level` based on its sensor capabilities:

| Sensor | Default Level | Reason |
|--------|:---:|--------|
| GelSight / DIGIT | L3 | Vision → full 3D force estimation |
| Daimon DM-TacClaw | L3 | Multimodal → force_vector available |
| PaXini PXCap | L2 | Force array → magnitude only, no 3D vector |
| VTouch | L3 | Vision-based |
| UniVTAC | L3 | Vision-based |
| TacQuad | L3 | Multi-sensor vision |
| YCB-Slide | L3 | Vision-based |
| PaXini GEN3 (real-time) | L2 | Force array, real-time |
| Daimon DM-Tac (real-time) | L3 | Vision-based |

---

## Cascade Rules

When a user modifies a field via the `patch()` method, the system enforces physical consistency:

### Rule 1: Contact Release → Zero Everything

When `contact` is set to `false`:
- Reset: `force_magnitude` → 0, `force_vector` → [0,0,0], `slip_event` → false
- Set `manipulation_phase` → `release` (if was contact-related)
- Set `compliance_level` → `L1` (force fields no longer valid)

### Rule 2: Slip Requires Contact

When `slip_event` is set to `true` but `contact` is `false`:
- Set `contact` → `true` (slip implies contact)
- If `manipulation_phase` was `idle`, upgrade to `slip`

### Rule 3: Force Requires Contact

When `force_magnitude` is set > 0 but `contact` is `false`:
- Set `contact` → `true` (force implies contact)

### Rule 4: Compliance Level Auto-Update

When fields are modified, `compliance_level` is recalculated:
- Only `contact` + `slip_event` + `confidence` → L1
- + `force_magnitude` > 0 → L2
- + `force_vector` not all-zero → L3
- + any optional field populated → L4

---

## Patch Mechanism

Each frame tracks its modification history in a `patches` list:

```python
frame.patch("contact", True, cascade=True)
# Returns:
# {
#     "field": "contact",
#     "old_value": False,
#     "new_value": True,
#     "cascade": [
#         {"field": "manipulation_phase", "old_value": "idle", "new_value": "initial_contact"},
#         {"field": "compliance_level", "old_value": "L1", "new_value": "L1"}
#     ]
# }
```

Patches are serialized to JSON for full audit trail — every correction is traceable.

---

## Calibration Dependencies

Most force-related values from vision-based sensors are in **pixel space** (arbitrary_unit), not SI units. Cross-sensor comparisons require calibration.

The `sensor_profile.elastomer` field provides physical parameters:
- `modulus_pa`: Young's modulus → enables deformation→force conversion
- `thickness_mm`: Elastomer thickness → affects force-deformation relationship
- `friction_coefficient`: Enables friction cone interpretation

See the [Schema JSON](../schema/tlabel-schema.json) for the complete field definitions.
