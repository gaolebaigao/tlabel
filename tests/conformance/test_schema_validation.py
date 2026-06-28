"""
TLabel Schema Conformance Test Suite

Validates that TLabelData output conforms to the JSON schema (tlabel-schema.json).
Run with: pytest tests/conformance/test_schema_validation.py
"""

import json
import pytest
from pathlib import Path

from tlabel.core.types import TLabelData, TLabelFrame


SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema" / "tlabel-schema.json"


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def sample_data():
    """Create a minimal valid TLabelData instance."""
    frames = [
        TLabelFrame(
            frame_idx=0,
            timestamp_s=0.0,
            tlabel_v2={
                "contact": 1.0,
                "deformation_magnitude": 0.234,
                "force_magnitude": 0.234,
                "force_peak": 0.456,
                "force_direction": 127.3,
                "slip_entropy": 3.14,
                "slip_event": 0.0,
                "texture_energy": 0.054,
                "edge_density": 0.12,
                "contact_area": 0.35,
                "centroid_x": 0.52,
                "normal_field_magnitude": 0.230,
                "normal_field_variance": 0.012,
                "shear_field_magnitude": 0.089,
                "shear_field_direction": 45.6,
                "delta_force_normal": 0.015,
                "delta_force_shear": 0.008,
                "friction_cone_ratio": 0.387,
                "optical_flow_magnitude": 1.23,
                "optical_flow_direction": 89.4,
                "temporal_deformation_rate": 0.05,
                "contact_transition": 0.85,
            },
            manipulation_phase="stable_contact",
            confidence=0.95,
        )
    ]
    return TLabelData(
        frames=frames,
        sensor_info={
            "sensor_name": "TestSensor",
            "sensor_type": "vision_based",
            "adapter_name": "test_adapter",
            "adapter_version": "0.8.0",
        },
        episode_info={"episode_id": "test_ep", "task": "test_task"},
        capabilities={"contact": True},
        schema_version="0.8.0",
        sensor_id="test_sensor_01",
    )


def test_schema_file_exists():
    """Schema file must exist."""
    assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"


def test_schema_is_valid_json():
    """Schema must be valid JSON."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    assert "$schema" in schema
    assert schema["title"] == "TLabel Annotation Format"


def test_tlabel_data_conforms_to_schema(sample_data, schema):
    """TLabelData.to_dict() output must validate against the JSON schema."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")

    data_dict = sample_data.to_dict()
    jsonschema.validate(instance=data_dict, schema=schema)


def test_all_22_dimensions_present(sample_data):
    """Every frame must have exactly 22 dimensions in tlabel_v2."""
    for frame in sample_data.frames:
        assert len(frame.tlabel_v2) == 22, (
            f"Expected 22 dimensions, got {len(frame.tlabel_v2)}"
        )


def test_required_top_level_fields(sample_data):
    """Top-level output must have all required fields."""
    d = sample_data.to_dict()
    required = ["schema_version", "format", "sensor", "capabilities", "frames"]
    for field in required:
        assert field in d, f"Missing required field: {field}"


def test_frame_structure(sample_data):
    """Each frame must have required fields."""
    d = sample_data.to_dict()
    valid_phases = {
        "idle", "initial_contact", "stable_contact", "slip",
        "release", "re_contact", "approach", "retract",
        "grasp", "transport", "hold"
    }
    for frame in d["frames"]:
        assert "frame_idx" in frame
        assert "timestamp_s" in frame
        assert "tlabel_v2" in frame
        assert "manipulation_phase" in frame
        assert frame["manipulation_phase"] in valid_phases


def test_cascade_contact_zero():
    """Setting contact=0 should cascade zero other force fields."""
    frame = TLabelFrame(
        frame_idx=0, timestamp_s=0.0,
        tlabel_v2={
            "contact": 1.0, "deformation_magnitude": 0.5,
            "force_magnitude": 0.5, "force_peak": 0.3,
            "slip_event": 0.8, "delta_force_normal": 0.1,
            "delta_force_shear": 0.05, "contact_area": 0.4,
            "contact_transition": 0.9,
        },
        manipulation_phase="stable_contact",
    )
    frame.patch("contact", 0.0, cascade=True)

    assert frame.tlabel_v2["force_magnitude"] == 0.0
    assert frame.tlabel_v2["force_peak"] == 0.0
    assert frame.tlabel_v2["slip_event"] == 0.0
    assert frame.tlabel_v2["delta_force_normal"] == 0.0
    assert frame.tlabel_v2["delta_force_shear"] == 0.0
    assert frame.tlabel_v2["contact_area"] == 0.0
    assert frame.manipulation_phase == "idle"
    assert len(frame.patches) == 1
    assert len(frame.patches[0]["cascade"]) > 0


def test_cascade_slip_without_contact():
    """Setting slip_event > 0.5 without contact should auto-set contact=1."""
    frame = TLabelFrame(
        frame_idx=0, timestamp_s=0.0,
        tlabel_v2={"contact": 0.0, "slip_event": 0.0},
        manipulation_phase="idle",
    )
    frame.patch("slip_event", 0.8, cascade=True)

    assert frame.tlabel_v2["contact"] == 1.0
    assert frame.manipulation_phase == "slip"


def test_cascade_force_without_contact():
    """Setting force > 0 without contact should auto-set contact=1."""
    frame = TLabelFrame(
        frame_idx=0, timestamp_s=0.0,
        tlabel_v2={"contact": 0.0, "force_magnitude": 0.0},
        manipulation_phase="idle",
    )
    frame.patch("force_magnitude", 0.5, cascade=True)

    assert frame.tlabel_v2["contact"] == 1.0


def test_feature_metadata_completeness():
    """Feature metadata must cover all 22 dimensions."""
    from tlabel.features_meta import FEATURE_REGISTRY

    expected_dims = [
        "contact", "deformation_magnitude", "force_magnitude", "force_peak",
        "force_direction", "slip_entropy", "slip_event", "texture_energy",
        "edge_density", "contact_area", "centroid_x",
        "normal_field_magnitude", "normal_field_variance",
        "shear_field_magnitude", "shear_field_direction",
        "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
        "optical_flow_magnitude", "optical_flow_direction",
        "temporal_deformation_rate", "contact_transition",
    ]
    for dim in expected_dims:
        assert dim in FEATURE_REGISTRY, f"Missing metadata for: {dim}"
        meta = FEATURE_REGISTRY[dim]
        assert "feature_id" in meta
        assert "category" in meta
        assert meta["category"] in ["deformation", "gradient", "force_semantic", "temporal"]


def test_force_magnitude_deprecated():
    """force_magnitude must be marked deprecated in metadata."""
    from tlabel.features_meta import FEATURE_REGISTRY

    meta = FEATURE_REGISTRY["force_magnitude"]
    assert meta["deprecated"] is True
    assert meta.get("deprecated_since") == "0.7.0"
    assert meta.get("replacement") == "deformation_magnitude_peak"
