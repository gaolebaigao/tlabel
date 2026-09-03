"""
v0.21.0 新增：data_quality 与 provenance 两个可选扩展元数据字段的测试。

设计原则：
- 两个字段完全可选，缺省 None 时向后兼容
- 提供时按结构校验，不合法字段报 validate() error
- 序列化 round-trip（to_dict → from_dict）保真
"""

import pytest

from tlabel.core.schema import (
    TLabelSchemaV2,
    VALID_DATA_QUALITY_LEVELS,
)


# =========================================================================
# 基础默认值 / 向后兼容
# =========================================================================

class TestBackwardCompat:
    def test_default_none(self):
        s = TLabelSchemaV2()
        assert s.data_quality is None
        assert s.provenance is None

    def test_to_dict_omits_when_none(self):
        """两个字段为 None 时，to_dict 不应包含对应 key，保持向后兼容"""
        s = TLabelSchemaV2()
        d = s.to_dict()
        assert "data_quality" not in d
        assert "provenance" not in d

    def test_from_dict_legacy_no_keys(self):
        """旧数据（无 data_quality/provenance）from_dict 不报错"""
        legacy = {
            "contact": True,
            "contact_centroid": [0.5, 0.5],
            "slip_event": False,
            "confidence": 0.9,
            "compliance_level": "L1",
        }
        s = TLabelSchemaV2.from_dict(legacy)
        assert s.data_quality is None
        assert s.provenance is None


# =========================================================================
# data_quality 字段
# =========================================================================

class TestDataQuality:
    VALID_Q2 = {
        "level": "Q2",
        "raw_processed": True,
        "denoised": True,
        "calibrated": True,
        "verified": False,
        "verified_by": None,
        "notes": "出厂校准，未做交叉验证",
    }

    def test_valid_q2(self):
        s = TLabelSchemaV2(data_quality=self.VALID_Q2)
        ok, errs = s.validate()
        assert ok, errs

    def test_all_levels_accepted(self):
        for lvl in VALID_DATA_QUALITY_LEVELS:
            dq = {"level": lvl}
            s = TLabelSchemaV2(data_quality=dq)
            ok, errs = s.validate()
            assert ok, (lvl, errs)

    def test_invalid_level_rejected(self):
        s = TLabelSchemaV2(data_quality={"level": "Q5"})
        ok, errs = s.validate()
        assert not ok
        assert any("data_quality.level" in e for e in errs)

    def test_bool_field_wrong_type(self):
        s = TLabelSchemaV2(data_quality={"denoised": "yes"})  # 应为 bool
        ok, errs = s.validate()
        assert not ok
        assert any("data_quality.denoised" in e for e in errs)

    def test_notes_wrong_type(self):
        s = TLabelSchemaV2(data_quality={"notes": 123})
        ok, errs = s.validate()
        assert not ok
        assert any("data_quality.notes" in e for e in errs)

    def test_not_dict_rejected(self):
        s = TLabelSchemaV2(data_quality="Q2")  # 应为 dict
        ok, errs = s.validate()
        assert not ok
        assert any("data_quality must be a dict" in e for e in errs)

    def test_partial_dict_allowed(self):
        """只填 level 也应通过，其他子字段全部可选"""
        s = TLabelSchemaV2(data_quality={"level": "Q1"})
        ok, errs = s.validate()
        assert ok, errs


# =========================================================================
# provenance 字段
# =========================================================================

class TestProvenance:
    VALID_PROV = {
        "sensor_model": "GelSight Mini v2",
        "sensor_firmware": "1.3.0",
        "calibration_date": "2026-08-01",
        "sampling_rate_hz": 270,
    }

    def test_valid_full(self):
        s = TLabelSchemaV2(provenance=self.VALID_PROV)
        ok, errs = s.validate()
        assert ok, errs

    def test_partial_allowed(self):
        s = TLabelSchemaV2(provenance={"sensor_model": "XELA uSkin"})
        ok, errs = s.validate()
        assert ok, errs

    def test_sampling_rate_must_be_positive(self):
        s = TLabelSchemaV2(provenance={"sampling_rate_hz": 0})
        ok, errs = s.validate()
        assert not ok
        assert any("sampling_rate_hz" in e for e in errs)

    def test_sampling_rate_rejects_bool(self):
        s = TLabelSchemaV2(provenance={"sampling_rate_hz": True})
        ok, errs = s.validate()
        assert not ok
        assert any("sampling_rate_hz" in e for e in errs)

    def test_sampling_rate_accepts_float(self):
        s = TLabelSchemaV2(provenance={"sampling_rate_hz": 120.5})
        ok, errs = s.validate()
        assert ok, errs

    def test_calibration_date_bad_format(self):
        s = TLabelSchemaV2(provenance={"calibration_date": "2026/08/01"})
        ok, errs = s.validate()
        assert not ok
        assert any("calibration_date" in e for e in errs)

    def test_calibration_date_good_format(self):
        s = TLabelSchemaV2(provenance={"calibration_date": "2026-08-01"})
        ok, errs = s.validate()
        assert ok, errs

    def test_sensor_model_wrong_type(self):
        s = TLabelSchemaV2(provenance={"sensor_model": 42})
        ok, errs = s.validate()
        assert not ok
        assert any("provenance.sensor_model" in e for e in errs)

    def test_not_dict_rejected(self):
        s = TLabelSchemaV2(provenance=["GelSight"])
        ok, errs = s.validate()
        assert not ok
        assert any("provenance must be a dict" in e for e in errs)


# =========================================================================
# 序列化 round-trip
# =========================================================================

class TestRoundTrip:
    def test_roundtrip_with_metadata(self):
        s1 = TLabelSchemaV2(
            contact=True,
            contact_centroid=[0.3, 0.4],
            slip_event=False,
            confidence=0.95,
            compliance_level="L2",
            force_magnitude=1.5,
            data_quality={"level": "Q3", "verified": True, "verified_by": "auto"},
            provenance={"sensor_model": "BioTac", "sampling_rate_hz": 100},
        )
        d = s1.to_dict()
        s2 = TLabelSchemaV2.from_dict(d)

        assert s2.data_quality == s1.data_quality
        assert s2.provenance == s1.provenance
        assert s2.force_magnitude == s1.force_magnitude
        assert s2.compliance_level == "L2"

    def test_roundtrip_without_metadata(self):
        """没有 metadata 时 round-trip 仍兼容"""
        s1 = TLabelSchemaV2(contact=False, slip_event=False, confidence=1.0)
        d = s1.to_dict()
        s2 = TLabelSchemaV2.from_dict(d)
        assert s2.data_quality is None
        assert s2.provenance is None


# =========================================================================
# validate() 整体行为：metadata 不影响 compliance_level 规则
# =========================================================================

class TestValidationIndependence:
    def test_metadata_independent_of_compliance(self):
        """即使带了 metadata，L2 缺 force_magnitude 仍报错"""
        s = TLabelSchemaV2(
            contact=True,
            contact_centroid=[0.1, 0.1],
            compliance_level="L2",
            # force_magnitude 缺失
            data_quality={"level": "Q2"},
            provenance={"sensor_model": "X"},
        )
        ok, errs = s.validate()
        assert not ok
        assert any("force_magnitude" in e for e in errs)
        # 同时 metadata 本身没问题
        assert not any("data_quality" in e or "provenance" in e for e in errs)


# =========================================================================
# build_provenance() 自动填充 helper
# =========================================================================

class TestBuildProvenanceHelper:
    def test_data_adapter_default(self):
        from tlabel.adapters.base import DataAdapterBase

        class DummyAdapter(DataAdapterBase):
            name = "dummy"
            supported_extensions = [".dat"]
            def load(self, *a, **k): return None
            def get_capabilities(self): return {}
            def get_sensor_info(self):
                return {"type": "vision", "manufacturer": "GelSight Inc.", "model": "Mini"}
            def extract_schema(self, raw): return TLabelSchemaV2()

        a = DummyAdapter()
        prov = a.build_provenance()
        assert prov is not None
        assert prov.get("sensor_model") == "Mini"

    def test_data_adapter_no_info(self):
        from tlabel.adapters.base import DataAdapterBase

        class EmptyAdapter(DataAdapterBase):
            name = "empty"
            supported_extensions = [".dat"]
            def load(self, *a, **k): return None
            def get_capabilities(self): return {}
            def get_sensor_info(self): return {}
            def extract_schema(self, raw): return TLabelSchemaV2()

        a = EmptyAdapter()
        assert a.build_provenance() is None

    def test_data_adapter_firmware_passthrough(self):
        from tlabel.adapters.base import DataAdapterBase

        class RichAdapter(DataAdapterBase):
            name = "rich"
            supported_extensions = [".dat"]
            def load(self, *a, **k): return None
            def get_capabilities(self): return {}
            def get_sensor_info(self):
                return {
                    "model": "BioTac",
                    "firmware": "2.1.0",
                    "sampling_rate_hz": 100,
                }
            def extract_schema(self, raw): return TLabelSchemaV2()

        a = RichAdapter()
        prov = a.build_provenance()
        assert prov == {
            "sensor_model": "BioTac",
            "sensor_firmware": "2.1.0",
            "sampling_rate_hz": 100,
        }
        # build 出来的字典应能通过 provenance 校验
        s = TLabelSchemaV2(provenance=prov)
        ok, errs = s.validate()
        assert ok, errs