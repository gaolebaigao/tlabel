#!/usr/bin/env python3
"""
v0.18 #3: detect_image_shape() 单元测试

覆盖:
  - DataAdapterBase / SensorAdapterBase 基类默认返回 None
  - GelSightAdapter: DIGIT (120,160,3) / GelSight Mini (240,320,3)
  - PaxiniGen3Adapter: GEN3-1 (8,8,1)
  - ToucHDAdapter: 从数据目录读取 / 无文件返回 None
  - VTouchAdapter: 无文件返回 None
  - LeRobot converter: detect_image_shape_for_lerobot() 工具函数
  - tlabel_to_lerobot: image_shape / adapter 参数集成
"""

import sys
import os
import json
import tempfile
import traceback
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# 确保 tlabel 在 sys.path 上
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ============================================================================
# 测试结果收集
# ============================================================================

test_results = {}
issues_found = []


def record_test(test_name: str, passed: bool, details: str):
    """记录测试结果"""
    test_results[test_name] = {"passed": passed, "details": details}
    status = "✅" if passed else "❌"
    print(f"  {status} {test_name}: {details}")
    if not passed:
        issues_found.append(f"{test_name}: {details}")


# ============================================================================
# Test 1: 基类默认行为
# ============================================================================

def test_base_class_defaults():
    """测试基类 detect_image_shape() 默认返回 None"""
    print("\n[Test 1] 基类默认行为")

    from tlabel.adapters.base import DataAdapterBase, SensorAdapterBase

    # 基类的 detect_image_shape 是非抽象方法，默认返回 None
    # 需要创建具体子类来测试
    class MinimalDataAdapter(DataAdapterBase):
        @property
        def name(self):
            return "test_data"

        @property
        def supported_extensions(self):
            return [".txt"]

        def extract_schema(self, raw):
            return None

        def load(self, file_path, **kwargs):
            return None

        def get_capabilities(self):
            return {}

        def get_sensor_info(self):
            return {}

    class MinimalSensorAdapter(SensorAdapterBase):
        @property
        def name(self):
            return "test_sensor"

        def extract_schema(self, raw):
            return None

        def load(self, file_path, **kwargs):
            return None

        def get_capabilities(self):
            return {}

        def get_sensor_info(self):
            return {}

        def connect(self, device_id="auto", **kwargs):
            return True

        def disconnect(self):
            pass

        def is_connected(self):
            return False

        def stream_frames(self, num_frames=-1, **kwargs):
            return iter([])

    # 测试 DataAdapterBase 子类
    da = MinimalDataAdapter()
    result = da.detect_image_shape()
    record_test("DataAdapterBase default",
                result is None,
                f"Expected None, got {result}")

    # 测试 SensorAdapterBase 子类
    sa = MinimalSensorAdapter()
    result = sa.detect_image_shape()
    record_test("SensorAdapterBase default",
                result is None,
                f"Expected None, got {result}")

    # 测试带 file_path 参数
    result = sa.detect_image_shape(file_path="/nonexistent/path")
    record_test("SensorAdapterBase with file_path",
                result is None,
                f"Expected None, got {result}")


# ============================================================================
# Test 2: GelSight 适配器
# ============================================================================

def test_gelsight_detect():
    """测试 GelSightAdapter.detect_image_shape()"""
    print("\n[Test 2] GelSight 适配器")

    from tlabel.adapters.gelsight import GelSightAdapter

    adapter = GelSightAdapter()

    # 无参数：默认返回 GelSight Mini 分辨率
    shape = adapter.detect_image_shape()
    record_test("GelSight default shape",
                shape == (240, 320, 3),
                f"Expected (240, 320, 3), got {shape}")

    # 从路径推断 DIGIT
    shape = adapter.detect_image_shape(file_path="/data/digit_force/test.pkl")
    record_test("GelSight DIGIT from path",
                shape == (120, 160, 3),
                f"Expected (120, 160, 3), got {shape}")

    # 从路径推断 GelSight
    shape = adapter.detect_image_shape(file_path="/data/gelsight_data/test.pkl")
    record_test("GelSight Mini from path",
                shape == (240, 320, 3),
                f"Expected (240, 320, 3), got {shape}")

    # 不存在的路径，应回退到默认
    shape = adapter.detect_image_shape(file_path="/nonexistent/data.pkl")
    record_test("GelSight nonexistent path fallback",
                shape == (240, 320, 3),
                f"Expected (240, 320, 3), got {shape}")


# ============================================================================
# Test 3: PaXini GEN3 适配器
# ============================================================================

def test_paxini_detect():
    """测试 PaxiniGen3Adapter.detect_image_shape()"""
    print("\n[Test 3] PaXini GEN3 适配器")

    from tlabel.adapters.paxini_gen3 import PaxiniGen3Adapter

    adapter = PaxiniGen3Adapter()

    # 未连接、无文件：默认返回 GEN3-1 指尖 (8, 8, 1)
    shape = adapter.detect_image_shape()
    record_test("PaXini default shape",
                shape == (8, 8, 1),
                f"Expected (8, 8, 1), got {shape}")

    # 不存在文件：应回退到默认
    shape = adapter.detect_image_shape(file_path="/nonexistent/test.paxini")
    record_test("PaXini nonexistent file fallback",
                shape == (8, 8, 1),
                f"Expected (8, 8, 1), got {shape}")


# ============================================================================
# Test 4: ToucHD 适配器
# ============================================================================

def test_touchd_detect():
    """测试 ToucHDAdapter.detect_image_shape()"""
    print("\n[Test 4] ToucHD 适配器")

    from tlabel.adapters.touchd import ToucHDAdapter

    adapter = ToucHDAdapter()

    # 无文件路径：返回 None
    shape = adapter.detect_image_shape()
    record_test("ToucHD no path",
                shape is None,
                f"Expected None, got {shape}")

    # 不存在路径：返回 None
    shape = adapter.detect_image_shape(file_path="/nonexistent/ToucHD-Force/")
    record_test("ToucHD nonexistent path",
                shape is None,
                f"Expected None, got {shape}")


# ============================================================================
# Test 5: VTouch 适配器
# ============================================================================

def test_vtouch_detect():
    """测试 VTouchAdapter.detect_image_shape()"""
    print("\n[Test 5] VTouch 适配器")

    from tlabel.adapters.vtouch import VTouchAdapter

    adapter = VTouchAdapter()

    # 无文件路径：返回 None
    shape = adapter.detect_image_shape()
    record_test("VTouch no path",
                shape is None,
                f"Expected None, got {shape}")

    # 不存在路径：返回 None
    shape = adapter.detect_image_shape(file_path="/nonexistent/test.h5")
    record_test("VTouch nonexistent path",
                shape is None,
                f"Expected None, got {shape}")


# ============================================================================
# Test 6: LeRobot converter - detect_image_shape_for_lerobot()
# ============================================================================

def test_lerobot_detect():
    """测试 detect_image_shape_for_lerobot() 工具函数"""
    print("\n[Test 6] LeRobot converter detect_image_shape_for_lerobot()")

    try:
        from tlabel.converters.lerobot import detect_image_shape_for_lerobot
    except ImportError:
        record_test("LeRobot import", False, "pyarrow not installed, skipping")
        return

    # 1. 从 adapter 获取
    mock_adapter = MagicMock()
    mock_adapter.detect_image_shape.return_value = (120, 160, 3)

    with tempfile.TemporaryDirectory() as tmpdir:
        shape = detect_image_shape_for_lerobot(tmpdir, adapter=mock_adapter)
        record_test("detect from adapter",
                    shape == (120, 160, 3),
                    f"Expected (120, 160, 3), got {shape}")

    # 2. 从 meta/info.json 获取
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_dir = Path(tmpdir) / "meta"
        meta_dir.mkdir()
        meta = {
            "features": {
                "observation.tactile_image": {
                    "dtype": "uint8",
                    "shape": [240, 320, 3],
                }
            }
        }
        with open(meta_dir / "info.json", "w") as f:
            json.dump(meta, f)

        shape = detect_image_shape_for_lerobot(tmpdir)
        record_test("detect from meta/info.json",
                    shape == (240, 320, 3),
                    f"Expected (240, 320, 3), got {shape}")

    # 3. 无数据源：返回 None
    with tempfile.TemporaryDirectory() as tmpdir:
        shape = detect_image_shape_for_lerobot(tmpdir)
        record_test("detect no data",
                    shape is None,
                    f"Expected None, got {shape}")


# ============================================================================
# Test 7: tlabel_to_lerobot 集成 image_shape / adapter
# ============================================================================

def test_tlabel_to_lerobot_image_shape():
    """测试 tlabel_to_lerobot() 的 image_shape 和 adapter 参数"""
    print("\n[Test 7] tlabel_to_lerobot image_shape 集成")

    try:
        import pyarrow
        import pyarrow.parquet as pq
    except ImportError:
        record_test("pyarrow import", False, "pyarrow not installed, skipping")
        return

    from tlabel.converters.lerobot import tlabel_to_lerobot

    with tempfile.TemporaryDirectory() as tmpdir:
        # 准备一个最小的 LeRobot 目录
        lerobot_dir = Path(tmpdir) / "lerobot_env"
        data_dir = lerobot_dir / "data"
        meta_dir = lerobot_dir / "meta"
        data_dir.mkdir(parents=True)
        meta_dir.mkdir(parents=True)

        # 创建最小的 parquet 文件（2帧）
        import pyarrow as pa
        data = {
            "timestamp": [0.0, 0.033],
            "observation.tactile": [[0.1, 0.2], [0.3, 0.4]],
        }
        table = pa.table(data)
        pq.write_table(table, data_dir / "chunk-0000.parquet")

        # 创建 meta/info.json
        meta = {"features": {"observation.tactile": {"dtype": "float32", "shape": [2]}}}
        with open(meta_dir / "info.json", "w") as f:
            json.dump(meta, f)

        # 创建 TLabel JSON
        tlabel_json = {
            "feature_names_v2": ["contact", "force_magnitude"],
            "frames": [
                {"schema_v2": {"contact": 1.0, "force_magnitude": 0.5}},
                {"schema_v2": {"contact": 0.0, "force_magnitude": 0.0}},
            ]
        }
        tlabel_path = Path(tmpdir) / "tlabel_annotations.json"
        with open(tlabel_path, "w") as f:
            json.dump(tlabel_json, f)

        # 测试 7a: 手动指定 image_shape
        tlabel_to_lerobot(
            tlabel_path, lerobot_dir,
            image_shape=(120, 160, 3),
            overwrite=True,
        )
        with open(meta_dir / "info.json") as f:
            meta = json.load(f)
        has_image = "observation.tactile_image" in meta["features"]
        image_shape = meta["features"].get("observation.tactile_image", {}).get("shape")
        record_test("manual image_shape",
                    has_image and image_shape == [120, 160, 3],
                    f"has_image={has_image}, shape={image_shape}")

        # 测试 7b: 通过 adapter 自动检测
        mock_adapter = MagicMock()
        mock_adapter.detect_image_shape.return_value = (240, 320, 3)
        tlabel_to_lerobot(
            tlabel_path, lerobot_dir,
            adapter=mock_adapter,
            overwrite=True,
        )
        with open(meta_dir / "info.json") as f:
            meta = json.load(f)
        image_shape = meta["features"].get("observation.tactile_image", {}).get("shape")
        record_test("adapter image_shape",
                    image_shape == [240, 320, 3],
                    f"Expected [240, 320, 3], got {image_shape}")

        # 测试 7c: 不提供 image_shape 也不提供 adapter（使用干净的目录）
        lerobot_dir2 = Path(tmpdir) / "lerobot_env2"
        data_dir2 = lerobot_dir2 / "data"
        meta_dir2 = lerobot_dir2 / "meta"
        data_dir2.mkdir(parents=True)
        meta_dir2.mkdir(parents=True)
        table2 = pa.table(data)
        pq.write_table(table2, data_dir2 / "chunk-0000.parquet")
        meta2 = {"features": {"observation.tactile": {"dtype": "float32", "shape": [2]}}}
        with open(meta_dir2 / "info.json", "w") as f:
            json.dump(meta2, f)

        tlabel_to_lerobot(
            tlabel_path, lerobot_dir2,
            overwrite=True,
        )
        with open(meta_dir2 / "info.json") as f:
            meta2 = json.load(f)
        has_image = "observation.tactile_image" in meta2["features"]
        record_test("no image_shape no adapter",
                    not has_image,
                    f"Should not have image field, has_image={has_image}")


# ============================================================================
# Test 8: 返回值类型验证
# ============================================================================

def test_return_types():
    """测试所有 detect_image_shape() 返回类型正确"""
    print("\n[Test 8] 返回值类型验证")

    from tlabel.adapters.gelsight import GelSightAdapter
    from tlabel.adapters.paxini_gen3 import PaxiniGen3Adapter

    # GelSight 返回 tuple
    shape = GelSightAdapter().detect_image_shape()
    record_test("GelSight returns tuple",
                isinstance(shape, tuple) and len(shape) == 3,
                f"type={type(shape)}, value={shape}")

    # PaXini 返回 tuple
    shape = PaxiniGen3Adapter().detect_image_shape()
    record_test("PaXini returns tuple",
                isinstance(shape, tuple) and len(shape) == 3,
                f"type={type(shape)}, value={shape}")

    # 所有 tuple 的元素都是 int
    shape = GelSightAdapter().detect_image_shape()
    all_int = all(isinstance(x, int) for x in shape)
    record_test("GelSight tuple elements are int",
                all_int,
                f"types={[type(x) for x in shape]}")


# ============================================================================
# 主流程
# ============================================================================

def main():
    print("=" * 60)
    print("TLabel v0.18 #3: detect_image_shape() 单元测试")
    print("=" * 60)

    try:
        test_base_class_defaults()
    except Exception as e:
        record_test("Test 1 (base class)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_gelsight_detect()
    except Exception as e:
        record_test("Test 2 (gelsight)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_paxini_detect()
    except Exception as e:
        record_test("Test 3 (paxini)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_touchd_detect()
    except Exception as e:
        record_test("Test 4 (touchd)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_vtouch_detect()
    except Exception as e:
        record_test("Test 5 (vtouch)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_lerobot_detect()
    except Exception as e:
        record_test("Test 6 (lerobot detect)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_tlabel_to_lerobot_image_shape()
    except Exception as e:
        record_test("Test 7 (lerobot integration)", False, f"Exception: {e}\n{traceback.format_exc()}")

    try:
        test_return_types()
    except Exception as e:
        record_test("Test 8 (return types)", False, f"Exception: {e}\n{traceback.format_exc()}")

    # 汇总
    print("\n" + "=" * 60)
    passed = sum(1 for v in test_results.values() if v["passed"])
    failed = sum(1 for v in test_results.values() if not v["passed"])
    total = len(test_results)
    print(f"总计: {total} 项测试, {passed} 通过, {failed} 失败")

    if issues_found:
        print("\n失败项:")
        for issue in issues_found:
            print(f"  ❌ {issue}")
        sys.exit(1)
    else:
        print("\n✅ 所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
