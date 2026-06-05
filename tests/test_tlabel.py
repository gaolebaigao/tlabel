"""TouchLabel pip包单元测试"""
import json
import tempfile
import os
import pytest


class TestImport:
    def test_import_tlabel(self):
        import tlabel
        assert hasattr(tlabel, "load")
        assert hasattr(tlabel, "__version__")

    def test_import_adapters(self):
        from tlabel.adapters.gelsight import GelSightAdapter
        from tlabel.adapters.paxini import PaxiniAdapter
        from tlabel.adapters.daimon import DaimonAdapter

    def test_import_types(self):
        from tlabel.core.types import TLabelData, TLabelFrame


class TestRegistry:
    def test_pkl_detection(self):
        from tlabel.core.registry import auto_detect_format
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            assert auto_detect_format(path) == "gelsight"
        finally:
            os.unlink(path)

    def test_h5_detection(self):
        from tlabel.core.registry import auto_detect_format
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            assert auto_detect_format(path) == "paxini"
        finally:
            os.unlink(path)

    def test_hdf5_detection(self):
        from tlabel.core.registry import auto_detect_format
        with tempfile.NamedTemporaryFile(suffix=".hdf5", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            assert auto_detect_format(path) == "paxini"
        finally:
            os.unlink(path)

    def test_parquet_detection(self):
        from tlabel.core.registry import auto_detect_format
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            assert auto_detect_format(path) == "daimon"
        finally:
            os.unlink(path)

    def test_daimon_dir_detection(self):
        from tlabel.core.registry import auto_detect_format
        info = {"robot_type": "ugripper_right", "fps": 30, "total_episodes": 1}
        with tempfile.TemporaryDirectory() as td:
            meta_dir = os.path.join(td, "meta")
            os.makedirs(meta_dir)
            with open(os.path.join(meta_dir, "info.json"), "w") as f:
                json.dump(info, f)
            assert auto_detect_format(td) == "daimon"

    def test_unknown_format(self):
        from tlabel.core.registry import auto_detect_format
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            assert auto_detect_format(path) is None
        finally:
            os.unlink(path)


class TestTLabelFrame:
    def _make_frame(self, **overrides):
        from tlabel.core.types import TLabelFrame
        defaults = {
            "frame_idx": 0,
            "timestamp_s": 0.0,
            "tlabel_v2": {
                "contact": 1.0,
                "force_magnitude": 0.8,
                "force_peak": 0.6,
                "slip_event": 0.3,
                "contact_area": 0.5,
                "deformation_magnitude": 0.4,
                "force_direction": 0.2,
                "slip_entropy": 0.1,
                "texture_energy": 0.0,
                "edge_density": 0.0,
                "centroid_x": 0.5,
                "normal_field_magnitude": 0.3,
                "normal_field_variance": 0.2,
                "shear_field_magnitude": 0.0,
                "shear_field_direction": 0.0,
                "delta_force_normal": 0.1,
                "delta_force_shear": 0.05,
                "friction_cone_ratio": 0.7,
            },
            "manipulation_phase": "stable_contact",
            "confidence": 0.9,
        }
        defaults.update(overrides)
        return TLabelFrame(**defaults)

    def test_properties(self):
        f = self._make_frame()
        assert f.contact == 1.0
        assert f.slip_event == 0.3
        assert f.force_magnitude == 0.8

    def test_patch_basic(self):
        f = self._make_frame()
        rec = f.patch("contact", 0.0, cascade=False)
        assert f.tlabel_v2["contact"] == 0.0
        assert rec["old_value"] == 1.0
        assert rec["new_value"] == 0.0

    def test_patch_cascade_contact_to_zero(self):
        f = self._make_frame()
        f.patch("contact", 0.0, cascade=True)
        assert f.tlabel_v2["force_magnitude"] == 0.0
        assert f.tlabel_v2["slip_event"] == 0.0
        assert f.tlabel_v2["contact_area"] == 0.0
        assert f.manipulation_phase == "idle"

    def test_patch_no_cascade_when_not_zero(self):
        f = self._make_frame()
        f.patch("contact", 0.5, cascade=True)
        # force should NOT be zeroed when contact != 0
        assert f.tlabel_v2["force_magnitude"] == 0.8

    def test_is_modified(self):
        f = self._make_frame()
        assert not f.is_modified
        f.patch("contact", 0.0)
        assert f.is_modified

    def test_to_dict(self):
        f = self._make_frame()
        d = f.to_dict()
        assert "frame_idx" in d
        assert "tlabel_v2" in d
        assert "manipulation_phase" in d


class TestTLabelData:
    def _make_data(self, n_frames=10):
        from tlabel.core.types import TLabelData, TLabelFrame
        frames = []
        for i in range(n_frames):
            f = TLabelFrame(
                frame_idx=i,
                timestamp_s=i / 30.0,
                tlabel_v2={"contact": 1.0 if i % 3 == 0 else 0.0,
                           "force_magnitude": 0.5 if i % 3 == 0 else 0.0,
                           "slip_event": 0.0, "force_peak": 0.0,
                           "deformation_magnitude": 0.0, "force_direction": 0.0,
                           "slip_entropy": 0.0, "texture_energy": 0.0,
                           "edge_density": 0.0, "contact_area": 0.0,
                           "centroid_x": 0.5, "normal_field_magnitude": 0.0,
                           "normal_field_variance": 0.0,
                           "shear_field_magnitude": 0.0,
                           "shear_field_direction": 0.0,
                           "delta_force_normal": 0.0, "delta_force_shear": 0.0,
                           "friction_cone_ratio": 0.0},
                manipulation_phase="idle",
                confidence=0.9,
            )
            frames.append(f)
        return TLabelData(
            frames=frames,
            sensor_info={"type": "test"},
            episode_info={"source": "test"},
            capabilities={"contact": True},
        )

    def test_num_frames(self):
        data = self._make_data(10)
        assert data.num_frames == 10

    def test_duration(self):
        data = self._make_data(10)
        assert data.duration_s > 0

    def test_batch_patch(self):
        data = self._make_data(10)
        n = data.batch_patch(0, 9, "contact", 0.0)
        assert n > 0

    def test_to_dict(self):
        data = self._make_data(5)
        d = data.to_dict()
        assert d["schema_version"] == "0.3.0"
        assert "frames" in d
        assert len(d["frames"]) == 5

    def test_empty_data(self):
        from tlabel.core.types import TLabelData
        data = TLabelData(
            frames=[], sensor_info={}, episode_info={}, capabilities={}
        )
        assert data.num_frames == 0
        assert data.duration_s == 0.0
        assert data.modified_count == 0

    def test_len(self):
        data = self._make_data(10)
        assert len(data) == 10


class TestLoaderErrors:
    def test_file_not_found(self):
        import tlabel
        with pytest.raises(FileNotFoundError):
            tlabel.load("/nonexistent/path/data.pkl")

    def test_unknown_format(self):
        import tlabel
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            with pytest.raises(ValueError, match="无法识别"):
                tlabel.load(path)
        finally:
            os.unlink(path)


class TestExport:
    def test_json_export(self):
        from tlabel.core.types import TLabelData, TLabelFrame
        from tlabel.export.writer import export_data
        frames = [TLabelFrame(
            frame_idx=0, timestamp_s=0.0,
            tlabel_v2={"contact": 1.0, "force_magnitude": 0.5,
                       "slip_event": 0.0, "force_peak": 0.0,
                       "deformation_magnitude": 0.0, "force_direction": 0.0,
                       "slip_entropy": 0.0, "texture_energy": 0.0,
                       "edge_density": 0.0, "contact_area": 0.0,
                       "centroid_x": 0.5, "normal_field_magnitude": 0.0,
                       "normal_field_variance": 0.0,
                       "shear_field_magnitude": 0.0,
                       "shear_field_direction": 0.0,
                       "delta_force_normal": 0.0, "delta_force_shear": 0.0,
                       "friction_cone_ratio": 0.0},
            manipulation_phase="idle", confidence=0.9,
        )]
        data = TLabelData(
            frames=frames, sensor_info={"type": "test"},
            episode_info={"source": "test"}, capabilities={"contact": True},
        )
        with tempfile.TemporaryDirectory() as td:
            path = export_data(data, os.path.join(td, "out"), format="json")
            assert os.path.exists(path)
            with open(path) as f:
                d = json.load(f)
            assert d["frames"][0]["tlabel_v2"]["contact"] == 1.0

    def test_csv_export(self):
        from tlabel.core.types import TLabelData, TLabelFrame
        from tlabel.export.writer import export_data
        frames = [TLabelFrame(
            frame_idx=0, timestamp_s=0.0,
            tlabel_v2={"contact": 1.0, "force_magnitude": 0.5,
                       "slip_event": 0.0, "force_peak": 0.0,
                       "deformation_magnitude": 0.0, "force_direction": 0.0,
                       "slip_entropy": 0.0, "texture_energy": 0.0,
                       "edge_density": 0.0, "contact_area": 0.0,
                       "centroid_x": 0.5, "normal_field_magnitude": 0.0,
                       "normal_field_variance": 0.0,
                       "shear_field_magnitude": 0.0,
                       "shear_field_direction": 0.0,
                       "delta_force_normal": 0.0, "delta_force_shear": 0.0,
                       "friction_cone_ratio": 0.0},
            manipulation_phase="idle", confidence=0.9,
        )]
        data = TLabelData(
            frames=frames, sensor_info={"type": "test"},
            episode_info={"source": "test"}, capabilities={"contact": True},
        )
        with tempfile.TemporaryDirectory() as td:
            path = export_data(data, os.path.join(td, "out"), format="csv")
            assert os.path.exists(path)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2  # header + 1 data row
            assert "contact" in lines[0]
