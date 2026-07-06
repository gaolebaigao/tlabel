"""
TLabel数据导出器

支持格式：JSON (TLabel Format v2) / CSV / HDF5
"""

import json
import csv
import numpy as np
from pathlib import Path
from typing import Optional

from tlabel.core.types import TLabelData


class NumpyEncoder(json.JSONEncoder):
    """处理numpy类型的JSON序列化"""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


def export_data(data: TLabelData, output_path: str, format: str = "auto"):
    """
    导出TLabelData为文件
    
    参数:
        data: TLabelData实例
        output_path: 输出路径
        format: "json" | "csv" | "hdf5" | "auto"（根据文件后缀自动判断）
    """
    # 自动检测格式：根据后缀名或默认json
    if format == "auto":
        suffix = Path(output_path).suffix.lower()
        if suffix == ".csv":
            format = "csv"
        elif suffix in (".h5", ".hdf5"):
            format = "hdf5"
        else:
            format = "json"

    if format == "json":
        return _export_json(data, output_path)
    elif format == "csv":
        return _export_csv(data, output_path)
    elif format == "hdf5":
        return _export_hdf5(data, output_path)
    else:
        raise ValueError(f"不支持的导出格式: {format}，可选: json, csv, hdf5, auto")


def _export_json(data: TLabelData, output_path: str):
    """导出为TLabel Format v2 JSON"""
    path = Path(output_path)
    if not path.suffix:
        path = path.with_suffix(".json")

    path.parent.mkdir(parents=True, exist_ok=True)

    result = data.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

    return str(path)


def _export_csv(data: TLabelData, output_path: str):
    """导出为CSV平面表（每帧一行，22维展开）"""
    path = Path(output_path)
    if not path.suffix:
        path = path.with_suffix(".csv")

    path.parent.mkdir(parents=True, exist_ok=True)

    TLABEL_DIMS = [
        "contact", "deformation_magnitude", "force_magnitude", "force_peak",
        "force_direction", "slip_entropy", "slip_event", "texture_energy",
        "edge_density", "contact_area", "centroid_x",
        "normal_field_magnitude", "normal_field_variance",
        "shear_field_magnitude", "shear_field_direction",
        "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
        # --- 时序4维 ---
        "optical_flow_magnitude", "optical_flow_direction",
        "temporal_deformation_rate", "contact_transition",
    ]

    # v0.13: 新增primitive_label列
    headers = ["frame_idx", "timestamp_s", "is_first", "is_last",
               "manipulation_phase", "confidence", "primitive_label"] + TLABEL_DIMS

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i, frame in enumerate(data.frames):
            is_first = (i == 0)
            is_last = (i == len(data.frames) - 1)
            # v0.13: 获取该帧的primitive
            primitive = ""
            if hasattr(data, 'primitive_annotations') and data.primitive_annotations:
                for p in data.primitive_annotations:
                    if p.start_frame <= frame.frame_idx <= p.end_frame:
                        primitive = p.primitive_name
                        break
            row = [
                frame.frame_idx,
                frame.timestamp_s,
                is_first,
                is_last,
                frame.manipulation_phase,
                frame.confidence,
                primitive,
            ]
            row.extend([frame.tlabel_v2.get(dim, 0.0) for dim in TLABEL_DIMS])
            writer.writerow(row)

    return str(path)


def _export_hdf5(data: TLabelData, output_path: str):
    """导出为HDF5格式（科学计算标准）"""
    try:
        import h5py
    except ImportError:
        raise ImportError(
            "HDF5 export requires h5py. Install with: pip install h5py"
        )
    
    path = Path(output_path)
    if not path.suffix:
        path = path.with_suffix(".h5")
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    TLABEL_DIMS = [
        "contact", "deformation_magnitude", "force_magnitude", "force_peak",
        "force_direction", "slip_entropy", "slip_event", "texture_energy",
        "edge_density", "contact_area", "centroid_x",
        "normal_field_magnitude", "normal_field_variance",
        "shear_field_magnitude", "shear_field_direction",
        "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
        "optical_flow_magnitude", "optical_flow_direction",
        "temporal_deformation_rate", "contact_transition",
    ]
    
    with h5py.File(path, "w") as f:
        # 1. 创建主数据集 /tactile_features
        n_frames = data.num_frames
        n_dims = len(TLABEL_DIMS)
        
        # 提取特征矩阵
        feature_matrix = np.zeros((n_frames, n_dims), dtype=np.float32)
        timestamps = np.zeros(n_frames, dtype=np.float64)
        frame_indices = np.zeros(n_frames, dtype=np.int32)
        is_first_arr = np.zeros(n_frames, dtype=bool)
        is_last_arr = np.zeros(n_frames, dtype=bool)
        
        for i, frame in enumerate(data.frames):
            timestamps[i] = frame.timestamp_s
            frame_indices[i] = frame.frame_idx
            is_first_arr[i] = (i == 0)
            is_last_arr[i] = (i == n_frames - 1)
            
            for j, dim in enumerate(TLABEL_DIMS):
                feature_matrix[i, j] = frame.tlabel_v2.get(dim, 0.0)
        
        # 写入数据集
        f.create_dataset("timestamps", data=timestamps)
        f.create_dataset("frame_indices", data=frame_indices)
        f.create_dataset("is_first", data=is_first_arr)
        f.create_dataset("is_last", data=is_last_arr)
        f.create_dataset("tactile_features", data=feature_matrix)
        
        # 添加维度名称作为属性
        f["tactile_features"].attrs["feature_names"] = json.dumps(TLABEL_DIMS)
        f["tactile_features"].attrs["description"] = "TLabel v2 tactile features (22 dimensions)"
        
        # 2. 创建元数据组 /metadata
        meta_group = f.create_group("metadata")
        meta_group.attrs["schema_version"] = data.schema_version
        meta_group.attrs["format"] = "tlabel_v2"
        meta_group.attrs["sensor_type"] = data.sensor_type
        meta_group.attrs["sensor_id"] = data.sensor_id or ""
        meta_group.attrs["num_frames"] = n_frames
        meta_group.attrs["duration_s"] = data.duration_s
        
        # 传感器信息
        sensor_info_json = json.dumps(data.sensor_info)
        meta_group.attrs["sensor_info"] = sensor_info_json
        
        # Episode 信息
        episode_info_json = json.dumps(data.episode_info)
        meta_group.attrs["episode_info"] = episode_info_json
        
        # Capabilities
        capabilities_json = json.dumps(data.capabilities)
        meta_group.attrs["capabilities"] = capabilities_json
        
        # Calibration params
        if data.calibration_params:
            calib_json = json.dumps(data.calibration_params)
            meta_group.attrs["calibration_params"] = calib_json
    
    return str(path)
