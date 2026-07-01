"""
tlabel.load() — 统一加载入口

自动识别文件格式，调用对应适配器，返回TLabelData。
"""

from pathlib import Path
from typing import Optional, Union

from tlabel.core.types import TLabelData
from tlabel.core.registry import auto_detect_format, _ensure_adapters, get_adapter


def load(file_path: Union[str, Path],
         format: Optional[str] = None,
         trajectory_id: Optional[int] = None,
         **kwargs) -> TLabelData:
    """
    加载触觉数据文件，自动识别格式并转换为TLabel Format v2
    
    参数:
        file_path: 数据文件路径
        format: 强制指定格式 ("gelsight" / "paxini" / "daimon" / "tlabel")
        trajectory_id: 轨迹ID（GelSight数据集可选）
        **kwargs: 传递给适配器的额外参数
    
    返回:
        TLabelData — 统一标注容器
    
    用法:
        data = tlabel.load("gelsight_01.pkl")
        data = tlabel.load("paxini.h5", trajectory_id=0)
        data = tlabel.load("annotations.json")
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 确保适配器已注册
    _ensure_adapters()

    # 自动检测格式
    fmt = format or auto_detect_format(str(path))
    if fmt is None:
        raise ValueError(
            f"无法识别文件格式: {file_path}\n"
            f"支持的格式: .pkl (GelSight/DIGIT), .h5/.hdf5 (帕西尼), .parquet/目录 (戴盟)\n"
            f"可手动指定: tlabel.load(path, format='gelsight')"
        )

    adapter_cls = get_adapter(fmt)
    if adapter_cls is None:
        available = list(k for k in ["gelsight", "paxini", "daimon", "univtac"] if get_adapter(k))
        raise ImportError(
            f"适配器 '{fmt}' 不可用（可能缺少依赖）\n"
            f"当前可用: {available or '无'}\n"
            f"GelSight: pip install numpy opencv-python\n"
            f"帕西尼: pip install h5py numpy\n"
            f"戴盟: pip install pyarrow numpy\n"
            f"UniVTAC: pip install h5py numpy"
        )

    adapter = adapter_cls()
    return adapter.load(str(path), trajectory_id=trajectory_id, **kwargs)
