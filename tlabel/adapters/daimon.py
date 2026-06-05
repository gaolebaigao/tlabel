"""
戴盟(Daimon)适配器 — 将Daimon-Infinity Parquet数据转换为TLabelData

Daimon-Infinity数据格式特点:
- 主数据: Parquet格式 (data/chunk-xxx/file-xxx.parquet)
- observation.state: 114维float32 (位姿+关节+触觉+IMU)
- action: 111维float32
- 触觉: 高分辨率视触觉传感器 (视频流, 640x480 RGB + 384x288 deformation/shear/depth)
- 数值触觉: finger0~finger35 (idx 67-102, 常为9930占位)
- 占位值: 9930.0 = 无效/未启用维度
- fps: 30

目录结构:
  DM-DataClaw/datasets/v1_3_usb_backups_XXXX/DEVICE_ID_lerobot_TIME/
  ├── meta/info.json          # 数据集配置
  ├── meta/stats.json         # 统计信息
  ├── meta/tasks.parquet      # 任务描述
  ├── data/chunk-000/file-000.parquet  # 主数据
  ├── videos/                 # 视频数据
  └── episodes_metadata.json  # 分集元数据

支持加载方式:
  1. 指定parquet文件路径 (自动查找同级meta/)
  2. 指定episode目录路径 (自动查找data/和meta/)
  3. 指定parquet文件 (直接加载)
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from tlabel.adapters.base import BaseAdapter
from tlabel.core.types import TLabelData, TLabelFrame

try:
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

# HACK: 占位值常量 — Daimon用9930.0表示无效维度
PLACEHOLDER = 9930.0

# observation.state 维度定义 (114维)
STATE_DIMS = {
    "left_x": 0, "left_y": 1, "left_z": 2,
    "left_qx": 3, "left_qy": 4, "left_qz": 5, "left_qw": 6,
    "right_x": 7, "right_y": 8, "right_z": 9,
    "right_qx": 10, "right_qy": 11, "right_qz": 12, "right_qw": 13,
    "head_x": 14, "head_y": 15, "head_z": 16,
    "head_qx": 17, "head_qy": 18, "head_qz": 19, "head_qw": 20,
    "left_eye_x": 21, "left_eye_y": 22, "left_eye_z": 23,
    "left_eye_qx": 24, "left_eye_qy": 25, "left_eye_qz": 26, "left_eye_qw": 27,
    "right_eye_x": 28, "right_eye_y": 29, "right_eye_z": 30,
    "right_eye_qx": 31, "right_eye_qy": 32, "right_eye_qz": 33, "right_eye_qw": 34,
    "third_x": 35, "third_y": 36, "third_z": 37,
    "third_qx": 38, "third_qy": 39, "third_qz": 40, "third_qw": 41,
    "arm_left_1": 42, "arm_left_2": 43, "arm_left_3": 44, "arm_left_4": 45,
    "arm_left_5": 46, "arm_left_6": 47, "arm_left_7": 48,
    "arm_right_1": 49, "arm_right_2": 50, "arm_right_3": 51, "arm_right_4": 52,
    "arm_right_5": 53, "arm_right_6": 54, "arm_right_7": 55,
    "head_pitch": 56, "head_yaw": 57,
    "hip_pitch": 58, "hip_yaw": 59, "knee": 60, "left_wheel": 61, "right_wheel": 62,
    "gripper": 63, "gripper_left": 64, "gripper_right": 65,
    "finger_0": 66, "finger_1": 67, "finger_2": 68, "finger_3": 69,
    "finger_4": 70, "finger_5": 71, "finger_6": 72, "finger_7": 73,
    "finger_8": 74, "finger_9": 75, "finger_10": 76, "finger_11": 77,
    "finger_12": 78, "finger_13": 79, "finger_14": 80, "finger_15": 81,
    "finger_16": 82, "finger_17": 83, "finger_18": 84, "finger_19": 85,
    "finger_20": 86, "finger_21": 87, "finger_22": 88, "finger_23": 89,
    "finger_24": 90, "finger_25": 91, "finger_26": 92, "finger_27": 93,
    "finger_28": 94, "finger_29": 95, "finger_30": 96, "finger_31": 97,
    "finger_32": 98, "finger_33": 99, "finger_34": 100, "finger_35": 101,
    "left_acc_x": 102, "left_acc_y": 103, "left_acc_z": 104,
    "left_gyro_x": 105, "left_gyro_y": 106, "left_gyro_z": 107,
    "right_acc_x": 108, "right_acc_y": 109, "right_acc_z": 110,
    "right_gyro_x": 111, "right_gyro_y": 112, "right_gyro_z": 113,
}

# 有效维度索引 (排除9930占位)
# 根据ugripper_right配置: right arm(7-13), gripper_left(65), finger(67-102?),
# right IMU(108-113)


def _is_valid(val):
    """检查值是否有效（非占位）"""
    if isinstance(val, (list, np.ndarray)):
        return not np.all(np.array(val) == PLACEHOLDER)
    return val != PLACEHOLDER


def _mask_placeholder(arr):
    """将9930占位替换为NaN"""
    result = np.array(arr, dtype=np.float64)
    result[result == PLACEHOLDER] = np.nan
    return result


def _load_info_json(parquet_path: Path) -> Dict:
    """查找并加载meta/info.json"""
    # 向上查找到包含meta/目录的父级
    current = parquet_path.parent
    for _ in range(5):
        meta_dir = current / "meta"
        if meta_dir.exists():
            info_file = meta_dir / "info.json"
            if info_file.exists():
                with open(info_file, "r") as f:
                    return json.load(f)
        current = current.parent
    return {}


def _load_tasks(parquet_path: Path) -> Dict[int, str]:
    """加载任务描述映射"""
    if not HAS_PYARROW:
        return {}
    current = parquet_path.parent
    for _ in range(5):
        tasks_file = current / "meta" / "tasks.parquet"
        if tasks_file.exists():
            try:
                table = pq.read_table(str(tasks_file))
                df = table.to_pandas()
                return dict(zip(df["task_index"], df["vlm_hybrid_task"]))
            except Exception:
                pass
        current = current.parent
    return {}


def _detect_robot_type(info: Dict) -> str:
    """从info.json检测机器人配置类型"""
    return info.get("robot_type", "unknown")


def _get_valid_state_dims(info: Dict) -> List[int]:
    """根据robot_type确定observation.state中哪些维度有效"""
    robot_type = _detect_robot_type(info)

    if robot_type == "ugripper_right":
        # 右手单夹爪配置: 右臂位姿(7-13), gripper_left(65), 右IMU(108-113)
        # 根据实际stats.json，gripper(64)也是9930
        valid = list(range(7, 14)) + [65] + list(range(108, 114))
        # finger维度可能是9930，也可能有数据
        return valid
    elif robot_type == "ugripper_left":
        valid = list(range(0, 7)) + [64] + list(range(102, 108))
        return valid
    elif robot_type == "dual_ugripper":
        valid = list(range(0, 14)) + [64, 65] + list(range(102, 114))
        return valid
    else:
        return list(range(114))


def _compute_contact_from_gripper(gripper_val: float,
                                   finger_data: np.ndarray,
                                   valid_dims: List[int]) -> bool:
    """从夹爪状态和触觉数据推断接触"""
    # gripper闭合 + finger有非9930数据 → 可能接触
    # gripper开合度较小 → 可能正在夹持
    if np.isnan(gripper_val):
        return False

    # 夹爪闭合到一定程度
    gripper_closed = gripper_val < 0.0  # negative = more closed (depends on config)

    # finger数据有效
    finger_valid = finger_data[~np.isnan(finger_data)]
    if len(finger_valid) > 0:
        finger_active = np.any(np.abs(finger_valid) > 0.5)
    else:
        finger_active = False

    return gripper_closed or finger_active


def _extract_tlabel_v2(state: np.ndarray, action: np.ndarray,
                        prev_state: Optional[np.ndarray],
                        robot_type: str,
                        force_metrics: Optional[Dict] = None) -> Dict[str, float]:
    """从observation.state提取18维TLabel v2特征

    戴盟的触觉数据主要在视频流里（deformation/shear/depth），
    数值维度(finger0-35)多为9930占位。
    这里从gripper状态和有效finger数据推断接触信息。
    """
    # Mask placeholders
    state_m = _mask_placeholder(state)

    # 接触检测
    gripper_left = state_m[65] if not np.isnan(state_m[65]) else np.nan
    gripper_right = state_m[66] if len(state_m) > 66 and not np.isnan(state_m[66]) else np.nan
    gripper_main = gripper_left if not np.isnan(gripper_left) else gripper_right

    # Finger data (idx 67-102)
    finger_data = state_m[67:103]
    finger_valid = finger_data[~np.isnan(finger_data)]

    # 接触推断: gripper闭合 + finger有响应
    is_contact = False
    if not np.isnan(gripper_main) and gripper_main < 0:
        is_contact = True
    if len(finger_valid) > 0 and np.any(np.abs(finger_valid) > 0.3):
        is_contact = True

    # Force metrics from tactile_cache (if available)
    if force_metrics:
        # 优先使用预计算的触觉力度
        force_mag = force_metrics.get("mean_force", 0.0)
        force_peak = force_metrics.get("max_force", 0.0)
        contact_area = force_metrics.get("contact_ratio", 0.0)
    else:
        # 从gripper开合度估算力
        if not np.isnan(gripper_main):
            force_mag = max(0, abs(gripper_main) * 10)  # 粗略估算
        else:
            force_mag = 0.0
        force_peak = force_mag
        # 接触面积从finger数据推断
        if len(finger_valid) > 0:
            contact_area = float(np.sum(np.abs(finger_valid) > 0.3)) / max(len(finger_valid), 1)
        else:
            contact_area = 0.0

    # Deformation from finger variance
    if len(finger_valid) > 1:
        deformation_mag = float(np.std(finger_valid))
    else:
        deformation_mag = 0.0

    # IMU-based slip detection
    right_acc = state_m[108:111]
    right_gyro = state_m[111:114]
    slip_event = 0.0
    slip_entropy = 0.0
    if not np.any(np.isnan(right_acc)):
        acc_mag = float(np.sqrt(np.sum(right_acc**2)))
        if acc_mag > 5.0:  # 突然加速度变化 → 可能滑移
            slip_event = min(acc_mag / 20.0, 1.0)
        if not np.any(np.isnan(right_gyro)):
            gyro_mag = float(np.sqrt(np.sum(right_gyro**2)))
            if gyro_mag > 1.0:
                slip_event = max(slip_event, min(gyro_mag / 5.0, 1.0))

    # Delta force (帧间差分)
    delta_fn = 0.0
    delta_fs = 0.0
    if prev_state is not None:
        prev_m = _mask_placeholder(prev_state)
        if not np.isnan(prev_m[65]) and not np.isnan(state_m[65]):
            delta_fn = abs(state_m[65] - prev_m[65])
        # IMU差分
        prev_acc = prev_m[108:111]
        if not np.any(np.isnan(prev_acc)) and not np.any(np.isnan(right_acc)):
            delta_fs = float(np.sqrt(np.sum((right_acc - prev_acc)**2)))

    # Normal field (from finger spatial distribution)
    nf_mag = force_mag
    nf_var = 0.0
    if len(finger_valid) > 1:
        nf_var = float(np.var(finger_valid))

    # Friction cone ratio
    friction_ratio = delta_fs / nf_mag if nf_mag > 1e-6 else 0.0

    # Force direction (from gripper + IMU)
    if not np.any(np.isnan(right_acc)) and np.sqrt(np.sum(right_acc**2)) > 0.01:
        force_dir = float(np.degrees(np.arctan2(right_acc[1], right_acc[0])))
    else:
        force_dir = 0.0

    # Pressure centroid (from finger spatial distribution)
    if len(finger_valid) > 0 and np.sum(np.abs(finger_valid)) > 1e-10:
        weighted_pos = np.sum(np.arange(len(finger_valid)) * np.abs(finger_valid))
        centroid_x = weighted_pos / (np.sum(np.abs(finger_valid)) * max(len(finger_valid) - 1, 1))
    else:
        centroid_x = 0.5

    return {
        "contact": 1.0 if is_contact else 0.0,
        "deformation_magnitude": round(deformation_mag, 4),
        "force_magnitude": round(force_mag, 4),
        "force_peak": round(force_peak, 4),
        "force_direction": round(force_dir, 2),
        "slip_entropy": round(slip_entropy, 4),
        "slip_event": round(slip_event, 4),
        "texture_energy": 0.0,  # 需要视频流deformation数据
        "edge_density": 0.0,    # 需要视频流数据
        "contact_area": round(min(contact_area, 1.0), 4),
        "centroid_x": round(centroid_x, 4),
        "normal_field_magnitude": round(nf_mag, 4),
        "normal_field_variance": round(nf_var, 4),
        "shear_field_magnitude": 0.0,  # 需要视频流shear数据
        "shear_field_direction": 0.0,  # 需要视频流数据
        "delta_force_normal": round(delta_fn, 4),
        "delta_force_shear": round(delta_fs, 4),
        "friction_cone_ratio": round(min(friction_ratio, 10.0), 4),
    }


def _infer_phases(frames_contact, frames_slip):
    """从接触和滑移状态推断操作阶段"""
    phases = []
    current = "idle"
    for ic, is_slip in zip(frames_contact, frames_slip):
        if current == "idle":
            if ic:
                current = "initial_contact"
        elif current == "initial_contact":
            if is_slip:
                current = "slip"
            elif ic:
                current = "stable_contact"
        elif current == "stable_contact":
            if is_slip:
                current = "slip"
            elif not ic:
                current = "release"
        elif current == "slip":
            if not is_slip and ic:
                current = "stable_contact"
            elif not ic:
                current = "release"
        elif current == "release":
            if ic:
                current = "re_contact"
            else:
                current = "idle"
        elif current == "re_contact":
            if is_slip:
                current = "slip"
            elif ic:
                current = "stable_contact"
        phases.append(current)
    return phases


class DaimonAdapter(BaseAdapter):
    """戴盟 Daimon-Infinity Parquet → TLabelData"""

    @property
    def name(self) -> str:
        return "daimon"

    @property
    def supported_extensions(self):
        return [".parquet"]

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "contact": True,
            "deformation_magnitude": True,   # finger数据
            "force_magnitude": True,          # gripper/finger推算
            "force_peak": True,
            "force_direction": True,          # IMU推算
            "slip_entropy": True,
            "slip_event": True,              # IMU加速度突变检测
            "texture_energy": False,          # 需视频流
            "edge_density": False,            # 需视频流
            "contact_area": True,
            "centroid_x": True,
            "normal_field_magnitude": True,
            "normal_field_variance": True,
            "shear_field_magnitude": False,    # 需视频流shear
            "shear_field_direction": False,    # 需视频流shear
            "delta_force_normal": True,
            "delta_force_shear": True,
            "friction_cone_ratio": True,
        }

    def get_sensor_info(self) -> Dict[str, Any]:
        return {
            "type": "vision-based_tactile",
            "manufacturer": "daimon",
            "model": "DM-TacClaw",
        }

    def load(self, file_path: str,
             episode_index: Optional[int] = None,
             max_frames: Optional[int] = None,
             **kwargs) -> TLabelData:
        """
        加载Daimon-Infinity parquet数据

        参数:
            file_path: parquet文件路径或episode目录路径
            episode_index: 指定episode (默认加载第一个)
            max_frames: 最大帧数 (懒加载, 默认全部)
        """
        if not HAS_PYARROW:
            raise ImportError("戴盟适配器需要pyarrow: pip install pyarrow")

        path = Path(file_path)

        # 查找parquet文件
        if path.is_dir():
            parquet_path = self._find_parquet(path)
        elif path.suffix == ".parquet":
            parquet_path = path
        else:
            raise ValueError(f"不支持的路径类型: {path}")

        # 加载meta信息
        info = _load_info_json(parquet_path)
        tasks = _load_tasks(parquet_path)
        robot_type = _detect_robot_type(info)
        fps = info.get("fps", 30)
        total_episodes = info.get("total_episodes", 1)

        # 读取parquet
        table = pq.read_table(str(parquet_path))
        df = table.to_pandas()

        # 筛选episode
        if episode_index is not None and "episode_index" in df.columns:
            df = df[df["episode_index"] == episode_index]
        elif "episode_index" in df.columns:
            # 默认取第一个episode
            first_ep = df["episode_index"].iloc[0]
            df = df[df["episode_index"] == first_ep]
            episode_index = int(first_ep)

        # 限制帧数 (懒加载)
        if max_frames is not None and len(df) > max_frames:
            df = df.head(max_frames)

        num_frames = len(df)

        # 提取任务描述
        task_idx = int(df["task_index"].iloc[0]) if "task_index" in df.columns else 0
        task_desc = tasks.get(task_idx, "unknown task")

        # 逐帧处理
        tlabel_frames = []
        frames_contact = []
        frames_slip = []

        states = df["observation.state"].values
        actions = df["action"].values if "action" in df.columns else None
        timestamps = df["timestamp"].values if "timestamp" in df.columns else None
        frame_indices = df["frame_index"].values if "frame_index" in df.columns else np.arange(num_frames)

        for i in range(num_frames):
            state = np.array(states[i])
            action = np.array(actions[i]) if actions is not None else np.zeros(111)
            prev_state = np.array(states[i - 1]) if i > 0 else None

            tlabel_v2 = _extract_tlabel_v2(state, action, prev_state, robot_type)

            frames_contact.append(tlabel_v2["contact"] > 0.5)
            frames_slip.append(tlabel_v2["slip_event"] > 0.5)

            # 传感器特有数据
            state_m = _mask_placeholder(state)
            sensor_specific = {
                "task": task_desc,
                "score": float(df["score"].iloc[i]) if "score" in df.columns else 1.0,
                "gripper_left": float(state_m[65]) if not np.isnan(state_m[65]) else None,
                "gripper_right": float(state_m[66]) if len(state_m) > 66 and not np.isnan(state_m[66]) else None,
                "right_acc": [float(v) for v in state_m[108:111]] if not np.any(np.isnan(state_m[108:111])) else None,
                "right_gyro": [float(v) for v in state_m[111:114]] if not np.any(np.isnan(state_m[111:114])) else None,
                "robot_type": robot_type,
            }

            confidence = self._compute_confidence(tlabel_v2)

            frame = TLabelFrame(
                frame_idx=int(frame_indices[i]),
                timestamp_s=round(float(timestamps[i]) if timestamps is not None else i / fps, 4),
                tlabel_v2=tlabel_v2,
                manipulation_phase="idle",  # 后面统一推断
                confidence=confidence,
                sensor_specific=sensor_specific,
            )
            tlabel_frames.append(frame)

        # 批量推断操作阶段
        phases = _infer_phases(frames_contact, frames_slip)
        for frame, phase in zip(tlabel_frames, phases):
            frame.manipulation_phase = phase

        sensor_info = {
            "type": "vision-based_tactile",
            "model": "DM-TacClaw",
            "manufacturer": "daimon",
            "modality": "vtla_multimodal",
            "layout": {
                "type": robot_type,
                "observation_state_dim": 114,
                "action_dim": 111,
                "fps": fps,
                "total_episodes": total_episodes,
                "placeholder_value": PLACEHOLDER,
                "note": "触觉RGB/deformation/shear/depth在视频流中，数值维度finger0-35多为占位",
            }
        }

        episode_info = {
            "source": "Daimon-Infinity",
            "file": parquet_path.name,
            "robot_type": robot_type,
            "episode_index": episode_index,
            "task": task_desc,
            "fps": fps,
        }

        return TLabelData(
            frames=tlabel_frames,
            sensor_info=sensor_info,
            episode_info=episode_info,
            capabilities=self.get_capabilities(),
        )

    @staticmethod
    def _find_parquet(directory: Path) -> Path:
        """在目录中查找parquet数据文件"""
        # 优先找 data/chunk-000/file-000.parquet
        for pattern in ["data/chunk-*/file-*.parquet", "**/*.parquet"]:
            matches = list(directory.glob(pattern))
            if matches:
                return sorted(matches)[0]
        raise FileNotFoundError(f"目录中没有找到parquet文件: {directory}")

    @staticmethod
    def _compute_confidence(tlabel_v2: Dict) -> float:
        """计算标注置信度"""
        if tlabel_v2["contact"] < 0.5 and tlabel_v2["slip_event"] < 0.5:
            return 0.95
        if tlabel_v2["contact"] > 0.5 and tlabel_v2["slip_event"] < 0.5:
            return 0.7  # 戴盟数值触觉精度较低，置信度略低
        if tlabel_v2["slip_event"] > 0.5:
            return 0.4  # IMU推断滑移，不太确定
        return 0.6
