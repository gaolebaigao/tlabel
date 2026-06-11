"""
TLabelPanel — Jupyter彩色标注面板

在Jupyter中弹出交互式标注面板，支持：
- 彩色时间轴（绿=接触 红=滑移 灰=无接触）
- 22维雷达图
- 帧详情查看
- 批量修正+联动
- 中英文切换
- JSON/CSV导出
"""

import json
import uuid
from typing import Optional

from tlabel.core.types import TLabelData
from tlabel.viewer.templates import generate_panel_html


class TLabelPanel:
    """Jupyter标注面板控制器"""

    def __init__(self, data: TLabelData, lang: str = "auto", **kwargs):
        self.data = data
        self.lang = lang
        self.instance_id = f"tlabel_{uuid.uuid4().hex[:6]}"

    def _repr_html_(self):
        """Jupyter自动调用渲染面板"""
        data_dict = self.data.to_dict()
        return generate_panel_html(
            data_dict=data_dict,
            lang=self.lang,
            instance_id=self.instance_id,
        )

    def __repr__(self):
        return (f"TLabelPanel(frames={self.data.num_frames}, "
                f"sensor={self.data.sensor_type}, "
                f"lang={self.lang})")
