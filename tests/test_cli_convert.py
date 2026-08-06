"""
Tests for v0.19.0-dev CLI convert commands

Tests: convert, batch-convert, list-adapters, adapter-info
"""

import pytest
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from tlabel.cli import (
    cmd_convert, cmd_batch_convert, cmd_list_adapters, cmd_adapter_info,
)
from tlabel.converters.base import (
    BaseConverter, FTP1Converter, LeRobotConverter,
    get_converter, list_converters, list_available_converters,
    CONVERTERS,
)


# =============================================================================
# Helper: resolve demo data path
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent


def _demo_path(name: str) -> Path:
    return REPO_ROOT / "tlabel" / "demo_data" / name


# =============================================================================
# Converter base tests
# =============================================================================

class TestConverterBase:
    def test_list_converters(self):
        converters = list_converters()
        assert "ftp1" in converters
        assert "lerobot" in converters

    def test_get_converter(self):
        assert get_converter("ftp1") is FTP1Converter
        assert get_converter("lerobot") is LeRobotConverter
        assert get_converter("nonexistent") is None

    def test_ftp1_available(self):
        assert isinstance(FTP1Converter.is_available(), bool)

    def test_lerobot_available(self):
        assert isinstance(LeRobotConverter.is_available(), bool)

    def test_list_available_converters(self):
        available = list_available_converters()
        assert isinstance(available, dict)

    def test_converter_names(self):
        assert FTP1Converter.name == "ftp1"
        assert LeRobotConverter.name == "lerobot"

    def test_converter_descriptions(self):
        assert "FTP-1" in FTP1Converter.description
        assert "LeRobot" in LeRobotConverter.description

    def test_required_dependencies(self):
        deps = FTP1Converter.required_dependencies()
        assert any("zarr" in d for d in deps)
        deps = LeRobotConverter.required_dependencies()
        assert any("pyarrow" in d for d in deps)


# =============================================================================
# list-adapters command tests
# =============================================================================

class TestListAdapters:
    def test_list_adapters_runs(self, capsys):
        """list-adapters should run without error"""
        result = cmd_list_adapters(SimpleNamespace())
        captured = capsys.readouterr()
        assert result == 0
        assert "TLabel 适配器列表" in captured.out
        assert "gelsight" in captured.out
        assert "paxini" in captured.out

    def test_list_adapters_shows_extensions(self, capsys):
        """list-adapters should show supported extensions"""
        cmd_list_adapters(SimpleNamespace())
        captured = capsys.readouterr()
        assert ".json" in captured.out or ".h5" in captured.out or ".pkl" in captured.out

    def test_list_adapters_shows_convert_hint(self, capsys):
        """list-adapters should show convert usage hints"""
        cmd_list_adapters(SimpleNamespace())
        captured = capsys.readouterr()
        assert "convert" in captured.out
        assert "lerobot" in captured.out
        assert "ftp1" in captured.out


# =============================================================================
# adapter-info command tests
# =============================================================================

class TestAdapterInfo:
    def test_adapter_info_gelsight(self, capsys):
        """adapter-info for gelsight should show detailed info"""
        result = cmd_adapter_info(SimpleNamespace(name="gelsight"))
        captured = capsys.readouterr()
        assert result == 0
        assert "gelsight" in captured.out
        assert "GelSightAdapter" in captured.out
        assert "合规等级" in captured.out

    def test_adapter_info_paxini(self, capsys):
        """adapter-info for paxini should show detailed info"""
        result = cmd_adapter_info(SimpleNamespace(name="paxini"))
        captured = capsys.readouterr()
        assert result == 0
        assert "paxini" in captured.out
        assert "PaxiniAdapter" in captured.out

    def test_adapter_info_nonexistent(self, capsys):
        """adapter-info for nonexistent adapter should return error"""
        result = cmd_adapter_info(SimpleNamespace(name="nonexistent_xyz"))
        captured = capsys.readouterr()
        assert result == 1
        assert "未找到" in captured.out

    def test_adapter_info_shows_capabilities(self, capsys):
        """adapter-info should show capabilities/field mapping"""
        cmd_adapter_info(SimpleNamespace(name="gelsight"))
        captured = capsys.readouterr()
        assert "能力声明" in captured.out or "字段映射" in captured.out

    def test_adapter_info_shows_supported_formats(self, capsys):
        """adapter-info should show supported file formats"""
        cmd_adapter_info(SimpleNamespace(name="gelsight"))
        captured = capsys.readouterr()
        assert ".pkl" in captured.out or "支持格式" in captured.out


# =============================================================================
# convert command tests
# =============================================================================

class TestConvert:
    def test_convert_tlabel_to_ftp1(self, capsys, tmp_path):
        """Convert tlabel JSON to FTP-1 zarr format"""
        demo = _demo_path("demo_gelsight.json")
        if not demo.exists():
            pytest.skip("Demo data not found")

        out_path = str(tmp_path / "output.zarr")
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="ftp1",
            input=str(demo),
            output=out_path,
        )
        result = cmd_convert(args)
        captured = capsys.readouterr()
        assert result == 0
        assert "✅" in captured.out
        assert Path(out_path).exists()

    def test_convert_tlabel_to_lerobot(self, capsys, tmp_path):
        """Convert tlabel JSON to LeRobot parquet format"""
        demo = _demo_path("demo_gelsight.json")
        if not demo.exists():
            pytest.skip("Demo data not found")

        out_dir = str(tmp_path / "lerobot_out")
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="lerobot",
            input=str(demo),
            output=out_dir,
        )
        result = cmd_convert(args)
        captured = capsys.readouterr()
        assert result == 0
        assert "✅" in captured.out
        assert (Path(out_dir) / "data" / "chunk-0000.parquet").exists()
        assert (Path(out_dir) / "meta" / "info.json").exists()

    def test_convert_nonexistent_input(self, capsys):
        """Convert with nonexistent input should fail gracefully"""
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="ftp1",
            input="/nonexistent/file.json",
            output="/tmp/out_test.zarr",
        )
        result = cmd_convert(args)
        captured = capsys.readouterr()
        assert result == 1
        assert "❌" in captured.out
        assert "不存在" in captured.out

    def test_convert_nonexistent_adapter(self, capsys, tmp_path):
        """Convert with nonexistent adapter should fail gracefully"""
        from tlabel.core.registry import _ensure_adapters
        _ensure_adapters()

        args = SimpleNamespace(
            from_format="nonexistent_adapter",
            to_format="ftp1",
            input=str(tmp_path / "dummy.json"),
            output=str(tmp_path / "out.zarr"),
        )
        result = cmd_convert(args)
        captured = capsys.readouterr()
        assert result == 1
        assert "❌" in captured.out


# =============================================================================
# batch-convert command tests
# =============================================================================

class TestBatchConvert:
    def test_batch_convert_tlabel_to_ftp1(self, capsys, tmp_path):
        """Batch convert multiple tlabel JSON files to FTP-1"""
        demo_files = ["demo_gelsight.json", "demo_paxini.json", "demo_digit.json"]
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        for name in demo_files:
            src = _demo_path(name)
            if src.exists():
                shutil.copy(src, input_dir / name)

        if not list(input_dir.iterdir()):
            pytest.skip("Demo data not found")

        out_dir = str(tmp_path / "output")
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="ftp1",
            input_dir=str(input_dir),
            output_dir=out_dir,
        )
        result = cmd_batch_convert(args)
        captured = capsys.readouterr()
        assert result == 0
        assert "成功" in captured.out
        zarr_files = list(Path(out_dir).glob("*.zarr"))
        assert len(zarr_files) > 0

    def test_batch_convert_empty_dir(self, capsys, tmp_path):
        """Batch convert with empty directory should report no files"""
        input_dir = tmp_path / "empty_input"
        input_dir.mkdir()
        out_dir = str(tmp_path / "output")
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="ftp1",
            input_dir=str(input_dir),
            output_dir=out_dir,
        )
        result = cmd_batch_convert(args)
        captured = capsys.readouterr()
        assert result == 0
        assert "未找到" in captured.out

    def test_batch_convert_nonexistent_dir(self, capsys):
        """Batch convert with nonexistent directory should fail"""
        args = SimpleNamespace(
            from_format="tlabel",
            to_format="ftp1",
            input_dir="/nonexistent/directory",
            output_dir="/tmp/output_test",
        )
        result = cmd_batch_convert(args)
        captured = capsys.readouterr()
        assert result == 1
        assert "❌" in captured.out


# =============================================================================
# CLI integration tests (subprocess)
# =============================================================================

class TestCLIIntegration:
    def test_cli_help_shows_all_commands(self):
        """CLI --help should list all 8 commands"""
        result = subprocess.run(
            [sys.executable, "-m", "tlabel.cli", "--help"],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        for cmd in ["validate", "list", "info", "version",
                     "convert", "batch-convert", "list-adapters", "adapter-info"]:
            assert cmd in result.stdout, f"Command '{cmd}' not in help output"

    def test_cli_convert_help(self):
        """convert --help should show usage"""
        result = subprocess.run(
            [sys.executable, "-m", "tlabel.cli", "convert", "--help"],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "--from" in result.stdout
        assert "--to" in result.stdout
        assert "--input" in result.stdout
        assert "--output" in result.stdout

    def test_cli_list_adapters(self):
        """list-adapters should run via CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "tlabel.cli", "list-adapters"],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "gelsight" in result.stdout

    def test_cli_adapter_info(self):
        """adapter-info should run via CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "tlabel.cli", "adapter-info", "gelsight"],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "gelsight" in result.stdout
        assert "GelSightAdapter" in result.stdout

    def test_cli_convert_end_to_end(self, tmp_path):
        """Full convert: tlabel -> ftp1 via CLI"""
        demo = _demo_path("demo_gelsight.json")
        if not demo.exists():
            pytest.skip("Demo data not found")

        out_path = tmp_path / "e2e_out.zarr"
        result = subprocess.run(
            [sys.executable, "-m", "tlabel.cli", "convert",
             "--from", "tlabel", "--to", "ftp1",
             "--input", str(demo),
             "--output", str(out_path)],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "✅" in result.stdout
        assert out_path.exists()
