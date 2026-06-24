"""
tlabel.demo() — 一键体验内置Demo数据

无需任何文件，直接加载内置数据集，在Jupyter中弹出交互面板。
"""

from pathlib import Path
from typing import Optional, List

from tlabel.core.types import TLabelData, TLabelFrame

# 内置Demo数据目录
_DEMO_DIR = Path(__file__).parent / "demo_data"

# 可用的Demo传感器列表
AVAILABLE_SENSORS = ["gelsight", "digit", "paxini", "daimon", "touchd"]


def demo(sensor: Optional[str] = None, **kwargs) -> TLabelData:
    """
    加载内置Demo数据集，快速体验TLabel标注面板

    参数:
        sensor: 传感器类型，可选 "gelsight" / "digit" / "paxini" / "daimon" / "touchd"
                不传则默认加载 gelsight demo

    返回:
        TLabelData — 可直接 review() / export()

    用法:
        import tlabel
        data = tlabel.demo()              # 默认GelSight demo
        data = tlabel.demo('digit')       # DIGIT demo
        data = tlabel.demo('touchd')      # ToucHD-Force demo
        data.review()                     # Jupyter弹出面板
    """
    if sensor is None:
        sensor = "gelsight"

    sensor = sensor.lower().strip()
    if sensor not in AVAILABLE_SENSORS:
        raise ValueError(
            f"未知的传感器类型: '{sensor}'\n"
            f"可用选项: {AVAILABLE_SENSORS}"
        )

    demo_file = _DEMO_DIR / f"demo_{sensor}.json"
    if not demo_file.exists():
        raise FileNotFoundError(f"Demo数据文件缺失: {demo_file}")

    # 直接从TLabel Format JSON加载，不走适配器
    import json
    with open(demo_file, "r") as f:
        raw = json.load(f)

    frames = []
    for fd in raw.get("frames", []):
        frame = TLabelFrame(
            frame_idx=fd["frame_idx"],
            timestamp_s=fd["timestamp_s"],
            tlabel_v2=fd["tlabel_v2"],
            manipulation_phase=fd.get("manipulation_phase", "idle"),
            confidence=fd.get("confidence", 1.0),
            sensor_specific=fd.get("sensor_specific"),
        )
        frames.append(frame)

    data = TLabelData(
        frames=frames,
        sensor_info=raw.get("sensor", {}),
        episode_info=raw.get("episode", {}),
        capabilities=raw.get("capabilities", {}),
        schema_version=raw.get("schema_version", "0.4.0"),
    )

    return data


def list_demos() -> List[str]:
    """列出所有可用的Demo传感器类型"""
    return AVAILABLE_SENSORS.copy()
