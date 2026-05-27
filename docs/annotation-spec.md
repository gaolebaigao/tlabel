# TLabel Annotation Specification

**Version:** 0.2.0  
**Status:** Draft  
**Last Updated:** 2026-05-27

---

## Overview

This document describes the annotation methodology used by TLabel adapters. It covers the general approach for each semantic dimension, but does **not** include sensor-specific thresholds or parameters — those are internal to each adapter implementation.

## General Annotation Flow

```
Raw Sensor Data → Preprocessing → Dimension-wise Annotation → TLabel JSON Output
```

1. **Preprocessing**: Each adapter applies sensor-specific normalization (e.g., baseline subtraction for vision-based, calibration for force arrays)
2. **Dimension-wise Annotation**: Each supported dimension is annotated independently using the methods described below
3. **Capability Filtering**: Only dimensions declared in `capabilities` are included in the output

## Annotation Methods by Dimension

### Contact Detection

**Vision-based sensors:**
- Method: Pixel deviation from baseline (no-contact reference frame)
- Output: Boolean per frame

**Distributed array sensors:**
- Method: Force threshold on individual taxels
- Output: Boolean per frame

### Contact Region

**Vision-based sensors:**
- Method: Connected component analysis on contact mask
- Output: Region label (sensor-specific vocabulary)

**Distributed array sensors:**
- Method: Taxel group identification based on spatial mapping
- Output: Region label based on taxel layout

### Force Magnitude

**Vision-based sensors:**
- Method: Photometric stereo reconstruction → depth map → contact force estimation
- Output: Normalized float [0.0, 1.0]
- **Note**: Indirect estimation; precision limited by optical properties

**Distributed array sensors:**
- Method: Direct force measurement from taxel readings
- Output: Normalized float [0.0, 1.0]
- **Note**: More reliable than vision-based estimation

### Force Direction

**Vision-based sensors:**
- Method: Displacement field analysis on contact region
- Output: Unit vector in sensor-local frame

**Distributed array sensors:**
- Method: 6-axis force/torque computation from distributed taxel readings
- Output: Unit vector in sensor-local frame

### Slip Detection

**Vision-based sensors:**
- Method: Optical flow analysis on contact region between consecutive frames
- Output: Boolean (slip detected) + direction vector

**Distributed array sensors:**
- Method: Temporal force pattern analysis (shear force change rate)
- Output: Boolean (slip detected) + direction vector

### Manipulation Phase Classification

**All sensors:**
- Method: Rule-based state machine using contact and force signals
- Phases: approach → contact → lift → hold → place → release
- Transitions determined by:
  - Contact onset/offset
  - Force magnitude thresholds
  - Temporal stability of contact state

### Texture Classification

**Vision-based sensors:**
- Method: Surface feature analysis on contact region (spatial frequency, edge density)
- Output: Descriptive label

**Distributed array sensors:**
- Method: Force distribution pattern matching
- Output: Descriptive label
- **Note**: Limited texture resolution compared to vision-based sensors

### Whole-Hand Coordination

**Vision-based sensors:**
- Typically **not supported** — single-finger viewpoint
- Exception: Multi-camera setups with finger-level resolution

**Distributed array sensors:**
- Method: Cross-taxel-group temporal correlation analysis
- Output: Coordination pattern descriptor

### Object Deformation

**Vision-based sensors:**
- Method: Contact region shape change analysis across frames
- Output: Deformation magnitude and type

**Distributed array sensors:**
- Typically **not supported** — force arrays measure external force, not object response
- Exception: High-density arrays with known object stiffness priors

## Validation and Quality Control

### Hard Error Check
A hard error occurs when an annotation contradicts observable sensor data:
- Contact marked `true` when sensor signal is at baseline
- Slip marked `true` when no relative motion is detectable
- Force direction not a valid unit vector

### Soft Anomaly Check
A soft anomaly occurs when an annotation is unusual but not impossible:
- Contact region unexpectedly large or small
- Manipulation phase transition out of normal sequence
- Force magnitude at extreme values (>0.95)

### Quality Metrics

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Hard error rate | 0% | Must be zero for release |
| Soft anomaly rate | <1% | Flagged for manual review |
| Coverage | >95% | Fraction of frames with valid annotations |

## Adapter Implementation Guide

To create a new TLabel adapter:

1. **Implement `capabilities` declaration** — define which dimensions your sensor supports
2. **Implement per-dimension annotators** — follow the methods above or develop sensor-specific alternatives
3. **Validate output** — run the validation rules from [tlabel-format.md](tlabel-format.md)
4. **Test on ground-truth episodes** — manually verify annotations on a small dataset
5. **Report metrics** — hard error rate, soft anomaly rate, coverage

## Limitations

- **No universal force calibration**: Force magnitude is normalized per-sensor, not in SI units. Cross-sensor force comparison requires external calibration.
- **No standardized texture taxonomy**: Texture labels are descriptive, not from a controlled vocabulary.
- **Manipulation phase model is simplified**: The 6-phase model may not capture all manipulation strategies (e.g., pushing, rolling, pivoting).
- **Capability declarations are binary**: A dimension is either supported or not. Partial support (e.g., "slip detection works above 0.5mm/s") is not currently expressible.

---

*This specification is released under MIT License. Feedback and contributions welcome.*
