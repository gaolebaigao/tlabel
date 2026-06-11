"""
TLabel数据导出器

支持格式：JSON (TLabel Format v2) / CSV
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
        format: "json" | "csv" | "auto"（根据文件后缀自动判断）
    """
    # 自动检测格式：根据后缀名或默认json
    if format == "auto":
        suffix = Path(output_path).suffix.lower()
        if suffix == ".csv":
            format = "csv"
        else:
            format = "json"

    if format == "json":
        return _export_json(data, output_path)
    elif format == "csv":
        return _export_csv(data, output_path)
    else:
        raise ValueError(f"不支持的导出格式: {format}，可选: json, csv, auto")


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

    headers = ["frame_idx", "timestamp_s", "manipulation_phase", "confidence"] + TLABEL_DIMS

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for frame in data.frames:
            row = [
                frame.frame_idx,
                frame.timestamp_s,
                frame.manipulation_phase,
                frame.confidence,
            ]
            row.extend([frame.tlabel_v2.get(dim, 0.0) for dim in TLABEL_DIMS])
            writer.writerow(row)

    return str(path)
