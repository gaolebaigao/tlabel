"""基础测试 — 验证适配器加载和 Schema 兼容性"""

import pytest
from adapter.my_sensor import MySensorAdapter


class TestMySensorAdapter:
    """适配器基础测试"""

    def setup_method(self):
        self.adapter = MySensorAdapter()

    def test_adapter_name(self):
        """适配器名称不为空"""
        assert self.adapter.name
        assert isinstance(self.adapter.name, str)

    def test_supported_extensions(self):
        """支持的扩展名列表不为空"""
        exts = self.adapter.supported_extensions
        assert isinstance(exts, list)
        assert len(exts) > 0
        for ext in exts:
            assert ext.startswith(".")

    def test_capabilities_structure(self):
        """capabilities 包含所有 22 个维度"""
        caps = self.adapter.get_capabilities()
        expected_keys = {
            "contact", "deformation_magnitude", "force_magnitude",
            "force_peak", "force_direction", "slip_entropy", "slip_event",
            "texture_energy", "edge_density", "contact_area", "centroid_x",
            "normal_field_magnitude", "normal_field_variance",
            "shear_field_magnitude", "shear_field_direction",
            "delta_force_normal", "delta_force_shear",
            "friction_cone_ratio", "optical_flow_magnitude",
            "optical_flow_direction", "temporal_deformation_rate",
            "contact_transition",
        }
        assert set(caps.keys()) == expected_keys, \
            f"Missing keys: {expected_keys - set(caps.keys())}"

    def test_sensor_info_structure(self):
        """sensor_info 包含必要字段"""
        info = self.adapter.get_sensor_info()
        assert "type" in info
        assert "manufacturer" in info
        assert "model" in info

    def test_load_returns_tlabel_data(self, tmp_path):
        """load() 返回 TLabelData 且通过 Schema 校验"""
        # TODO: 创建样例数据文件到 tmp_path
        # sample_file = tmp_path / "sample.csv"
        # sample_file.write_text("your,sample,data")

        # data = self.adapter.load(str(sample_file))
        # assert data.num_frames > 0

        # # Schema 校验
        # from tlabel.core.schema import validate_tlabel_v2
        # for frame in data.frames:
        #     result = validate_tlabel_v2(frame.tlabel_v2)
        #     assert result.valid, f"Schema validation failed: {result.errors}"
        pytest.skip("TODO: implement with actual sample data")
