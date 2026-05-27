# TLabel Format Specification

**Version:** 0.2.0  
**Status:** Draft  
**Last Updated:** 2026-05-27

---

## Overview

TLabel Format is a cross-sensor tactile annotation schema that uses capability declarations to manage sensor heterogeneity. Instead of forcing all sensors into a single representation, TLabel allows each sensor adapter to declare which semantic dimensions it can annotate, producing compatible but not identical output.

## Core Design Principles

1. **Capability Declaration**: Each adapter explicitly declares which dimensions it supports. Unsupported dimensions are omitted from output — never fabricated.
2. **Semantic Level Unification**: TLabel unifies at the annotation level (contact, force, slip), not at the raw signal level. Different sensors capture different aspects of the same phenomena.
3. **Schema-Versioned**: All files carry a `schema_version` field, enabling backward-compatible evolution.

## Schema Structure

### Top-Level

```json
{
  "schema_version": "0.2.0",
  "sensor_info": { ... },
  "capabilities": { ... },
  "episodes": [ ... ]
}
```

### sensor_info

Describes the sensor hardware and adapter software:

```json
{
  "sensor_info": {
    "sensor_name": "Daimon-Infinity",
    "sensor_type": "vision_based",
    "manufacturer": "Daimon",
    "model": "Infinity",
    "resolution": "640x480",
    "frame_rate": 30,
    "adapter_name": "tlabel-daimon",
    "adapter_version": "0.2.0"
  }
}
```

### capabilities

Boolean declarations for each semantic dimension:

| Dimension | Type | Description |
|-----------|------|-------------|
| `contact` | bool | Binary contact detection |
| `contact_region` | bool | Spatial location of contact |
| `force_magnitude` | bool | Normalized force magnitude |
| `force_direction` | bool | Force direction vector |
| `slip_event` | bool | Binary slip detection |
| `slip_direction` | bool | Slip direction vector |
| `manipulation_phase` | bool | Phase classification (approach/contact/lift/hold/place/release) |
| `texture` | bool | Surface texture classification |
| `whole_hand_coordination` | bool | Multi-finger coordination patterns |
| `object_deformation` | bool | Object deformation detection |

```json
{
  "capabilities": {
    "contact": true,
    "contact_region": true,
    "force_magnitude": true,
    "force_direction": true,
    "slip_event": true,
    "slip_direction": true,
    "manipulation_phase": true,
    "texture": true,
    "whole_hand_coordination": false,
    "object_deformation": false
  }
}
```

### episodes

Array of annotated episodes. Each episode contains metadata and per-frame annotations:

```json
{
  "episodes": [
    {
      "episode_id": "ep_001",
      "task": "pick_place",
      "object": "plastic_bottle",
      "metadata": {
        "duration_s": 12.5,
        "num_frames": 375
      },
      "frames": [ ... ]
    }
  ]
}
```

### Per-Frame Annotation

Only dimensions declared in `capabilities` appear in frame output:

```json
{
  "frame_idx": 42,
  "timestamp_s": 1.4,
  "contact": true,
  "contact_region": "fingertip_left",
  "force_magnitude": 0.72,
  "force_direction": [0.1, -0.3, 0.95],
  "slip_event": false,
  "slip_direction": null,
  "manipulation_phase": "hold",
  "texture": "smooth_plastic"
}
```

## Semantic Dimension Definitions

### contact
- **Type**: boolean
- **True when**: Any detectable contact between sensor and object
- **False when**: No contact or signal below noise floor

### contact_region
- **Type**: string (enum)
- **Values**: Sensor-specific regions (e.g., "fingertip_left", "palm_center", "taxel_group_3")
- **Note**: Region names are sensor-dependent; TLabel does not enforce a universal spatial vocabulary

### force_magnitude
- **Type**: float [0.0, 1.0]
- **Normalized**: Sensor's maximum measurable force = 1.0
- **Note**: Not in Newtons — cross-sensor force comparison requires calibration metadata

### force_direction
- **Type**: [float, float, float]
- **Format**: Unit vector in sensor-local coordinate frame
- **Note**: Coordinate frame convention must be documented in sensor_info

### slip_event
- **Type**: boolean
- **True when**: Detectable relative motion between sensor surface and contact object
- **Detection method**: Sensor-specific (optical flow for vision-based, threshold for array)

### slip_direction
- **Type**: [float, float, float] or null
- **Format**: Unit vector indicating slip direction in sensor-local frame
- **null when**: No slip detected

### manipulation_phase
- **Type**: string (enum)
- **Values**: "approach" | "contact" | "lift" | "hold" | "place" | "release"
- **Transition rules**: Sequential, but "hold" may repeat; "release" may transition to "approach"

### texture
- **Type**: string
- **Format**: Descriptive label (e.g., "smooth_plastic", "rough_cloth", "metal_grid")
- **Note**: Not a standardized taxonomy — labels reflect sensor resolution limits

### whole_hand_coordination
- **Type**: object or null
- **Format**: Multi-finger contact state pattern
- **null when**: Sensor is single-finger or coordination cannot be determined

### object_deformation
- **Type**: object or null
- **Format**: Deformation magnitude and type
- **null when**: Sensor cannot detect deformation (e.g., low-resolution arrays)

## Sensor Type Categories

TLabel recognizes three broad sensor categories:

| Category | Typical Capabilities | Examples |
|----------|---------------------|----------|
| **vision_based** | contact, contact_region, slip_event, slip_direction, texture, manipulation_phase | GelSight, DIGIT, Daimon-Infinity |
| **distributed_array** | contact, contact_region, force_magnitude, force_direction, whole_hand_coordination | PaXini PXCap, tactile gloves |
| **hybrid** | All dimensions (potentially) | Next-generation multi-modal sensors |

## Validation Rules

A TLabel annotation file is valid if and only if:

1. `schema_version` is present and matches a known version
2. `capabilities` declares at least 1 dimension as `true`
3. Every field in `frames` that is declared `true` in `capabilities` is present and non-null
4. No field appears in `frames` that is declared `false` in `capabilities`
5. `force_magnitude` values are in [0.0, 1.0]
6. `force_direction` and `slip_direction` (when present) are unit vectors (‖v‖ ∈ [0.99, 1.01])
7. `manipulation_phase` values are from the defined enum

## Versioning

TLabel follows semantic versioning:
- **Major**: Breaking changes to schema structure
- **Minor**: New optional dimensions or fields
- **Patch**: Documentation or clarification updates

## Relationship to Other Standards

| Standard | Level | TLabel's Relationship |
|----------|-------|----------------------|
| LeRobot | Raw data format | TLabel annotations can augment LeRobot episodes |
| Open X-Embodiment | Task-level metadata | TLabel provides per-frame tactile detail |
| RoboMimic | Demonstration format | TLabel annotations are compatible with RoboMimic HDF5 |

---

*This specification is released under MIT License. Feedback and contributions welcome.*
