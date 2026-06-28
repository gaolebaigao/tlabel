# TLabel: A Sensor-Agnostic Annotation Schema for Tactile Intelligence

**Version:** 0.8.0 | **Date:** 2026-06-28  
**Authors:** Xi Luo (Niuzu Tech)  
**Contact:** luoxi@touchlabelai.cn

---

## Abstract

The rapid proliferation of tactile sensors in robotics has created a fragmentation problem: each sensor produces data in a proprietary format, making cross-sensor comparison, dataset sharing, and foundation model training unnecessarily difficult. TLabel is a sensor-agnostic annotation schema and toolkit that addresses this gap by defining a unified 22-dimensional feature space, a capability declaration system, and a physical consistency enforcement mechanism. This document describes the design rationale, dimension taxonomy, and integration with emerging foundation models such as FTP-1.

---

## 1. Introduction

Tactile sensing is essential for dexterous manipulation, yet the field lacks a standardized annotation format. Vision has COCO and ImageNet; natural language has CoNLL and Universal Dependencies; but tactile data remains siloed in sensor-specific binaries.

TLabel was designed from the ground up to be the standard for touch. Its key insight is that while raw sensor signals differ radically across modalities (vision-based gel elastomers, resistive taxel arrays, event-driven sensors), the semantic annotations that matter for downstream tasks can be expressed in a common vocabulary.

---

## 2. Design Principles

### 2.1 Semantic Unification Over Raw Signal Unification

We deliberately avoid forcing all sensors into a common raw representation. Instead, TLabel unifies at the annotation level: every adapter maps its raw data to the same 22-dimensional semantic feature vector. The raw data can remain sensor-specific (stored in sensor_specific), while the semantic layer is interoperable.

### 2.2 Capability Declaration

Not all sensors can measure all 22 dimensions. Rather than filling gaps with zeros (which would be misleading), TLabel uses a capabilities dictionary where each sensor declares what it can and cannot provide.

### 2.3 Pixel-Space Honesty

Many tactile force measurements are actually pixel-space deformations merely correlated with force. TLabel is explicit about this: dimensions like normal_field_magnitude and shear_field_magnitude are computed in pixel space and reported in arbitrary_unit. Only when sensor_profile provides calibration parameters can these be converted to physical units.

### 2.4 Physical Consistency via Cascade Rules

TLabel enforces physical plausibility through cascade rules:
- Contact release zeros all force-related fields
- Slip events require contact
- Force without contact is physically impossible (auto-corrected)

---

## 3. The 22-Dimensional Feature Space

### 3.1 Deformation (IDs 1-5)
contact, deformation_magnitude, force_magnitude (deprecated), force_peak, force_direction

### 3.2 Gradient (IDs 6-9)
slip_entropy, slip_event, texture_energy, edge_density

### 3.3 Force Semantic (IDs 10-18)
contact_area, centroid_x, normal_field_magnitude, normal_field_variance, shear_field_magnitude, shear_field_direction, delta_force_normal, delta_force_shear, friction_cone_ratio

### 3.4 Temporal (IDs 19-22)
optical_flow_magnitude, optical_flow_direction, temporal_deformation_rate, contact_transition

---

## 4. Integration with Foundation Models

### 4.1 FTP-1 / MTTS

FTP-1 is the first general-purpose tactile foundation model (Tsinghua + Sharpa Robotics). It uses MTTS (Morphology-aware Tactile Token Space) with 21 functional areas.

TLabel v0.8.0 provides native FTP-1/MTTS export. The relationship is complementary:
- TLabel = data layer (annotation, standardization, quality)
- FTP-1 = model layer (policy learning, foundation model)

### 4.2 LeRobot

TLabel supports HuggingFace LeRobot format export for robot learning ecosystem integration.

---

## 5. Future Directions

1. Physical calibration database with community-contributed sensor profiles
2. TLabel-Bench: Standardized benchmark for cross-sensor transfer learning
3. Real-time streaming via WebSocket for online experiments
4. Multi-sensor fusion for synchronized multi-sensor episodes
5. Tactile language model integration for LLM-based reasoning

---

## 6. Conclusion

TLabel provides the missing standardization layer for tactile intelligence. By defining a sensor-agnostic 22-dimensional feature space with physical consistency guarantees, it enables cross-sensor comparison, dataset sharing, and foundation model training. The v0.8.0 release adds FTP-1/MTTS export, positioning TLabel as the data layer for the emerging tactile foundation model ecosystem.

---

*Released under CC-BY-4.0. Software under MIT License.*
