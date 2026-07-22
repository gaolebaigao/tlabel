"""
Tests for tlabel CLI tool

v0.16.0 — validate, list, info, version commands
"""

import pytest
import json
import tempfile
from pathlib import Path

from tlabel.cli import (
    validate_tlabel_file, TLABEL_V2_DIMENSIONS,
    ValidationResult, cmd_list, cmd_version, cmd_info,
)


class TestDimensions:
    def test_22_dimensions(self):
        assert len(TLABEL_V2_DIMENSIONS) == 22

    def test_core_dims_present(self):
        assert "contact" in TLABEL_V2_DIMENSIONS
        assert "deformation_magnitude" in TLABEL_V2_DIMENSIONS
        assert "slip_event" in TLABEL_V2_DIMENSIONS


class TestValidationResult:
    def test_error_repr(self):
        r = ValidationResult("error", "missing field", "frames[0].tlabel_v2")
        s = repr(r)
        assert "❌" in s
        assert "frames[0].tlabel_v2" in s

    def test_warning_repr(self):
        r = ValidationResult("warning", "low coverage")
        s = repr(r)
        assert "⚠️" in s


class TestValidateJSON:
    def test_valid_file(self, tmp_path):
        data = {
            "schema_version": "0.16.0",
            "format": "tlabel_v2",
            "sensor": {"type": "test"},
            "capabilities": {"contact": True, "deformation_magnitude": True},
            "frames": [
                {
                    "frame_idx": 0,
                    "timestamp_s": 0.0,
                    "tlabel_v2": {
                        "contact": 1.0,
                        "deformation_magnitude": 0.5,
                        "slip_event": 0.0,
                    }
                }
            ]
        }
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))

        results = validate_tlabel_file(str(f))
        errors = [r for r in results if r.level == "error"]
        assert len(errors) == 0

    def test_missing_frames(self, tmp_path):
        data = {"schema_version": "0.16.0", "format": "tlabel_v2"}
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(data))

        results = validate_tlabel_file(str(f))
        errors = [r for r in results if r.level == "error"]
        assert any("frames" in r.message for r in errors)

    def test_missing_tlabel_v2_in_frame(self, tmp_path):
        data = {
            "schema_version": "0.16.0",
            "format": "tlabel_v2",
            "frames": [{"frame_idx": 0, "timestamp_s": 0.0}]
        }
        f = tmp_path / "bad2.json"
        f.write_text(json.dumps(data))

        results = validate_tlabel_file(str(f))
        errors = [r for r in results if r.level == "error"]
        assert any("tlabel_v2" in r.message for r in errors)

    def test_nonexistent_file(self):
        results = validate_tlabel_file("/nonexistent/path.json")
        errors = [r for r in results if r.level == "error"]
        assert len(errors) == 1
        assert "不存在" in errors[0].message

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "broken.json"
        f.write_text("{not valid json}")

        results = validate_tlabel_file(str(f))
        errors = [r for r in results if r.level == "error"]
        assert any("JSON" in r.message for r in errors)


class TestValidateDirectory:
    def test_directory_validation(self, tmp_path):
        # Create a simple directory structure
        (tmp_path / "meta").mkdir()
        (tmp_path / "meta" / "info.json").write_text("{}")
        
        results = validate_tlabel_file(str(tmp_path))
        infos = [r for r in results if r.level == "info"]
        assert any("目录" in r.message for r in infos)


class TestCLICommands:
    def test_version(self):
        """Version command should print without error"""
        class Args:
            pass
        result = cmd_version(Args())
        assert result == 0

    def test_list(self, capsys):
        """List command should output adapter info"""
        class Args:
            pass
        result = cmd_list(Args())
        captured = capsys.readouterr()
        assert "适配器" in captured.out
        assert result == 0

    def test_info_existing(self, capsys):
        """Info for existing adapter should show details"""
        class Args:
            name = "gelsight"
        result = cmd_info(Args())
        captured = capsys.readouterr()
        assert "gelsight" in captured.out
        assert result == 0

    def test_info_nonexistent(self, capsys):
        """Info for non-existent adapter should return error code"""
        class Args:
            name = "nonexistent_sensor_xyz"
        result = cmd_info(Args())
        assert result == 1
