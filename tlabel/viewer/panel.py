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
- [v0.5.0] 预标注结果高亮 + 预标注按钮
"""

import json
import uuid
from typing import Optional, Dict, List

from tlabel.core.types import TLabelData
from tlabel.viewer.templates import generate_panel_html


class TLabelPanel:
    """Jupyter标注面板控制器"""

    def __init__(self, data: TLabelData, lang: str = "auto",
                 auto_label: bool = False, **kwargs):
        self.data = data
        self.lang = lang
        self.instance_id = f"tlabel_{uuid.uuid4().hex[:6]}"

        # v0.4.1: 预计算质量评分和统计摘要
        self._quality_score = None
        self._describe_stats = None
        self._predict_results = None
        self._auto_label_summary = None

        try:
            self._quality_score = data.quality_score(verbose=True)
        except Exception:
            pass
        try:
            self._describe_stats = data.describe()
        except Exception:
            pass

        # v0.5.0: 自动预标注
        if auto_label:
            try:
                self._auto_label_summary = data.auto_label(min_confidence=0.6)
                self._predict_results = getattr(data, '_predict_results', None)
            except Exception:
                pass
        elif hasattr(data, '_predict_results') and data._predict_results is not None:
            self._predict_results = data._predict_results

    def _repr_html_(self):
        """Jupyter自动调用渲染面板"""
        data_dict = self.data.to_dict()

        episode_info = {}
        if hasattr(self.data, 'episode_info') and self.data.episode_info:
            episode_info = self.data.episode_info

        # v0.5.0: 构建预测结果高亮数据
        predict_highlights = {}
        if self._predict_results:
            for r in self._predict_results:
                low_conf_fields = [
                    k for k, v in r.confidence.items() if v < 0.6
                ]
                predicted_fields = list(r.predictions.keys())
                if low_conf_fields or predicted_fields:
                    predict_highlights[str(r.frame_idx)] = {
                        "predicted": predicted_fields,
                        "low_confidence": low_conf_fields,
                        "methods": r.method,
                    }

        # v0.12: 提取图像数据用于可视化
        tactile_images = None
        try:
            images = self.data.get_images(max_frames=50)  # 限制最多50帧避免内存爆炸
            if any(img is not None for img in images):
                # 转换为base64供前端使用
                import base64
                import cv2
                tactile_images = []
                for img in images:
                    if img is not None:
                        _, buffer = cv2.imencode('.png', img)
                        img_base64 = base64.b64encode(buffer).decode('utf-8')
                        tactile_images.append(f"data:image/png;base64,{img_base64}")
                    else:
                        tactile_images.append(None)
        except Exception:
            pass  # 图像提取失败不影响其他功能

        return generate_panel_html(
            data_dict=data_dict,
            lang=self.lang,
            instance_id=self.instance_id,
            episode_info=episode_info,
            quality_score=self._quality_score,
            describe_stats=self._describe_stats,
            predict_highlights=predict_highlights,
            auto_label_summary=self._auto_label_summary,
            tactile_images=tactile_images,  # v0.12: 传入图像数据
        )

    def __repr__(self):
        has_predict = "yes" if self._predict_results else "no"
        return (f"TLabelPanel(frames={self.data.num_frames}, "
                f"sensor={self.data.sensor_type}, "
                f"lang={self.lang}, "
                f"predict={has_predict})")
