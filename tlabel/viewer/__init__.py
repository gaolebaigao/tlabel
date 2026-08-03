"""
查看器模块

v0.18 新增触觉图像可视化:
  - contact_heatmap: 接触热力图
  - force_vector_field: 力向量场
  - contact_region_overlay: 接触区域高亮
  - composite_view: 组合视图
  - frame_animation: 帧序列动画
  - visualize_frame: 自动降级可视化
"""

from tlabel.viewer.panel import TLabelPanel

# v0.18: 触觉图像可视化
try:
    from tlabel.viewer.tactile_vis import (
        contact_heatmap,
        force_vector_field,
        contact_region_overlay,
        composite_view,
        frame_animation,
        visualize_frame,
        text_summary,
    )
    _HAS_VIS = True
except ImportError:
    _HAS_VIS = False


__all__ = ["TLabelPanel"]

if _HAS_VIS:
    __all__.extend([
        "contact_heatmap",
        "force_vector_field",
        "contact_region_overlay",
        "composite_view",
        "frame_animation",
        "visualize_frame",
        "text_summary",
    ])
