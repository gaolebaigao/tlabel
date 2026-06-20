"""
TLabelBatchPanel — 批处理仪表盘

在Jupyter中显示BatchProcessor的运行结果，支持：
- 批量Episode列表（含质量评分+等级）
- 平均质量评分仪表
- 每个Episode的快速预览

用法:
    bp = tlabel.BatchProcessor("episodes_dir/")
    bp.load_all().auto_label().quality_check()
    bp.review()  # 渲染批处理仪表盘
"""

import json
import uuid
from typing import Optional, Dict

from tlabel.batch.processor import BatchProcessor


class TLabelBatchPanel:
    """批处理仪表盘"""

    def __init__(self, batch_processor: BatchProcessor, lang: str = "auto", **kwargs):
        self.bp = batch_processor
        self.lang = lang
        self.instance_id = f"tlabel_batch_{uuid.uuid4().hex[:6]}"

    def _repr_html_(self):
        """Jupyter自动调用渲染"""
        summary = self.bp.summary()
        summary_json = json.dumps(summary, ensure_ascii=False, default=str)
        tid = self.instance_id

        return f"""<!DOCTYPE html>
<div id="{tid}-root" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
     max-width: 960px; margin: 0 auto; background: #f8f9fa; color: #343a40;
     border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">

<!-- Header -->
<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 20px;
     background:linear-gradient(135deg,#e9ecef,#f1f3f5);border-bottom:1px solid #dee2e6;">
  <div style="display:flex;align-items:center;gap:10px;">
    <span style="font-size:20px;">🦞</span>
    <span style="font-size:16px;font-weight:700;color:#e85d75;">TLabel 批处理仪表盘</span>
    <span style="font-size:10px;color:#868e96;background:#e9ecef;padding:1px 6px;border-radius:4px;">v0.4.1</span>
  </div>
</div>

<!-- Summary Stats -->
<div style="display:flex;gap:16px;padding:16px 20px;background:#fff;border-bottom:1px solid #e9ecef;">
  <div style="text-align:center;flex:1;">
    <div style="font-size:28px;font-weight:900;color:#e85d75;">{summary.get('total_episodes', 0)}</div>
    <div style="font-size:11px;color:#868e96;">Episodes</div>
  </div>
  <div style="text-align:center;flex:1;">
    <div style="font-size:28px;font-weight:900;color:#495057;">{summary.get('total_frames', 0)}</div>
    <div style="font-size:11px;color:#868e96;">Total Frames</div>
  </div>
  <div style="text-align:center;flex:1;">
    <div style="font-size:28px;font-weight:900;color:#4dabf7;">{summary.get('avg_quality', 0):.1f}</div>
    <div style="font-size:11px;color:#868e96;">Avg Quality</div>
  </div>
  <div style="text-align:center;flex:1;">
    <div style="font-size:12px;font-weight:700;line-height:1.6;">
    {self._grade_bar_html(summary.get('quality_grades', {}))}
    </div>
    <div style="font-size:11px;color:#868e96;">Grade分布</div>
  </div>
</div>

<!-- Episode Table -->
<div style="padding:16px 20px;background:#fff;">
  <div style="font-size:13px;font-weight:600;color:#343a40;margin-bottom:10px;">📁 Episode 列表</div>
  <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead>
        <tr style="border-bottom:2px solid #dee2e6;">
          <th style="padding:8px 10px;text-align:left;color:#868e96;">文件</th>
          <th style="padding:8px 10px;text-align:right;color:#868e96;">帧数</th>
          <th style="padding:8px 10px;text-align:right;color:#868e96;">时长(s)</th>
          <th style="padding:8px 10px;text-align:left;color:#868e96;">传感器</th>
          <th style="padding:8px 10px;text-align:right;color:#868e96;">质量</th>
          <th style="padding:8px 10px;text-align:center;color:#868e96;">等级</th>
          <th style="padding:8px 10px;text-align:right;color:#868e96;">已修正</th>
        </tr>
      </thead>
      <tbody>
        {self._episode_rows_html(summary.get('episodes', []))}
      </tbody>
    </table>
  </div>
</div>

</div>"""

    def _grade_bar_html(self, grades: Dict) -> str:
        if not grades:
            return '<span style="color:#adb5bd;">—</span>'
        parts = []
        for g in ['A', 'B', 'C', 'D', 'F']:
            if g in grades:
                colors = {'A': '#51cf66', 'B': '#4dabf7', 'C': '#ffd43b', 'D': '#ff922b', 'F': '#ff6b6b'}
                parts.append(f'<span style="color:{colors.get(g, "#868e96")};">{g}:{grades[g]}</span>')
        return ' '.join(parts)

    def _episode_rows_html(self, episodes: list) -> str:
        if not episodes:
            return '<tr><td colspan="7" style="padding:20px;text-align:center;color:#adb5bd;">暂无Episode数据</td></tr>'
        rows = []
        for ep in episodes:
            grade = ep.get('grade', '-')
            quality = ep.get('quality', 0)
            grade_colors = {'A': '#51cf66', 'B': '#4dabf7', 'C': '#ffd43b', 'D': '#ff922b', 'F': '#ff6b6b'}
            gcolor = grade_colors.get(grade, '#adb5bd')
            rows.append(f"""<tr style="border-bottom:1px solid #f1f3f5;">
              <td style="padding:6px 10px;color:#495057;font-weight:500;">{ep.get('file', '-')}</td>
              <td style="padding:6px 10px;text-align:right;">{ep.get('frames', 0)}</td>
              <td style="padding:6px 10px;text-align:right;">{ep.get('duration_s', 0)}</td>
              <td style="padding:6px 10px;">{ep.get('sensor', '-')}</td>
              <td style="padding:6px 10px;text-align:right;font-weight:600;color:#e85d75;">{quality:.1f if quality else '-'}</td>
              <td style="padding:6px 10px;text-align:center;"><span style="background:{gcolor};color:#fff;padding:1px 8px;border-radius:4px;font-weight:700;font-size:11px;">{grade}</span></td>
              <td style="padding:6px 10px;text-align:right;">{ep.get('modified', 0)}</td>
            </tr>""")
        return '\n'.join(rows)

    def __repr__(self):
        return (f"TLabelBatchPanel(episodes={len(self.bp)}, "
                f"dir={self.bp.source_dir})")
