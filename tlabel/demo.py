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
AVAILABLE_SENSORS = [
    "gelsight", "digit", "paxini", "daimon", "touchd",
    "gelsight_images", "primitives_demo",
    "gelsight_force_demo",   # v0.14: 视触觉→力推断→Primitive标注
    "tactile_events_demo",   # v0.14: 触觉事件标注系统
    "paxini_gen3",           # v0.14: PaXini GEN3 实时传感器
    "daimon_dm_tac",         # v0.14: DM-Tac 实时传感器
]



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
        sensor: 传感器类型，可选:
            "gelsight" / "digit" / "paxini" / "daimon" / "touchd" — 基础传感器demo
            "gelsight_images" — 带触觉图像的GelSight demo
            "primitives_demo" — Motor Primitive 标注 demo (v0.13)
            "gelsight_force_demo" — 视触觉→力推断→Primitive标注 (v0.14)
            "tactile_events_demo" — 触觉事件标注系统 (v0.14)
            "paxini_gen3" — PaXini GEN3 实时传感器 demo (v0.14)
            "daimon_dm_tac" — DM-Tac 实时传感器 demo (v0.14)
            不传则默认加载 gelsight demo


    返回:
        TLabelData — 可直接 review() / export()

    用法:
        import tlabel
        data = tlabel.demo()              # 默认GelSight demo
        data = tlabel.demo('digit')       # DIGIT demo
        data = tlabel.demo('touchd')      # ToucHD-Force demo
        data = tlabel.demo('gelsight_images')  # 带触觉图像的GelSight demo
        data = tlabel.demo('primitives_demo')  # Motor Primitive 标注 demo
        data = tlabel.demo('gelsight_force_demo')  # 力推断 demo (v0.14)
        data = tlabel.demo('tactile_events_demo')  # 事件检测 demo (v0.14)

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
    # v0.14: 动态demos复用gelsight基础数据
    if not demo_file.exists() and sensor in ("gelsight_force_demo", "tactile_events_demo"):
        demo_file = _DEMO_DIR / "demo_gelsight.json"
    # v0.14: paxini_gen3 / daimon_dm_tac 没有预设JSON，生成随机帧
    if not demo_file.exists() and sensor in ("paxini_gen3", "daimon_dm_tac"):
        return _build_realtime_sensor_demo(sensor)
    if not demo_file.exists():
        raise FileNotFoundError(f"Demo数据文件缺失: {demo_file}")

    # 直接从TLabel Format JSON加载，不走适配器
    import json
    with open(demo_file, "r", encoding="utf-8") as f:
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

    # v0.13: 加载 primitive_annotations
    if "primitive_annotations" in raw:
        from tlabel.core.primitive import PrimitiveAnnotation
        for pa_dict in raw["primitive_annotations"]:
            try:
                pa = PrimitiveAnnotation(
                    name=pa_dict["primitive_name"],
                    start=pa_dict["start_frame"],
                    end=pa_dict["end_frame"],
                    confidence=pa_dict.get("confidence", 1.0),
                    source=pa_dict.get("source", "manual"),
                )
                data.primitive_annotations.append(pa)
            except (ValueError, KeyError):
                pass

    # v0.14: 加载 tactile_events
    if "tactile_events" in raw:
        from tlabel.core.events import TactileEvent
        for ev_dict in raw["tactile_events"]:
            try:
                te = TactileEvent.from_dict(ev_dict)
                data.tactile_events.append(te)
            except (ValueError, KeyError):
                pass

    # v0.14: 动态生成 demos（无预设JSON文件）
    if sensor == "gelsight_force_demo":
        data = _build_gelsight_force_demo(data)
    elif sensor == "tactile_events_demo":
        data = _build_tactile_events_demo(data)


    return data


def list_demos() -> List[str]:
    """列出所有可用的Demo传感器类型"""
    return AVAILABLE_SENSORS.copy()


# ============================================================
# v0.14.0: 动态 Demo 构建器
# ============================================================

def _build_gelsight_force_demo(data: TLabelData) -> TLabelData:
    """
    构建GelSight力推断Demo

    模拟一个只有GelSight图像数据（无力/力矩传感器）的场景：
    1. 将原始force_magnitude清零（模拟无F/T传感器）
    2. 保留deformation_magnitude数据
    3. 调用auto_force_estimate()推断力
    4. 调用predict_primitives()展示完整流程
    """
    from tlabel.predict.force_estimator import auto_force_estimate
    from tlabel.predict.engine import PredictEngine

    # 步骤1: 清零force_magnitude（模拟无力传感器）
    for frame in data.frames:
        frame.tlabel_v2["force_magnitude"] = 0.0
        frame.tlabel_v2["delta_force_normal"] = 0.0
        frame.tlabel_v2["delta_force_shear"] = 0.0
        frame.tlabel_v2["normal_field_magnitude"] = 0.0
        frame.tlabel_v2["normal_field_variance"] = 0.0
        frame.tlabel_v2["shear_field_magnitude"] = 0.0

    # 步骤2: 设置传感器类型信息
    data.sensor_info = {
        "type": "gelsight_mini",
        "model": "GelSight Mini (No F/T Sensor)",
        "resolution": "240x320",
    }

    # 步骤3: 用推断的力进行primitive标注
    # predict_primitives内部会自动检测力缺失并调用force_estimator
    engine = PredictEngine()
    annotations = engine.predict_primitives(data)

    # 应用primitive标注
    from tlabel.core.primitive import PrimitiveAnnotation
    for ann in annotations:
        try:
            # v0.14: 映射 estimated source
            source = ann.get('source', 'ai_predicted')
            if source == 'ai_predicted_estimated':
                source = 'ai_predicted'
            pa = PrimitiveAnnotation(
                name=ann['primitive_name'],
                start=ann['start_frame'],
                end=ann['end_frame'],
                confidence=ann['confidence'],
                source=source,
            )
            data.primitive_annotations.append(pa)
        except ValueError:
            pass

    # 更新episode信息
    data.episode_info["description"] = (
        "GelSight力推断Demo — 模拟无F/T传感器场景，"
        "通过deformation_magnitude + 弹性体刚度推断力，"
        "再基于推断力进行Motor Primitive标注"
    )

    return data


def _build_tactile_events_demo(data: TLabelData) -> TLabelData:
    """
    构建触觉事件标注Demo

    展示自动检测的6种触觉事件:
    - contact_onset / contact_loss: 接触开始/丢失
    - slip: 滑移事件
    - force_spike: 力值突变
    - deformation_anomaly: 形变异常
    - stable_grip: 稳定抓握
    """
    from tlabel.predict.engine import PredictEngine

    engine = PredictEngine()

    # 自动检测事件
    count = engine.apply_events(data, min_confidence=0.5)

    # 更新episode信息
    event_summary = {}
    for ev in data.tactile_events:
        t = ev.event_type
        event_summary[t] = event_summary.get(t, 0) + 1

    data.episode_info["description"] = (
        "触觉事件标注Demo — 自动检测6种关键事件: "
        f"contact_onset/contact_loss/slip/force_spike/"
        f"deformation_anomaly/stable_grip。"
        f"共检测到 {count} 个事件"
    )
    data.episode_info["event_summary"] = event_summary

    return data


def _build_realtime_sensor_demo(sensor: str) -> TLabelData:
    """
    构建实时传感器Demo（paxini_gen3 / daimon_dm_tac）

    由于这些传感器没有预设JSON文件，生成随机帧数据用于演示。
    """
    import random

    num_frames = 50
    is_paxini = sensor == "paxini_gen3"

    frames = []
    prev_tlabel_v2 = None
    sample_rate = 100 if is_paxini else 120
    dt = 1.0 / sample_rate

    # 模拟一段接触序列: idle → contact → slip → stable → release
    for fi in range(num_frames):
        phase_frac = fi / num_frames
        if phase_frac < 0.2:
            contact = 0.0
            force_mag = 0.0
            slip = 0.0
            phase = "idle"
        elif phase_frac < 0.4:
            contact = 1.0
            force_mag = random.uniform(0.3, 0.7)
            slip = 0.0
            phase = "initial_contact"
        elif phase_frac < 0.6:
            contact = 1.0
            force_mag = random.uniform(0.5, 0.9)
            slip = random.uniform(0.5, 1.0) if random.random() > 0.5 else 0.0
            phase = "slip" if slip > 0.5 else "stable_contact"
        elif phase_frac < 0.8:
            contact = 1.0
            force_mag = random.uniform(0.4, 0.7)
            slip = 0.0
            phase = "stable_contact"
        else:
            contact = 0.0
            force_mag = 0.0
            slip = 0.0
            phase = "release"

        deformation_mag = force_mag * 0.8
        contact_area = contact * random.uniform(0.3, 0.7)
        nf_mag = force_mag
        nf_var = force_mag * 0.1

        temporal_deform_rate = 0.0
        if prev_tlabel_v2 is not None and dt > 0:
            prev_deform = prev_tlabel_v2.get("deformation_magnitude", 0.0)
            temporal_deform_rate = abs(deformation_mag - prev_deform) / dt

        contact_trans = 0.0
        if prev_tlabel_v2 is not None:
            prev_contact = prev_tlabel_v2.get("contact", 0.0)
            prev_area = prev_tlabel_v2.get("contact_area", 0.0)
            contact_trans = min(1.0, abs(contact - prev_contact) +
                                abs(contact_area - prev_area) * 5.0)

        tlabel_v2 = {
            "contact": contact,
            "deformation_magnitude": round(deformation_mag, 4),
            "force_magnitude": round(force_mag, 4),
            "force_peak": round(force_mag * 1.3, 4),
            "force_direction": 0.0,
            "slip_entropy": round(slip * 0.5, 4),
            "slip_event": slip,
            "texture_energy": 0.0 if is_paxini else round(random.uniform(0, 0.1), 4),
            "edge_density": 0.0 if is_paxini else round(random.uniform(0, 0.1), 4),
            "contact_area": round(min(contact_area, 1.0), 4),
            "centroid_x": 0.5,
            "normal_field_magnitude": round(nf_mag, 4),
            "normal_field_variance": round(nf_var, 4),
            "shear_field_magnitude": 0.0 if is_paxini else round(slip * 0.3, 4),
            "shear_field_direction": 0.0 if is_paxini else round(random.uniform(0, 360), 2),
            "delta_force_normal": round(abs(force_mag - (prev_tlabel_v2.get("force_magnitude", 0.0) if prev_tlabel_v2 else 0.0)), 4),
            "delta_force_shear": 0.0 if is_paxini else round(slip * 0.1, 4),
            "friction_cone_ratio": 0.0 if is_paxini else round(random.uniform(0, 0.5), 4),
            "optical_flow_magnitude": 0.0,
            "optical_flow_direction": 0.0,
            "temporal_deformation_rate": round(temporal_deform_rate, 4),
            "contact_transition": round(contact_trans, 4),
        }

        frame = TLabelFrame(
            frame_idx=fi,
            timestamp_s=round(fi / sample_rate, 4),
            tlabel_v2=tlabel_v2,
            manipulation_phase=phase,
            confidence=0.8 if contact > 0.5 else 0.95,
            sensor_specific={"demo": True, "source": sensor},
        )
        frames.append(frame)
        prev_tlabel_v2 = tlabel_v2

    if is_paxini:
        sensor_info = {
            "type": "distributed_taxel_array",
            "model": "GEN3",
            "manufacturer": "paxini",
            "modality": "pressure_array",
        }
        sensor_id = "paxini_gen3"
        caps = {
            "contact": True, "deformation_magnitude": True,
            "force_magnitude": True, "force_peak": True,
            "force_direction": False, "slip_entropy": True,
            "slip_event": True, "texture_energy": False,
            "edge_density": False, "contact_area": True,
            "centroid_x": True, "normal_field_magnitude": True,
            "normal_field_variance": True, "shear_field_magnitude": False,
            "shear_field_direction": False, "delta_force_normal": True,
            "delta_force_shear": False, "friction_cone_ratio": False,
            "optical_flow_magnitude": False, "optical_flow_direction": False,
            "temporal_deformation_rate": True, "contact_transition": True,
        }
    else:
        sensor_info = {
            "type": "vision-based_tactile",
            "model": "DM-Tac",
            "manufacturer": "daimon",
            "modality": "vtla_multimodal",
        }
        sensor_id = "daimon_dm_tac"
        caps = {
            "contact": True, "deformation_magnitude": True,
            "force_magnitude": True, "force_peak": True,
            "force_direction": True, "slip_entropy": True,
            "slip_event": True, "texture_energy": True,
            "edge_density": True, "contact_area": True,
            "centroid_x": True, "normal_field_magnitude": True,
            "normal_field_variance": True, "shear_field_magnitude": True,
            "shear_field_direction": True, "delta_force_normal": True,
            "delta_force_shear": True, "friction_cone_ratio": True,
            "optical_flow_magnitude": True, "optical_flow_direction": True,
            "temporal_deformation_rate": True, "contact_transition": True,
        }

    return TLabelData(
        frames=frames,
        sensor_info=sensor_info,
        episode_info={"source": f"{sensor}_demo", "description": f"{sensor} 合成Demo数据"},
        capabilities=caps,
        sensor_id=sensor_id,
    )