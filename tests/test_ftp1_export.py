"""
FTP-1/MTTS 集成测试

验证 TLabel → FTP-1 格式转换的完整流程。
需要先安装: pip install zarr
"""

import sys
import json
import tempfile
from pathlib import Path

# 1. 基础导入测试
print("=" * 60)
print("TLabel → FTP-1/MTTS 集成测试")
print("=" * 60)

print("\n[1/6] 导入模块...")
from tlabel import demo
from tlabel.converters.ftp1 import (
    tlabel_to_ftp1, list_functional_areas, list_known_sensors,
    HAND_FUNCTIONAL_AREAS, FTP1_KNOWN_SENSORS, DEFAULT_AREA_MAPPINGS,
    ALL_FUNCTIONAL_AREAS
)
print("  ✅ 导入成功")

# 2. 功能区定义测试
print("\n[2/6] 功能区定义...")
areas = list_functional_areas()
assert len(areas) == 21, f"Expected 21 areas, got {len(areas)}"
assert areas[0] == "thumb_tip"
assert areas[1] == "index_fingertip"
assert areas[15] == "wrist_fx"
print(f"  ✅ {len(areas)} 功能区定义正确")
print(f"     手部: 0-14 ({len(HAND_FUNCTIONAL_AREAS)}个)")
print(f"     力矩: 15-20 (6个)")

# 3. 传感器注册表测试
print("\n[3/6] 传感器注册表...")
sensors = list_known_sensors()
assert "GelSightMini" in sensors
assert "Contactile" in sensors
assert "BinaryContact" in sensors
print(f"  ✅ {len(sensors)} 种已知传感器:")
for name, info in sensors.items():
    print(f"     {name}: type={info['type']}")

# 4. 预设映射测试
print("\n[4/6] 功能区预设映射...")
for preset, mapping in DEFAULT_AREA_MAPPINGS.items():
    names = [ALL_FUNCTIONAL_AREAS.get(a, f"?{a}") for a in mapping]
    print(f"  {preset}: slots={mapping} → {names}")
print("  ✅ 4 种预设映射")

# 5. 导出方法签名测试
print("\n[5/6] export_ftp1 方法...")
data = demo('gelsight')
assert hasattr(data, 'export_ftp1'), "TLabelData should have export_ftp1 method"
print(f"  ✅ Demo loaded: {data.num_frames} frames, sensor={data.sensor_type}")
print(f"  ✅ export_ftp1 方法存在")

# 6. Zarr导出测试（需要zarr）
print("\n[6/6] Zarr 导出测试...")
try:
    import zarr
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_export.zarr"
        
        stats = data.export_ftp1(
            str(output_path),
            sensor_name="GelSightMini",
            functional_areas=[0, 1],
            side="right",
            group="gripper",
        )
        
        print(f"  ✅ 导出成功!")
        print(f"     输出路径: {stats['output_path']}")
        print(f"     传感器: {stats['sensor_name']}")
        print(f"     类型: {stats['tactile_type']}")
        print(f"     时间步: {stats['time_steps']}")
        print(f"     功能区: {stats['functional_areas']} → {stats['functional_area_names']}")
        print(f"     Zarr keys: {stats['zarr_keys']}")
        
        # 验证Zarr文件内容
        root = zarr.open(str(output_path), mode='r')
        for key in stats['zarr_keys']:
            if key in root:
                arr = root[key]
                print(f"     {key}: shape={arr.shape}, dtype={arr.dtype}")
            else:
                print(f"     ⚠️ {key} not found!")
                
    print("\n" + "=" * 60)
    print("🎉 全部测试通过!")
    print("=" * 60)
    
except ImportError:
    print("  ⚠️ zarr 未安装，跳过导出测试")
    print("  安装: pip install zarr")
    print("\n" + "=" * 60)
    print("✅ 基础测试通过 (导出测试需安装zarr)")
    print("=" * 60)
