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
AVAILABLE_SENSORS = ["gelsight", "digit", "paxini", "daimon", "touchd", "gelsight_images"]


def _generate_synthetic_tactile_images(num_frames: int = 10) -> list:
    """生成合成触觉图像（用于demo演示）"""
    import numpy as np
    
    images = []
    for i in range(num_frames):
        # 创建320x240灰度图像
        img = np.zeros((240, 320), dtype=np.uint8)
        
        # 添加高斯噪声模拟传感器噪声
        noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # 根据帧阶段添加不同的接触区域
        phase = i / num_frames
        
        if phase < 0.3:  # approach
            # 小圆形接触区域，逐渐增大
            radius = int(20 + phase * 50)
            cv2 = None
            try:
                import cv2
                cv2.circle(img, (160, 120), radius, 180, -1)
            except:
                pass
        elif phase < 0.7:  # contact
            # 大圆形接触区域
            try:
                import cv2
                cv2.circle(img, (160, 120), 60, 200, -1)
            except:
                pass
        else:  # slip
            # 接触区域偏移，模拟滑动
            try:
                import cv2
                offset_x = int((phase - 0.7) * 100)
                cv2.circle(img, (160 + offset_x, 120), 50, 180, -1)
            except:
                pass
        
        images.append(img)
    
    return images


def demo(sensor: Optional[str] = None, **kwargs) -> TLabelData:
    """
    加载内置Demo数据集，快速体验TLabel标注面板

    参数:
        sensor: 传感器类型，可选 "gelsight" / "digit" / "paxini" / "daimon" / "touchd" / "gelsight_images"
                不传则默认加载 gelsight demo
                "gelsight_images" 会加载带触觉图像的demo数据

    返回:
        TLabelData — 可直接 review() / export()

    用法:
        import tlabel
        data = tlabel.demo()              # 默认GelSight demo
        data = tlabel.demo('digit')       # DIGIT demo
        data = tlabel.demo('touchd')      # ToucHD-Force demo
        data = tlabel.demo('gelsight_images')  # 带触觉图像的GelSight demo
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

    # 如果是gelsight_images，生成合成图像
    synthetic_images = None
    if sensor == "gelsight_images":
        try:
            num_frames = len(raw.get("frames", []))
            synthetic_images = _generate_synthetic_tactile_images(num_frames)
        except Exception:
            pass

    frames = []
    for idx, fd in enumerate(raw.get("frames", [])):
        # 如果有合成图像，使用合成图像
        image_data = None
        if synthetic_images and idx < len(synthetic_images):
            image_data = synthetic_images[idx]
        
        frame = TLabelFrame(
            frame_idx=fd["frame_idx"],
            timestamp_s=fd["timestamp_s"],
            tlabel_v2=fd["tlabel_v2"],
            manipulation_phase=fd.get("manipulation_phase", "idle"),
            confidence=fd.get("confidence", 1.0),
            sensor_specific=fd.get("sensor_specific"),
            image=image_data,  # v0.12: 支持图像数据
            image_path=fd.get("image_path"),  # v0.12: 支持图像路径
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
