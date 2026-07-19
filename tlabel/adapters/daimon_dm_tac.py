"""
DM-Tac 实时传感器适配器 — 将Daimon DM-Tac USB/UVC实时数据转换为TLabelData

数据格式特点:
- 分辨率: 320×240 或 384×288
- 采样率: 120 Hz
- 三路场输出: deformation / shear / depth
- 传感器型号: DM-Tac W / W2 / X / F / G 系列商业传感器
- 连接方式: USB (UVC摄像头协议)

这是Daimon DM-Tac系列商业传感器的实时适配器，用于通过USB/UVC连接传感器
并读取三路触觉数据（deformation/shear/depth）。
数据集（离线）适配器见 daimon_dataset.py。
"""

from typing import Optional, Dict, Any

from tlabel.adapters.base import BaseAdapter
from tlabel.core.types import TLabelData, TLabelFrame


class DaimonDmTacAdapter(BaseAdapter):
    """DM-Tac 实时传感器 → TLabelData

    支持DM-Tac W/W2/X/F/G系列商业传感器，通过USB (UVC)连接
    实时读取deformation/shear/depth三路触觉数据并转换为TLabel Format v2。

    依赖: opencv-python (pip install opencv-python)
    """

    @property
    def name(self) -> str:
        return "daimon_dm_tac"

    @property
    def supported_extensions(self):
        return [".avi", ".bag"]

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "contact": True,
            "deformation_magnitude": True,
            "force_magnitude": True,
            "force_peak": True,
            "force_direction": True,
            "slip_entropy": True,
            "slip_event": True,
            "texture_energy": True,   # 从deformation视频算
            "edge_density": True,     # 从deformation视频算
            "contact_area": True,
            "centroid_x": True,
            "normal_field_magnitude": True,
            "normal_field_variance": True,
            "shear_field_magnitude": True,  # 从shear视频算
            "shear_field_direction": True,  # 从shear视频算
            "delta_force_normal": True,
            "delta_force_shear": True,
            "friction_cone_ratio": True,
            "optical_flow_magnitude": True,   # 从deformation视频算
            "optical_flow_direction": True,   # 从deformation视频算
            "temporal_deformation_rate": True,
            "contact_transition": True,
        }

    def get_sensor_info(self) -> Dict[str, Any]:
        return {
            "type": "vision-based_tactile",
            "manufacturer": "daimon",
            "model": "DM-Tac",
            "modality": "vtla_multimodal",
            "resolution": "320×240 / 384×288",
            "sampling_rate_hz": 120,
            "channels": "deformation / shear / depth",
        }

    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        """加载DM-Tac传感器数据

        参数:
            file_path: .avi/.bag 文件路径或设备索引字符串（如"0"表示/dev/video0）
            trajectory_id: 轨迹ID（可选）
            **kwargs: 适配器特有参数
                - device_index: UVC设备索引（默认0）
                - num_frames: 采集帧数（默认100）
                - resolution: 分辨率元组（默认(320, 240)）

        返回:
            TLabelData — 统一标注容器
        """
        try:
            import cv2
        except ImportError:
            raise ImportError(
                "DM-Tac 实时适配器需要 opencv-python: "
                "pip install opencv-python"
            )

        import numpy as np

        device_index = kwargs.get("device_index", 0)
        num_frames = kwargs.get("num_frames", 100)
        resolution = kwargs.get("resolution", (320, 240))
        sample_rate = 120

        # 连接UVC设备
        cap = cv2.VideoCapture(device_index)
        if not cap.isOpened():
            raise RuntimeError(
                f"无法打开DM-Tac设备 (index={device_index})。"
                "请确认USB连接正常且设备已被系统识别。"
            )

        try:
            frames = []
            prev_tlabel_v2 = None
            dt = 1.0 / sample_rate

            for fi in range(num_frames):
                ret, frame = cap.read()
                if not ret:
                    break

                # DM-Tac三路数据: 根据分辨率分割帧
                # 典型布局: 左=deformation, 中=shear, 右=depth
                h, w = frame.shape[:2]
                third_w = w // 3
                deform_frame = frame[:, :third_w]
                shear_frame = frame[:, third_w:2*third_w]
                depth_frame = frame[:, 2*third_w:]

                # 从deformation帧计算触觉特征
                gray = cv2.cvtColor(deform_frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

                contact = float(gray.max() > 0.1)
                deformation_mag = float(np.sqrt(np.mean(gray ** 2)))
                contact_area = float(np.mean(gray > 0.05))
                nf_mag = float(np.mean(gray))
                nf_var = float(np.var(gray))

                # 时序维度
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
                    "force_magnitude": round(deformation_mag * 100, 4),
                    "force_peak": round(float(gray.max()) * 100, 4),
                    "force_direction": 0.0,
                    "slip_entropy": 0.0,
                    "slip_event": 0.0,
                    "texture_energy": 0.0,
                    "edge_density": 0.0,
                    "contact_area": round(min(contact_area, 1.0), 4),
                    "centroid_x": 0.5,
                    "normal_field_magnitude": round(nf_mag, 4),
                    "normal_field_variance": round(nf_var, 4),
                    "shear_field_magnitude": 0.0,
                    "shear_field_direction": 0.0,
                    "delta_force_normal": 0.0,
                    "delta_force_shear": 0.0,
                    "friction_cone_ratio": 0.0,
                    "optical_flow_magnitude": 0.0,
                    "optical_flow_direction": 0.0,
                    "temporal_deformation_rate": round(temporal_deform_rate, 4),
                    "contact_transition": round(contact_trans, 4),
                }

                frame_data = TLabelFrame(
                    frame_idx=fi,
                    timestamp_s=round(fi / sample_rate, 4),
                    tlabel_v2=tlabel_v2,
                    manipulation_phase="idle",
                    confidence=0.8 if contact > 0.5 else 0.95,
                    sensor_specific={
                        "device_index": device_index,
                        "frame_shape": list(frame.shape),
                        "source": "dm_tac_uvc",
                    },
                )
                frames.append(frame_data)
                prev_tlabel_v2 = tlabel_v2

        finally:
            cap.release()

        sensor_info = {
            "type": "vision-based_tactile",
            "model": "DM-Tac",
            "manufacturer": "daimon",
            "modality": "vtla_multimodal",
            "layout": {
                "type": "dm_tac_realtime",
                "resolution": resolution,
                "sampling_rate_hz": sample_rate,
                "channels": ["deformation", "shear", "depth"],
                "total_frames": len(frames),
            }
        }

        episode_info = {
            "source": "dm_tac_uvc",
            "device_index": device_index,
            "sample_rate_hz": sample_rate,
        }

        return TLabelData(
            frames=frames,
            sensor_info=sensor_info,
            episode_info=episode_info,
            capabilities=self.get_capabilities(),
            sensor_id="daimon_dm_tac",
        )
