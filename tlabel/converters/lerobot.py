"""
LeRobot ↔ TLabel 双向转换器

支持：
1. LeRobot Parquet → TLabel JSON（读取触觉观测，生成标注文件）
2. TLabel JSON → LeRobot Parquet（将标注写回，更新 meta/info.json）

用法：
    # LeRobot → TLabel
    from tlabel.converters import lerobot_to_tlabel
    data = lerobot_to_tlabel("path/to/lerobot_episode/")
    data.export("output.json")

    # TLabel → LeRobot
    from tlabel.converters import tlabel_to_lerobot
    tlabel_to_lerobot("tlabel_annotations.json", "path/to/lerobot_episode/")
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, Union, List, Dict

try:
    import pyarrow.parquet as pq
    import pyarrow as pa
except ImportError:
    raise ImportError(
        "LeRobot converter requires pyarrow. Install with: pip install pyarrow"
    )

from tlabel.core.types import TLabelData, TLabelFrame


def lerobot_to_tlabel(
    lerobot_path: Union[str, Path],
    tactile_field: str = "observation.tactile",
    output_format: str = "tlabel"
) -> TLabelData:
    """
    从 LeRobot Parquet 文件加载触觉数据，转换为 TLabelData
    
    参数:
        lerobot_path: LeRobot episode 目录路径（含 meta/info.json 和 data/*.parquet）
        tactile_field: 触觉字段在 Parquet 中的列名（默认 "observation.tactile"）
        output_format: 输出格式（目前仅支持 "tlabel"）
    
    返回:
        TLabelData 实例
    
    示例:
        data = lerobot_to_tlabel("data/episode_000/")
        data.review()
    """
    path = Path(lerobot_path)
    
    # 1. 读取 meta/info.json
    info_path = path / "meta" / "info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"LeRobot meta file not found: {info_path}")
    
    with open(info_path, "r") as f:
        meta = json.load(f)
    
    # 2. 读取 Parquet 文件
    data_dir = path / "data"
    parquet_files = sorted(data_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {data_dir}")
    
    # 合并所有 chunk
    tables = [pq.read_table(pf) for pf in parquet_files]
    table = pa.concat_tables(tables)
    df = table.to_pandas()
    
    # 3. 提取触觉字段
    if tactile_field not in df.columns:
        available = [c for c in df.columns if "tactile" in c.lower() or "force" in c.lower()]
        raise ValueError(
            f"Tactile field '{tactile_field}' not found in parquet.\n"
            f"Available columns: {available[:10]}..."
        )
    
    tactile_data = df[tactile_field].values
    
    # 4. 构建 TLabelFrame 列表
    frames = []
    for i, tact in enumerate(tactile_data):
        # 假设触觉数据是 22 维向量
        if isinstance(tact, (list, np.ndarray)):
            tact_array = np.array(tact)
        else:
            # 如果是标量或其他格式，需要适配
            tact_array = np.array([float(tact)])
        
        # 映射到 tlabel_v2 字典
        tlabel_v2 = {}
        feature_names = meta.get("features", {}).get(tactile_field, {}).get("feature_names", [])
        if len(feature_names) == len(tact_array):
            for name, val in zip(feature_names, tact_array):
                tlabel_v2[name] = float(val)
        else:
            # 如果没有 feature_names，用索引作为键
            for j, val in enumerate(tact_array):
                tlabel_v2[f"dim_{j}"] = float(val)
        
        timestamp = float(df["timestamp"].iloc[i]) if "timestamp" in df.columns else i * 0.033  # 默认 30fps
        
        frame = TLabelFrame(
            frame_idx=i,
            timestamp_s=round(timestamp, 4),
            tlabel_v2=tlabel_v2,
            manipulation_phase="idle",
            confidence=1.0,
        )
        frames.append(frame)
    
    # 5. 构建 sensor_info
    sensor_info = {
        "type": "lerobot_tactile",
        "model": meta.get("robot_type", "unknown"),
        "source": "LeRobot Parquet",
    }
    
    episode_info = {
        "episode_id": meta.get("episode_id", path.stem),
        "task": meta.get("task", ""),
    }
    
    capabilities = {name: True for name in tlabel_v2.keys()}
    
    return TLabelData(
        frames=frames,
        sensor_info=sensor_info,
        episode_info=episode_info,
        capabilities=capabilities,
        sensor_id=f"lerobot_{path.stem}",
    )


def tlabel_to_lerobot(
    tlabel_path: Union[str, Path],
    lerobot_path: Union[str, Path],
    tactile_field: str = "observation.tactile",
    action_field: str = "action",
    overwrite: bool = False
):
    """
    将 TLabel 标注写回 LeRobot Parquet 文件
    
    参数:
        tlabel_path: TLabel JSON 文件路径
        lerobot_path: LeRobot episode 目录路径
        tactile_field: 要写入的触觉字段名
        action_field: 动作字段名（用于配对）
        overwrite: 是否覆盖现有 Parquet 文件
    
    示例:
        tlabel_to_lerobot("annotations.json", "data/episode_000/")
    """
    tlabel_path = Path(tlabel_path)
    lerobot_path = Path(lerobot_path)
    
    # 1. 读取 TLabel JSON
    with open(tlabel_path, "r") as f:
        tlabel_data = json.load(f)
    
    frames = tlabel_data.get("frames", [])
    if not frames:
        raise ValueError("TLabel JSON has no frames")
    
    # 2. 读取现有 Parquet
    data_dir = lerobot_path / "data"
    parquet_files = sorted(data_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {data_dir}")
    
    tables = [pq.read_table(pf) for pf in parquet_files]
    table = pa.concat_tables(tables)
    df = table.to_pandas()
    
    # 3. 验证帧数匹配
    if len(df) != len(frames):
        raise ValueError(
            f"Frame count mismatch: LeRobot has {len(df)} frames, "
            f"TLabel has {len(frames)} frames"
        )
    
    # 4. 提取 22 维特征并添加到 DataFrame
    feature_names = tlabel_data.get("feature_names", [])
    if not feature_names:
        # 从第一帧推断
        feature_names = list(frames[0].get("tlabel_v2", {}).keys())
    
    # 构建触觉特征矩阵
    tactile_matrix = []
    for frame in frames:
        tlabel_v2 = frame.get("tlabel_v2", {})
        row = [float(tlabel_v2.get(name, 0.0)) for name in feature_names]
        tactile_matrix.append(row)
    
    tactile_array = np.array(tactile_matrix, dtype=np.float32)
    
    # 5. 添加到 DataFrame
    if tactile_field in df.columns and not overwrite:
        raise ValueError(
            f"Field '{tactile_field}' already exists. Use overwrite=True to replace."
        )
    
    df[tactile_field] = list(tactile_array)
    
    # 6. 写回 Parquet（合并为单个文件）
    output_parquet = data_dir / "chunk-0000.parquet"
    new_table = pa.Table.from_pandas(df)
    pq.write_table(new_table, output_parquet)
    
    # 删除旧的 chunk 文件
    for pf in parquet_files:
        if pf != output_parquet:
            pf.unlink()
    
    # 7. 更新 meta/info.json
    info_path = lerobot_path / "meta" / "info.json"
    if info_path.exists():
        with open(info_path, "r") as f:
            meta = json.load(f)
    else:
        meta = {"features": {}}
    
    # 添加触觉字段 schema
    meta["features"][tactile_field] = {
        "dtype": "float32",
        "shape": [len(feature_names)],
        "type": "vector",
        "feature_names": feature_names,
        "description": "TLabel annotated tactile features (22 dimensions)",
    }
    
    with open(info_path, "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"[OK] Tactile annotations written to {output_parquet}")
    print(f"[OK] Updated meta/info.json with '{tactile_field}' schema")


# 导出公共 API
__all__ = ["lerobot_to_tlabel", "tlabel_to_lerobot"]
