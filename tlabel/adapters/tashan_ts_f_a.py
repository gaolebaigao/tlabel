"""
他山科技 TS-F-A 触觉传感器数据集适配器

命名规范: 品牌名称(tashan) + 传感器型号(TS-F-A) → tashan_ts_f_a
数据来源: RoboMIND V2.0 (AgileX Cobot Magic)
HDF5结构: tactile_observations/tactile_{left/right}_align/data
数据形状: (T, 2, 6) float32
  - dim0: normal_force (法向力, N)
  - dim1: tangential_force (切向力, N)
  - dim2: tangential_direction (切向方向, rad)
  - dim3: tangential_fx (切向力x分量, N)
  - dim4: tangential_fy (切向力y分量, N)
  - dim5: contact_indicator (接触指示)
  - 65535.0 = 无效值/溢出标记 (uint16 overflow)

Compliance Level: L3 (有完整3D力向量: tangential_fx, tangential_fy, normal_force)
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from tlabel.adapters.base import DataAdapterBase
from tlabel.core.types import TLabelData, TLabelFrame
from tlabel.core.schema import TLabelSchemaV2

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

# 无效值标记 (uint16 overflow → float32 = 65535.0)
INVALID_MARKER = 65535.0
# 法向力接触阈值
CONTACT_THRESHOLD = 0.01


class TashanTsFAAdapter(DataAdapterBase):
    """他山科技 TS-F-A 指尖力传感器 → TLabelData

    解析 RoboMIND V2.0 中 AgileX 移动双臂机器人采集的 Tashan 触觉数据。
    Compliance Level: L3（有法向力 + 切向力x/y分量 = 完整3D力向量）
    """

    default_compliance_level: str = "L3"

    @property
    def name(self) -> str:
        return "tashan_ts_f_a"

    @property
    def manufacturer(self) -> str:
        return "Tashan (他山科技)"

    @property
    def model(self) -> str:
        return "TS-F-A"

    @property
    def supported_extensions(self) -> List[str]:
        return [".hdf5", ".h5"]

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "dims": 6,
            "measures": ["normal_force", "tangential_force", "tangential_direction",
                         "tangential_fx", "tangential_fy", "contact_indicator"],
            "has_temperature": False,
            "has_spatial_array": False,
            "has_force_vector": True,
            "num_sensors_per_hand": 2,
            "invalid_marker": INVALID_MARKER,
        }

    def get_sensor_info(self) -> Dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "type": "force",
            "dimensions": 6,
            "units": {
                "normal_force": "N",
                "tangential_force": "N",
                "tangential_direction": "rad",
                "tangential_fx": "N",
                "tangential_fy": "N",
                "contact_indicator": "binary",
            },
            "notes": "RoboMIND V2.0 data; 65535.0 = invalid/no-contact marker",
        }

    def extract_schema(self, raw_frame_data: Dict[str, Any]) -> TLabelSchemaV2:
        """将 Tashan TS-F-A 原始数据转换为 TLabel Schema V2 (14维结构化触觉语义标注)

        参数:
            raw_frame_data: dict with keys:
                - sensor_id: str ("left"/"right")
                - normal_force: float (dim0)
                - tangential_force: float (dim1)
                - tangential_direction: float (dim2)
                - tangential_fx: float (dim3)
                - tangential_fy: float (dim4)
                - contact_indicator: float (dim5)

        返回:
            TLabelSchemaV2 — L3级别（有完整3D力向量）
        """
        nf = raw_frame_data.get("normal_force", 0.0)
        tf = raw_frame_data.get("tangential_force", 0.0)
        fx = raw_frame_data.get("tangential_fx", 0.0)
        fy = raw_frame_data.get("tangential_fy", 0.0)

        prov = {
            "sensor_model": f"{self.manufacturer} {self.model}",
            "source_hand": raw_frame_data.get("sensor_id", "unknown"),
            "adapter": self.name,
        }

        if nf == INVALID_MARKER or tf == INVALID_MARKER:
            return TLabelSchemaV2(
                contact=False,
                force_magnitude=0.0,
                force_vector=None,
                compliance_level="L1",
                provenance=prov,
                data_quality={
                    "raw_normal_force": 0.0,
                    "raw_tangential_force": 0.0,
                    "invalid": True,
                    "invalid_marker_value": INVALID_MARKER,
                },
            )

        contact = bool(nf > CONTACT_THRESHOLD or tf > CONTACT_THRESHOLD)

        return TLabelSchemaV2(
            contact=contact,
            contact_centroid=None,
            force_magnitude=float(nf) if contact else 0.0,
            force_vector=[float(fx), float(fy), float(nf)] if contact else None,
            slip_event=None,
            manipulation_phase=None,
            object_deformation=None,
            temperature=None,
            texture_class=None,
            confidence=0.9 if contact else 0.5,
            compliance_level="L3" if contact else "L1",
            provenance=prov,
            data_quality={
                "raw_normal_force": float(nf),
                "raw_tangential_force": float(tf),
                "tangential_direction": float(raw_frame_data.get("tangential_direction", 0.0)),
                "tangential_fx": float(fx),
                "tangential_fy": float(fy),
                "contact_indicator": float(raw_frame_data.get("contact_indicator", 0.0)),
                "invalid_marker_value": INVALID_MARKER,
            },
        )

    def load(self, file_path: str, **kwargs) -> Optional[TLabelData]:
        """加载 RoboMIND V2.0 HDF5 触觉数据"""
        if not HAS_H5PY:
            raise ImportError("h5py is required for Tashan TS-F-A adapter. Install: pip install h5py")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        frames = []
        with h5py.File(str(path), "r") as f:
            for side in ["left", "right"]:
                tactile_key = f"tactile_observations/tactile_{side}_align/data"
                if tactile_key not in f:
                    raise ValueError(f"Missing tactile data: {tactile_key}")

                data = f[tactile_key]
                T = data.shape[0]

                for t in range(T):
                    for sensor_idx in range(data.shape[1]):
                        raw = {
                            "sensor_id": side,
                            "normal_force": float(data[t, sensor_idx, 0]),
                            "tangential_force": float(data[t, sensor_idx, 1]),
                            "tangential_direction": float(data[t, sensor_idx, 2]),
                            "tangential_fx": float(data[t, sensor_idx, 3]),
                            "tangential_fy": float(data[t, sensor_idx, 4]),
                            "contact_indicator": float(data[t, sensor_idx, 5]),
                        }
                        schema = self.extract_schema(raw)
                        frame = TLabelFrame(
                            frame_index=t,
                            sensor_id=f"{side}_sensor{sensor_idx}",
                            schema_v2=schema,
                        )
                        frames.append(frame)

        return TLabelData(
            frames=frames,
            sensor_type="force",
            source_adapter=self.name,
            source_file=str(path),
            total_frames=len(frames),
        )
