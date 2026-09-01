---
title: 'TLabel: A Python Package for Cross-Sensor Tactile Data Annotation and Interchange'
tags:
  - Python
  - tactile sensing
  - data annotation
  - robot manipulation
  - embodied AI
  - data format standard
authors:
  - name: Xi Luo
    equal-contrib: true
    affiliation: "1, 2"
  - name: Sheng Wu
    equal-contrib: true
    affiliation: "1"
affiliations:
  - name: Tactile Intelligence Lab, Niuxu Technology, Hangzhou, China
    index: 1
  - name: Independent Researcher
    index: 2
date: 01 September 2026
bibliography: paper.bib
---

# Summary

Robot manipulation requires rich tactile feedback, yet tactile datasets from different sensors ship in incompatible formats with no shared semantic annotations. `TLabel` is a Python package that provides the first cross-sensor tactile data annotation schema with explicit capability declarations and Compliance Level stratification. It enables heterogeneous tactile sensors — regardless of operating principle (capacitive, piezoresistive, optical, etc.) — to produce compatible 14-dimensional semantic annotations while preserving each sensor's unique strengths and honestly declaring its limitations.

# Statement of Need

Tactile sensing is critical for dexterous robot manipulation [@sundaram2019learning; @lin2024vision], yet the field suffers from a fundamental data interoperability problem. Each research group encodes tactile observations in ad-hoc formats: some store raw voltage readings, others pre-processed force vectors, and others binary masks with no provenance. This fragmentation makes cross-sensor comparison, data sharing, and benchmark construction nearly impossible.

Recent efforts toward large-scale tactile foundation models [@qi2024tactile; @kerr2024learning] have amplified this problem. Training on heterogeneous data requires either re-implementing sensor-specific pipelines for each dataset or discarding valuable metadata that could inform model design. The absence of a standard annotation format also means that downstream consumers — robotics researchers, foundation model developers, and benchmark organizers — must reverse-engineer each dataset to understand what information is actually available.

`TLabel` addresses this gap by providing: (1) a unified 14-dimensional annotation schema covering spatial, mechanical, surface, dynamic, and meta perceptions; (2) an explicit capability declaration system where each sensor adapter states which dimensions it can and cannot annotate; (3) a four-level Compliance hierarchy (L1–L4) ensuring every sensor participates at its appropriate information density; and (4) semantic maturity tracking that distinguishes verified annotations from estimates from placeholders.

# State of the Field

No existing tool provides a cross-sensor tactile annotation standard. The closest prior work includes:

**Sensor-specific toolkits.** Packages such as `GelSightPy` and BioTac processing scripts provide format-specific loaders but do not address inter-sensor compatibility. Each toolkit is designed for a single sensor family and assumes domain-specific knowledge from its users.

**Robotics data formats.** `LeRobot` [@albert2025openlerobot] and `RLDS` provide standardized formats for robot manipulation trajectories, but they focus on proprioceptive and visual data. Tactile observations are treated as opaque byte arrays without semantic structure. `TLabel` complements these formats by providing the semantic layer that they lack.

**Robot data quality tools.** `RDA` (Robot Data Audit) [@luo2026rda] provides data quality diagnostics for robot manipulation datasets but does not define annotation schemas. `TLabel` and `RDA` are designed to work together: `TLabel` annotates, `RDA` audits.

**General data schemas.** Schema languages such as JSON Schema and Pydantic provide validation infrastructure but do not encode domain-specific knowledge about tactile sensing physics. `TLabel` builds on these tools while adding the tactile-specific semantic model.

`TLabel` was built as a standalone package rather than contributing to existing projects because no existing project targets the specific problem of cross-sensor tactile annotation standardization. The package follows Python packaging best practices and integrates with the broader scientific Python ecosystem (NumPy, Pandas, xarray).

# Software Design

`TLabel` follows a three-layer architecture:

**Layer 1 — Schema.** The 14-dimensional annotation schema defines the semantic space: spatial contact (pose, area, pressure distribution), mechanical interaction (force vector, torque, slip), surface properties (texture, temperature), dynamic events (contact onset/offset, slip transitions), and metadata (compliance level, provenance). Each dimension carries a capability declaration: `supported`, `unsupported`, or `estimated`.

**Layer 2 — Adapters.** Each sensor adapter (currently 13: BioTac, GelSight/DIGIT, PaXini, Sparsh, YCB-Slide, Daimon DM-TacClaw, XELA uSkin, ATI force/torque, etc.) implements a common `SensorAdapterBase` interface with `extract()` and `load()` methods. Adapters self-report their Compliance Level (L1–L4) based on which dimensions their sensor physics can support.

**Layer 3 — Downstream converters.** Exporters transform annotated data into training-ready formats: JSON, CSV, FTP-1 Zarr, LeRobot, RLDS, and ROS2. Each converter preserves the semantic annotations from the `TLabel` schema.

A key design principle is the **non-fabrication principle**: `unavailable ≠ zero ≠ estimated`. When a sensor cannot measure a dimension (e.g., a purely force-based sensor cannot report texture), the schema records this as `unsupported` rather than filling in a zero or guess. This honest representation prevents downstream models from learning on fabricated features.

The package also provides CLI tools (`tlabel list`, `tlabel info`, `tlabel validate`, `tlabel convert`) for schema inspection and batch processing, and an interactive Jupyter-based annotation panel (`data.review()`) for bilingual (Chinese/English) manual annotation and AI pre-annotation.

# Research Impact

`TLabel` has been used to annotate over 15,000 real tactile frames from three public datasets (BioTac, YCB-Slide, Sparsh), demonstrating cross-sensor schema migration. The package has been downloaded from PyPI since its initial release and has attracted an external contributor who submitted a XELA uSkin adapter (PR #24). The software has also been used to support the development of `RDA` (Robot Data Audit), a complementary data quality diagnostics tool.

The 14-dimensional schema and Compliance Level system were developed through iterative design informed by the physics of 13 different sensor types, ensuring that the standard is grounded in real sensing capabilities rather than theoretical ideals.

# AI Usage Disclosure

Generative AI tools were used in the development of this software and the preparation of this manuscript. Specifically, large language models (LLMs) assisted with: (1) code scaffolding and refactoring of sensor adapter implementations; (2) documentation writing and API reference generation; (3) drafting of this manuscript. All AI-assisted outputs were reviewed, validated, and modified by the human authors. Core design decisions — including the 14-dimensional schema, the Compliance Level hierarchy, the non-fabrication principle, and the three-layer architecture — were made by the human authors.

# Acknowledgements

We thank the open-source contributors to the `TLabel` project, including `gaolebaigao` for the XELA uSkin adapter. We also thank the developers of BioTac, GelSight, PaXini, and Sparsh for making their datasets publicly available.

# References
