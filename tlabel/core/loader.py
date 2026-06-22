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
        format: 强制指定格式 ("gelsight" / "paxini" / "daimon" / "vtouch" / "tlabel")
        trajectory_id: 轨迹ID（GelSight数据集可选）
        **kwargs: 传递给适配器的额外参数
            VTouch额外参数:
                hand: 选择哪只手 "left"/"right" (默认"left")
                sensor_side: 选择哪侧传感器 "left"/"right" (默认"left")
    
    返回:
        TLabelData — 统一标注容器
    
    用法:
        data = tlabel.load("gelsight_01.pkl")
        data = tlabel.load("paxini.h5", trajectory_id=0)
        data = tlabel.load("annotations.json")
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"文件不存在: {file_path}\n"
            f"请检查路径是否正确（建议使用绝对路径）"
        )

    # 确保适配器已注册
    _ensure_adapters()

    # 自动检测格式
    fmt = format or auto_detect_format(str(path))
    if fmt is None:
        raise ValueError(
            f"无法识别文件格式: {path.suffix or '(无扩展名)'}\n"
            f"\n支持的文件格式：\n"
            f"  • .pkl / .pickle  — GelSight Mini, DIGIT (视觉型触觉传感器)\n"
            f"  • .h5 / .hdf5     — PaXini PXCap (分布式力阵列)\n"
            f"  • .parquet        — Daimon DM-TacClaw (多模态机器人)\n"
            f"  • 目录             — Daimon LeRobot 格式 (含 info.json + parquet + videos)\n"
            f"\n如果文件扩展名不标准，可手动指定格式：\n"
            f"  tlabel.load('{file_path}', format='gelsight')\n"
            f"  tlabel.load('{file_path}', format='paxini')\n"
            f"  tlabel.load('{file_path}', format='daimon')"
        )

    adapter_cls = get_adapter(fmt)
    if adapter_cls is None:
        available = list(k for k in ["gelsight", "paxini", "vtouch", "daimon", "tlabel"] if get_adapter(k))
        missing_deps = {
            "gelsight": "pip install tlabel[gelsight]  # 安装 opencv-python",
            "paxini": "pip install tlabel[paxini]      # 安装 h5py",
            "vtouch": "pip install tlabel[vtouch]      # install h5py + opencv-python",
            "daimon": "pip install tlabel[daimon]      # 安装 pyarrow + opencv-python",
            "tlabel": "无需额外依赖（TLabel Format JSON）",
        }
        raise ImportError(
            f"适配器 '{fmt}' 不可用，可能缺少依赖包\n"
            f"\n解决方法：\n"
            f"  {missing_deps.get(fmt, 'pip install tlabel[all]')}\n"
            f"\n当前可用的适配器: {available or '无'}\n"
            f"\n或者一次性安装所有依赖: pip install tlabel[all]"
        )

    adapter = adapter_cls()
    return adapter.load(str(path), trajectory_id=trajectory_id, **kwargs)
