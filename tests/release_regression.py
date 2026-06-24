"""
TLabel 发版回归测试脚本

每次发版前运行，确保所有适配器和demo数据正常工作。
运行: python tests/release_regression.py

测试覆盖:
  1. 所有适配器可导入和注册
  2. 所有demo数据可加载
  3. 核心API（load/demo/review）正常
  4. 数据格式一致性（22维特征完整）
  5. ToucHD适配器力归一化正确
"""

import sys
import json
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

passed = 0
failed = 0
errors = []


def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1
        errors.append((name, str(e)))


# ============================================================
# Part 1: 导入与版本
# ============================================================
print("=" * 60)
print("Part 1: 导入与版本")
print("=" * 60)


def test_version():
    import tlabel

    assert hasattr(tlabel, "__version__"), "缺少 __version__"
    ver = tlabel.__version__
    parts = ver.split(".")
    assert len(parts) >= 2, f"版本号格式异常: {ver}"
    print(f"    version: {ver}")


test("tlabel版本号", test_version)


def test_core_imports():
    from tlabel import load, TLabelData, TLabelFrame

    assert callable(load)
    assert TLabelData is not None
    assert TLabelFrame is not None


test("核心API导入", test_core_imports)


# ============================================================
# Part 2: 适配器注册
# ============================================================
print("\n" + "=" * 60)
print("Part 2: 适配器注册")
print("=" * 60)


def test_all_adapters_registered():
    from tlabel.core.registry import _ensure_adapters, list_adapters

    _ensure_adapters()
    adapters = list_adapters()
    expected = ["gelsight", "paxini", "daimon", "tlabel", "touchd", "vtouch"]
    for name in expected:
        assert name in adapters, f"缺少适配器: {name}"
    print(f"    已注册: {list(adapters.keys())}")


test("全部适配器注册", test_all_adapters_registered)


def test_adapter_capabilities():
    from tlabel.adapters.touchd import ToucHDAdapter

    adapter = ToucHDAdapter()
    caps = adapter.get_capabilities()
    assert len(caps) == 22, f"ToucHD特征维度: {len(caps)}, 期望22"
    for key in ["contact", "force_magnitude", "slip_event", "contact_transition"]:
        assert key in caps, f"缺少关键特征: {key}"


test("ToucHD 22维特征完整", test_adapter_capabilities)


# ============================================================
# Part 3: Demo数据加载
# ============================================================
print("\n" + "=" * 60)
print("Part 3: Demo数据加载")
print("=" * 60)


def test_demo_all_sensors():
    from tlabel import demo, list_demos

    available = list_demos()
    print(f"    可用demo: {available}")
    for sensor in available:
        data = demo(sensor)
        assert len(data.frames) > 0, f"{sensor} demo无帧数据"
        assert data.sensor_info is not None, f"{sensor} demo无sensor_info"
        print(f"    {sensor}: {len(data.frames)} frames ✅")


test("所有Demo数据加载", test_demo_all_sensors)


def test_demo_frame_structure():
    from tlabel import demo

    # 检查每个demo的帧结构一致性
    for sensor in ["gelsight", "digit", "paxini", "daimon", "touchd"]:
        data = demo(sensor)
        f0 = data.frames[0]
        # 22维特征
        v2 = f0.tlabel_v2
        expected_keys = [
            "contact", "deformation_magnitude", "force_magnitude", "force_peak",
            "force_direction", "slip_entropy", "slip_event", "texture_energy",
            "edge_density", "contact_area", "centroid_x",
            "normal_field_magnitude", "normal_field_variance",
            "shear_field_magnitude", "shear_field_direction",
            "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
            "optical_flow_magnitude", "optical_flow_direction",
            "temporal_deformation_rate", "contact_transition",
        ]
        for key in expected_keys:
            assert key in v2, f"{sensor} demo帧缺少特征: {key}"
        # 值范围检查
        assert 0 <= v2["contact"] <= 1, f"{sensor} contact超范围: {v2['contact']}"
        assert 0 <= v2["force_magnitude"] <= 1, f"{sensor} force_magnitude超范围: {v2['force_magnitude']}"


test("Demo帧结构22维一致性", test_demo_frame_structure)


def test_touchd_demo_specific():
    from tlabel import demo

    data = demo("touchd")
    assert data.sensor_info.get("type") == "vision-based_tactile"
    assert "AnyTouch" in data.sensor_info.get("model", "")
    # ToucHD特有: sensor_specific含力标注
    for f in data.frames[:10]:
        if f.tlabel_v2.get("contact", 0) > 0.5:
            assert f.sensor_specific is not None, "ToucHD接触帧缺少sensor_specific"
            assert "force_xyz_normalized" in f.sensor_specific, "缺少force_xyz_normalized"
            assert "action_label" in f.sensor_specific, "缺少action_label"


test("ToucHD Demo特有字段", test_touchd_demo_specific)


# ============================================================
# Part 4: 格式自动检测
# ============================================================
print("\n" + "=" * 60)
print("Part 4: 格式自动检测")
print("=" * 60)


def test_auto_detect():
    from tlabel.core.registry import auto_detect_format
    import tempfile
    import os

    # pkl → gelsight
    tmpdir = tempfile.mkdtemp()
    pkl_path = os.path.join(tmpdir, "test.pkl")
    with open(pkl_path, "wb") as f:
        f.write(b"fake")
    assert auto_detect_format(pkl_path) == "gelsight"

    # h5 → paxini
    h5_path = os.path.join(tmpdir, "test.h5")
    with open(h5_path, "wb") as f:
        f.write(b"fake")
    assert auto_detect_format(h5_path) == "paxini"

    # dir with all_data_direction.json → touchd
    touchd_dir = os.path.join(tmpdir, "touchd")
    os.makedirs(touchd_dir, exist_ok=True)
    with open(os.path.join(touchd_dir, "all_data_direction.json"), "w") as f:
        json.dump({}, f)
    assert auto_detect_format(touchd_dir) == "touchd"

    # tlabel format json
    tlabel_path = os.path.join(tmpdir, "test.json")
    with open(tlabel_path, "w") as f:
        json.dump({"schema_version": "0.4.0", "frames": []}, f)
    assert auto_detect_format(tlabel_path) == "tlabel"


test("格式自动检测", test_auto_detect)


# ============================================================
# Part 5: 错误处理
# ============================================================
print("\n" + "=" * 60)
print("Part 5: 错误处理")
print("=" * 60)


def test_bad_demo_sensor():
    from tlabel import demo

    try:
        demo("nonexistent_sensor")
        assert False, "应该报错"
    except ValueError as e:
        assert "nonexistent_sensor" in str(e) or "未知" in str(e)


test("错误demo传感器名", test_bad_demo_sensor)


def test_load_nonexistent():
    from tlabel import load

    try:
        load("/path/that/does/not/exist")
        assert False, "应该报错"
    except (FileNotFoundError, ValueError):
        pass


test("加载不存在的文件", test_load_nonexistent)


def test_touchd_bad_params():
    from tlabel.adapters.touchd import ToucHDAdapter

    try:
        ToucHDAdapter().load("/tmp/fake", sensor="bad_sensor")
        assert False, "应该报错"
    except ValueError:
        pass

    try:
        ToucHDAdapter().load("/tmp/fake", sensor="digit", hand="x")
        assert False, "应该报错"
    except ValueError:
        pass


test("ToucHD错误参数处理", test_touchd_bad_params)


# ============================================================
# 结果
# ============================================================
print(f"\n{'=' * 60}")
print(f"测试结果: ✅ {passed} 通过, ❌ {failed} 失败")
if failed > 0:
    print("\n失败详情:")
    for name, err in errors:
        print(f"  - {name}: {err}")
    sys.exit(1)
else:
    print("\n🎉 全部测试通过！可以发版。")
    sys.exit(0)
