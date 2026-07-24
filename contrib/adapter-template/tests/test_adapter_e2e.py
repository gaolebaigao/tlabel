"""端到端测试 — 验证完整数据流（需要样例数据）"""

import pytest


class TestE2E:
    """端到端集成测试"""

    def test_load_and_export_json(self, tmp_path):
        """加载 → 导出 JSON 完整流程"""
        # from adapter.my_sensor import MySensorAdapter
        # from tlabel.export.writer import Exporter
        #
        # adapter = MySensorAdapter()
        # data = adapter.load("data/sample/")
        #
        # exporter = Exporter()
        # output_path = tmp_path / "output.json"
        # exporter.to_json(data, str(output_path))
        #
        # assert output_path.exists()
        # assert output_path.stat().st_size > 0
        pytest.skip("TODO: implement with actual sample data")

    def test_load_and_export_csv(self, tmp_path):
        """加载 → 导出 CSV 完整流程"""
        pytest.skip("TODO: implement with actual sample data")
