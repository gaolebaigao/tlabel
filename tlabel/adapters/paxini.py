"""
帕西尼适配器 — 将OmniSharingDB HDF5数据转换为TLabelData

复用paxini_adapter.py的PaxiniParser核心逻辑，封装为BaseAdapter接口。
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from tlabel.adapters.base import BaseAdapter
from tlabel.core.types import TLabelData, TLabelFrame

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


# 区域名称映射
REGION_NAME_MAP = {
    "palm_sensor1": "palm",
    "J32L": "index_prox", "J42L": "index_mid",
    "M6L": "middle",
    "S22L": "ring_prox", "S32L": "ring_dist", "S6L": "ring_base",
    "Z22L": "thumb_prox", "Z32L": "thumb_dist", "Z6L": "thumb_base",
    "W22L": "pinky_prox", "W32L": "pinky_dist", "W6L": "pinky_base",
}

# 接触阈值
CONTACT_THRESHOLD = 0.3


class PaxiniAdapter(BaseAdapter):
    """帕西尼 HDF5 → TLabelData"""

    @property
    def name(self) -> str:
        return "paxini"

    @property
    def supported_extensions(self):
        return [".h5", ".hdf5"]

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "contact": True, "deformation_magnitude": True,
            "force_magnitude": True, "force_peak": True,
            "force_direction": False,  # PaXini只有法向力
            "slip_entropy": True, "slip_event": True,
            "texture_energy": False,   # 非视觉传感器
            "edge_density": False,     # 非视觉传感器
            "contact_area": True, "centroid_x": True,
            "normal_field_magnitude": True, "normal_field_variance": True,
            "shear_field_magnitude": False,
            "shear_field_direction": False,
            "delta_force_normal": True,
            "delta_force_shear": False,
            "friction_cone_ratio": False,
        }

    def get_sensor_info(self) -> Dict[str, Any]:
        return {
            "type": "distributed_taxel_array",
            "manufacturer": "paxini",
            "model": "PXCap",
        }

    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        if not HAS_H5PY:
            raise ImportError("帕西尼适配器需要h5py: pip install h5py")

        hf = h5py.File(file_path, 'r')
        try:
            return self._parse(hf, file_path, **kwargs)
        finally:
            hf.close()

    def _parse(self, hf, file_path: str, **kwargs) -> TLabelData:
        """解析HDF5文件"""
        # 元数据
        meta = hf['dataset/meta'].attrs
        objects = self._decode_list(meta.get('物品种类', []))

        # 传感器布局
        obs = hf['dataset/observation']
        ref_hand = 'righthand' if 'righthand' in obs else 'lefthand'
        tactile_data = obs[f'{ref_hand}/tactile/data']
        sensor_lengths = [int(x) for x in tactile_data.attrs.get('sensor_lengths', [])]
        sensor_names = self._decode_list(tactile_data.attrs.get('sensor_names', []))
        if not sensor_names:
            sensor_names = [f"sensor_{i}" for i in range(len(sensor_lengths))]

        # 触觉数据
        try:
            right_tac = hf['dataset/observation/righthand/tactile/data'][:]
            left_tac = hf['dataset/observation/lefthand/tactile/data'][:]
        except:
            right_tac = np.zeros((1, sum(sensor_lengths)))
            left_tac = np.zeros((1, sum(sensor_lengths)))

        # 手部位姿
        try:
            right_pose = hf['dataset/observation/righthand/handpose/data'][:]
            left_pose = hf['dataset/observation/lefthand/handpose/data'][:]
        except:
            right_pose = np.zeros((1, 7))
            left_pose = np.zeros((1, 7))

        # 时间戳
        try:
            timestamps = hf['dataset/observation/aligned_timestamp'][:]
        except:
            num_frames = right_tac.shape[0]
            timestamps = np.arange(num_frames) * 33  # ~30Hz

        num_frames = len(timestamps)
        if num_frames > 1:
            dt_ms = np.mean(np.diff(timestamps))
            sample_rate = 1000.0 / dt_ms
        else:
            sample_rate = 30.0

        # 计算基线
        baseline_n = min(10, num_frames)
        baseline_right = np.mean(right_tac[:baseline_n], axis=0)
        baseline_left = np.mean(left_tac[:baseline_n], axis=0)

        # 逐帧处理
        tlabel_frames = []
        prev_contacts = None

        for fi in range(num_frames):
            r_tac = right_tac[fi]
            l_tac = left_tac[fi]

            # 切分为区域
            r_regions = self._split_regions(r_tac, sensor_lengths)
            l_regions = self._split_regions(l_tac, sensor_lengths)
            r_bl = self._split_regions(baseline_right, sensor_lengths)
            l_bl = self._split_regions(baseline_left, sensor_lengths)

            # 逐区域检测接触
            r_contacts = [self._detect_contact(reg, bl) for reg, bl in zip(r_regions, r_bl)]
            l_contacts = [self._detect_contact(reg, bl) for reg, bl in zip(l_regions, l_bl)]
            all_contacts = r_contacts + l_contacts

            # 滑移检测
            slip_detected = False
            if prev_contacts is not None:
                slip_detected = self._detect_slip(all_contacts, prev_contacts)

            # 提取18维TLabel v2
            tlabel_v2 = self._extract_tlabel_v2(all_contacts, slip_detected, prev_contacts)

            # 操作阶段
            any_contact = any(c["state"] != "no_contact" for c in all_contacts)
            phase = self._infer_phase(any_contact, slip_detected, fi, num_frames)

            # 置信度
            confidence = self._compute_confidence(any_contact, slip_detected)

            # 传感器特有数据
            sensor_specific = {
                "right_regions": {sensor_names[i]: r_contacts[i] for i in range(min(len(sensor_names), len(r_contacts)))},
                "left_regions": {sensor_names[i]: l_contacts[i] for i in range(min(len(sensor_names), len(l_contacts)))},
            }

            frame = TLabelFrame(
                frame_idx=fi,
                timestamp_s=round(float(timestamps[fi]) / 1000.0, 4),
                tlabel_v2=tlabel_v2,
                manipulation_phase=phase,
                confidence=confidence,
                sensor_specific=sensor_specific,
            )
            tlabel_frames.append(frame)
            prev_contacts = all_contacts

        sensor_info = {
            "type": "distributed_taxel_array",
            "model": "PXCap",
            "manufacturer": "paxini",
            "modality": "pressure_array",
            "layout": {
                "type": "whole_hand",
                "num_sensors": len(sensor_lengths),
                "sensor_names": sensor_names,
                "sensor_lengths": sensor_lengths,
                "total_taxels": sum(sensor_lengths),
                "sampling_rate_hz": round(sample_rate, 1),
            }
        }

        episode_info = {
            "source": "OmniSharingDB",
            "file": Path(file_path).name,
            "objects": objects,
        }

        return TLabelData(
            frames=tlabel_frames,
            sensor_info=sensor_info,
            episode_info=episode_info,
            capabilities=self.get_capabilities(),
        )

    @staticmethod
    def _decode_list(arr) -> List[str]:
        result = []
        for item in arr:
            if isinstance(item, bytes):
                result.append(item.decode('utf-8', errors='replace'))
            elif isinstance(item, np.bytes_):
                result.append(str(item, encoding='utf-8', errors='replace'))
            else:
                result.append(str(item))
        return result

    @staticmethod
    def _split_regions(data, sensor_lengths):
        regions = []
        offset = 0
        for length in sensor_lengths:
            regions.append(data[offset:offset + length])
            offset += length
        return regions

    @staticmethod
    def _detect_contact(region, baseline):
        adjusted = region - baseline
        active_mask = adjusted > CONTACT_THRESHOLD
        num_active = int(np.sum(active_mask))
        total = len(region)

        if num_active == 0:
            return {"state": "no_contact", "active_taxels": 0,
                    "contact_ratio": 0.0, "mean_force": 0.0, "max_force": 0.0}

        active_vals = adjusted[active_mask]
        ratio = num_active / total

        if ratio < 0.1:
            state = "initial_contact"
        elif ratio < 0.5:
            state = "partial_contact"
        else:
            state = "full_contact"

        return {
            "state": state,
            "active_taxels": num_active,
            "contact_ratio": round(float(ratio), 4),
            "mean_force": round(float(np.mean(active_vals)), 4),
            "max_force": round(float(np.max(active_vals)), 4),
        }

    @staticmethod
    def _detect_slip(curr_contacts, prev_contacts):
        """质心偏移+力变化率检测滑移"""
        for cc, pc in zip(curr_contacts, prev_contacts):
            if cc["state"] == "no_contact" or pc["state"] == "no_contact":
                continue
            centroid_shift = abs(cc["mean_force"] - pc["mean_force"])
            force_rate = abs(cc["mean_force"] - pc["mean_force"]) / max(pc["mean_force"], 0.01)
            if centroid_shift > 1.0 or force_rate > 0.3:
                return True
        return False

    @staticmethod
    def _extract_tlabel_v2(contacts, slip_detected, prev_contacts=None):
        """帕西尼18维TLabel v2提取"""
        active_forces = [c["mean_force"] for c in contacts if c["state"] != "no_contact"]
        active_max = [c["max_force"] for c in contacts if c["state"] != "no_contact"]
        active_ratios = [c["contact_ratio"] for c in contacts if c["state"] != "no_contact"]

        any_contact = len(active_forces) > 0
        total_ratio = sum(active_ratios)

        nf_mag = float(np.mean(active_forces)) if active_forces else 0.0
        nf_var = float(np.var(active_forces)) if len(active_forces) > 1 else 0.0

        delta_fn = 0.0
        if prev_contacts is not None:
            prev_active = [c["mean_force"] for c in prev_contacts if c["state"] != "no_contact"]
            curr_mean = np.mean(active_forces) if active_forces else 0.0
            prev_mean = np.mean(prev_active) if prev_active else 0.0
            delta_fn = abs(curr_mean - prev_mean)

        # slip entropy
        forces = [c["mean_force"] for c in contacts if c["mean_force"] > 0]
        if len(forces) >= 2:
            total = sum(forces)
            if total > 1e-10:
                probs = np.array(forces) / total
                probs = probs[probs > 0]
                slip_ent = float(-np.sum(probs * np.log(probs)))
            else:
                slip_ent = 0.0
        else:
            slip_ent = 0.0

        # pressure centroid
        all_forces = [c["mean_force"] for c in contacts]
        if sum(all_forces) > 1e-10:
            weighted_pos = sum(i * f for i, f in enumerate(all_forces))
            centroid_x = weighted_pos / (sum(all_forces) * max(len(all_forces) - 1, 1))
        else:
            centroid_x = 0.5

        return {
            "contact": 1.0 if any_contact else 0.0,
            "deformation_magnitude": round(nf_mag, 4),
            "force_magnitude": round(nf_mag, 4),
            "force_peak": round(float(np.max(active_max)) if active_max else 0.0, 4),
            "force_direction": 0.0,
            "slip_entropy": round(slip_ent, 4),
            "slip_event": 1.0 if slip_detected else 0.0,
            "texture_energy": 0.0,
            "edge_density": 0.0,
            "contact_area": round(min(total_ratio, 1.0), 4),
            "centroid_x": round(centroid_x, 4),
            "normal_field_magnitude": round(nf_mag, 4),
            "normal_field_variance": round(nf_var, 4),
            "shear_field_magnitude": 0.0,
            "shear_field_direction": 0.0,
            "delta_force_normal": round(delta_fn, 4),
            "delta_force_shear": 0.0,
            "friction_cone_ratio": 0.0,
        }

    @staticmethod
    def _infer_phase(any_contact, slip, fi, total):
        if not any_contact:
            return "approach" if fi < total * 0.5 else "retract"
        if slip:
            return "slip"
        return "stable_contact"

    @staticmethod
    def _compute_confidence(any_contact, slip):
        if not any_contact and not slip:
            return 0.95
        if any_contact and not slip:
            return 0.8
        return 0.5
