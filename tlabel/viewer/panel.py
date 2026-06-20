"""
TLabelPanel — Jupyter彩色标注面板

在Jupyter中弹出交互式标注面板，支持：
- 彩色时间轴（绿=接触 红=滑移 灰=无接触）
- 22维雷达图
- 帧详情查看
- 批量修正+联动
- 中英文切换
- JSON/CSV导出
- Episode级标注（v0.4.1）
- 数据质量评分（v0.4.1）
- 统计摘要 describe（v0.4.1）
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

        # v0.4.1: 预计算质量评分和统计摘要，传给前端展示
        self._quality_score = None
        self._describe_stats = None
        try:
            self._quality_score = data.quality_score(verbose=True)
        except Exception:
            pass
        try:
            self._describe_stats = data.describe()
        except Exception:
            pass

    def _repr_html_(self):
        """Jupyter自动调用渲染面板"""
        data_dict = self.data.to_dict()

        # 注入 episode_info 供前端编辑
        episode_info = {}
        if hasattr(self.data, 'episode_info') and self.data.episode_info:
            episode_info = self.data.episode_info

        return generate_panel_html(
            data_dict=data_dict,
            lang=self.lang,
            instance_id=self.instance_id,
            episode_info=episode_info,
            quality_score=self._quality_score,
            describe_stats=self._describe_stats,
        )

    def __repr__(self):
        return (f"TLabelPanel(frames={self.data.num_frames}, "
                f"sensor={self.data.sensor_type}, "
                f"lang={self.lang})")
