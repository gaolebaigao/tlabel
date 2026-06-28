# TLabel Annotation Specification

**Version:** 0.8.0  
**Status:** Active  
**Last Updated:** 2026-06-28

---

## Overview

This document describes the annotation methodology used by TLabel adapters. It covers the general approach for each semantic dimension, cascade rules, and the patch mechanism.

## General Annotation Flow

```
Raw Sensor Data → Preprocessing → Dimension-wise Annotation → Cascade Rules → TLabelData Output
```

1. **Preprocessing**: Each adapter applies sensor-specific normalization (e.g., baseline subtraction for vision-based sensors, calibration for force arrays)
2. **Dimension-wise Annotation**: Each supported dimension is annotated independently using the methods described below
3. **Cascade Rules**: Physical consistency constraints are enforced across dimensions
4. **Capability Filtering**: Only dimensions declared in `capabilities` are included in the output

---

## Annotation Methods by Dimension

### 1. Contact Detection

**Vision-based sensors (GelSight, Daimon, PaXini):**
- Method: Pixel deviation from baseline (no-contact reference frame)
- Computation: `contact = 1.0 if mean(|diff_image|) > threshold else 0.0`
- Output: Binary per frame (0.0 or 1.0)

**Array-based sensors (ToucHD, VTouch):**
- Method: Threshold on taxel activation count
- Computation: `contact = 1.0 if sum(active_taxels) > min_taxels else 0.0`
- Output: Binary per frame

### 2. Deformation Magnitude

**Vision-based sensors:**
- Computation: `sqrt(mean(R² + G² + B²))` of background-subtracted differential image
- Physical meaning: RMS of RGB pixel-level deformation intensity
- Unit: arbitrary_unit (pixel intensity, not force)
- Note: Despite its name, `force_magnitude` (deprecated) is identical to this value

### 3. Force Magnitude (DEPRECATED)

- Since v0.7.0: Deprecated. Use `deformation_magnitude_peak` instead.
- Reason: The name "force_magnitude" implies a calibrated force measurement in Newtons, but the value has NOT undergone force-deformation calibration.
- Migration: The value is identical to `deformation_magnitude` — just rename.

### 4. Force Peak

**Vision-based sensors:**
- Computation: `max(|gray|)` where `gray = mean(R, G, B)` of differential image
- Physical meaning: Peak single-pixel deformation intensity
- Unit: arbitrary_unit

### 5. Force Direction

**Vision-based sensors:**
- Computation: `arctan2(weighted_mean_gy, weighted_mean_gx)` where weights = `|gray|`, gx/gy = spatial gradient of grayscale differential
- Physical meaning: Intensity-weighted dominant direction of surface displacement in image coordinates
- Unit: degree (0-360)
- Note: NOT in world coordinates without extrinsic calibration

### 6. Slip Entropy

**Vision-based sensors:**
- Computation: `-sum(p * log(p))` where `p = histogram(grayscale_diff, bins=32, density=True) + 1e-10`
- Physical meaning: Shannon entropy of the grayscale deformation distribution
- Higher entropy → more complex/distributed contact patterns
- Unit: dimensionless (nats)

### 7. Slip Event

**Vision-based sensors:**
- Computation: `min(var(gradient_angle) / 100, 1.0)` where `gradient_angle = arctan2(gy, gx)` of grayscale differential
- Physical meaning: Variance of gradient angles — high angular variance suggests multi-directional displacement consistent with slip
- Unit: dimensionless [0, 1]
- Note: This is a pixel-space heuristic, not a calibrated slip detector

### 8. Texture Energy

**Vision-based sensors:**
- Computation: `mean(gray²)` where `gray = mean(R, G, B)` of differential image
- Physical meaning: Mean squared intensity — related to deformation magnitude (squared), not surface texture per se
- Unit: arbitrary_unit

### 9. Edge Density

**Vision-based sensors:**
- Computation: `mean(|gradient(gray)| > percentile_90)`
- Physical meaning: Fraction of pixels with sharp deformation edges
- Unit: dimensionless [0, 1]

### 10. Contact Area

**Vision-based sensors:**
- Computation: `mean(|gray| > 2 * std(gray))`
- Physical meaning: Fraction of pixels exceeding 2σ — approximates contact region in pixel space
- Unit: dimensionless [0, 1]
- Note: Proportional to physical contact area when sensor geometry is known

### 11. Centroid X

**Vision-based sensors:**
- Computation: `weighted_avg(col_index, weights=col_sums(|gray|)) / image_width`
- Physical meaning: Lateral position of the contact centroid
- Unit: dimensionless [0, 1]

### 12. Normal Field Magnitude

**Vision-based sensors:**
- Computation: `sqrt(mean(R² + G² + B²))` of contact differential image
- Physical meaning: Despite the name, this is RMS of the RGB differential — not an actual normal force measurement
- Unit: arbitrary_unit

### 13. Normal Field Variance

**Vision-based sensors:**
- Computation: `var(sqrt(gx² + gy²))` where gx, gy = gradient of mean(R,G,B) differential
- Physical meaning: Non-uniformity of the deformation field
- Unit: arbitrary_unit

### 14. Shear Field Magnitude

**Vision-based sensors:**
- Computation: `sqrt(mean(|R_gx|)² + mean(|G_gy|)²)` where R_gx = spatial gradient of R channel (x-direction), G_gy = spatial gradient of G channel (y-direction)
- Physical meaning: Shear deformation estimated from channel-separated spatial gradients
- Unit: arbitrary_unit

### 15. Shear Field Direction

**Vision-based sensors:**
- Computation: `arctan2(mean(|G_gy|), mean(|R_gx|))` in degrees
- Physical meaning: Direction of shear deformation in image coordinates
- Unit: degree (0-360)

### 16. Delta Force Normal

**Vision-based sensors:**
- Computation: `|normal_field_t - normal_field_{t-1}|` — frame-to-frame change in normal deformation
- Physical meaning: Rate of change of normal deformation
- Unit: arbitrary_unit

### 17. Delta Force Shear

**Vision-based sensors:**
- Computation: `|shear_field_t - shear_field_{t-1}|` — frame-to-frame change in shear deformation
- Physical meaning: Rate of change of shear deformation
- Unit: arbitrary_unit

### 18. Friction Cone Ratio

**Vision-based sensors:**
- Computation: `shear_field_magnitude / normal_field_magnitude` (clamped to max 10.0)
- Physical meaning: Analogous to friction cone concept (τ/σ < μ for no-slip), but computed from uncalibrated pixel values
- Unit: dimensionless

### 19. Optical Flow Magnitude

**Vision-based sensors (requires OpenCV):**
- Computation: `mean(magnitude)` of Farneback dense optical flow between consecutive frames
- Physical meaning: Average pixel displacement between frames
- Unit: pixel/frame

### 20. Optical Flow Direction

**Vision-based sensors (requires OpenCV):**
- Computation: `mean(angle)` of Farneback dense optical flow
- Physical meaning: Dominant motion direction in image coordinates
- Unit: degree (0-360)

### 21. Temporal Deformation Rate

- Computation: `|deformation_magnitude_t - deformation_magnitude_{t-1}| / dt`
- Physical meaning: How quickly contact intensity is changing
- Unit: arbitrary_unit/s

### 22. Contact Transition

- Computation: `min(1.0, |contact_t - contact_{t-1}| + |Δcontact_area| * 5.0)`
- Physical meaning: Contact state transition intensity — values near 1.0 indicate contact onset or release
- Unit: dimensionless [0, 1]

---

## Cascade Rules (v0.3+)

When a user modifies a field via the `patch()` method, the system enforces physical consistency:

### Rule 1: Contact Release → Zero Everything

When `contact` is set to 0:
- Zero out: `force_magnitude`, `force_peak`, `slip_event`, `delta_force_normal`, `delta_force_shear`, `contact_area`, `contact_transition`
- Exception: `contact_transition` is only zeroed if its value > 0.5
- Set `manipulation_phase` → `idle` (if it was in a contact-related phase)

### Rule 2: Slip Requires Contact

When `slip_event` is set > 0.5 but `contact` < 0.5:
- Set `contact` → 1.0 (slip implies contact)
- If `manipulation_phase` was `idle`, upgrade to `slip`

### Rule 3: Force Requires Contact

When `force_magnitude` is set > 0 but `contact` < 0.5:
- Set `contact` → 1.0 (force implies contact)

---

## Patch Mechanism

Each frame tracks its modification history in a `patches` list:

```python
frame.patch("contact", 1.0, cascade=True)
# Returns:
# {
#     "field": "contact",
#     "old_value": 0.0,
#     "new_value": 1.0,
#     "cascade": [
#         {"field": "manipulation_phase", "old_value": "idle", "new_value": "initial_contact"}
#     ]
# }
```

Patches are serialized to JSON for full audit trail — every correction is traceable.

---

## Adapter-Specific Notes

### Vision-Based Adapters (GelSight, Daimon, PaXini)

All vision-based adapters follow the same pipeline:
1. Load raw image frames (pkl, h5, or directory of images)
2. Compute background-subtracted differential image against first frame (or provided baseline)
3. Extract 22 dimensions from differential image
4. Declare capabilities based on sensor type

### Array-Based Adapters (ToucHD)

- Input: Taxel activation matrix
- Different computation path: direct from taxel values rather than image processing
- Capabilities may differ (e.g., no `optical_flow_*` dimensions)

### Event-Based Adapters (VTouch)

- Input: Event stream (timestamp, taxel, polarity)
- Requires binning into fixed time windows before annotation
- May produce sparse annotations (many frames with zero values)

---

## Calibration Dependencies

13 of the 22 dimensions require calibration to produce physically meaningful values. Without calibration:
- Values are in **pixel space** (arbitrary_unit), not SI units
- Cross-sensor comparisons are unreliable
- Force-related names (e.g., "normal_field_magnitude") are misleading

The `sensor_profile.elastomer` field provides the physical parameters needed for calibration:
- `modulus_pa`: Young's modulus → enables deformation→force conversion
- `thickness_mm`: Elastomer thickness → affects force-deformation relationship
- `friction_coefficient`: Enables friction cone interpretation

See the [Format Specification](tlabel-format.md) for the full `sensor_profile` schema.
