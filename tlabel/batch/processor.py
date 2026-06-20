"""
BatchProcessor — 多Episode批处理引擎

解决v0.3.0只能单条处理的痛点，实现：
1. 批量加载目录下所有Episode
2. 批量AI预标注
3. 批量质量评分
4. 批量导出

用法:
    bp = tlabel.BatchProcessor("episodes_dir/")
    bp.auto_label(min_confidence=0.7)
    bp.quality_check()
    bp.export_all("output/")
    bp.summary()
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from tlabel.core.types import TLabelData
from tlabel.core.loader import load
from tlabel.core.registry import auto_detect_format, _ensure_adapters


class BatchProcessor:
    """
    多Episode批处理器

    Args:
        source_dir: 包含多个Episode文件的目录
        pattern: 文件匹配模式，默认递归搜索所有支持格式
        recursive: 是否递归搜索子目录

    用法:
        bp = tlabel.BatchProcessor("episodes/")
        bp.load_all()
        bp.auto_label(min_confidence=0.7)
        bp.quality_check()
        bp.export_all("output/")
    """

    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {".pkl", ".pickle", ".h5", ".hdf5", ".parquet", ".json"}

    def __init__(self, source_dir: str, pattern: str = "*", recursive: bool = True):
        self.source_dir = Path(source_dir)
        self.pattern = pattern
        self.recursive = recursive
        self.datasets: Dict[str, TLabelData] = {}
        self._quality_scores: Dict[str, Dict] = {}
        self._label_summaries: Dict[str, Dict] = {}

    def load_all(self) -> "BatchProcessor":
        """
        批量加载目录下所有Episode文件

        Returns:
            self，支持链式调用
        """
        if not self.source_dir.exists():
            raise FileNotFoundError(f"目录不存在: {self.source_dir}")

        files = self._scan_files()
        if not files:
            raise ValueError(f"未找到支持的数据文件: {self.source_dir}")

        _ensure_adapters()

        for fpath in files:
            try:
                data = load(str(fpath))
                key = str(fpath.relative_to(self.source_dir))
                self.datasets[key] = data
            except Exception as e:
                print(f"[BatchProcessor] 跳过 {fpath.name}: {e}")

        return self

    def auto_label(self, min_confidence: float = 0.6,
                   engine: str = "auto",
                   target_fields: Optional[List[str]] = None) -> "BatchProcessor":
        """
        批量AI预标注

        Args:
            min_confidence: 最低置信度阈值
            engine: 引擎选择 ("auto" / "ml" / "rule")
            target_fields: 只预测指定维度

        Returns:
            self
        """
        for key, data in self.datasets.items():
            try:
                summary = data.auto_label(
                    min_confidence=min_confidence,
                    engine=engine,
                    target_fields=target_fields,
                )
                self._label_summaries[key] = summary
            except Exception as e:
                self._label_summaries[key] = {"error": str(e)}

        return self

    def quality_check(self, verbose: bool = False) -> "BatchProcessor":
        """
        批量质量评分

        Args:
            verbose: 是否输出详细警告

        Returns:
            self
        """
        for key, data in self.datasets.items():
            try:
                score = data.quality_score(verbose=verbose)
                self._quality_scores[key] = score
            except Exception as e:
                self._quality_scores[key] = {"error": str(e), "overall": 0, "grade": "F"}

        return self

    def export_all(self, output_dir: str, format: str = "auto") -> "BatchProcessor":
        """
        批量导出所有Episode

        Args:
            output_dir: 输出目录
            format: 导出格式 ("json" / "csv" / "hdf5" / "auto")

        Returns:
            self
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        for key, data in self.datasets.items():
            # 保留子目录结构
            file_out = out_path / key
            file_out.parent.mkdir(parents=True, exist_ok=True)

            # 确定输出后缀
            if format == "auto":
                suffix = ".json"
            elif format == "csv":
                suffix = ".csv"
            elif format in ("hdf5", "h5"):
                suffix = ".h5"
            else:
                suffix = ".json"

            output_file = file_out.with_suffix(suffix)
            try:
                data.export(str(output_file), format=format)
            except Exception as e:
                print(f"[BatchProcessor] 导出失败 {key}: {e}")

        return self

    def summary(self) -> Dict:
        """
        批处理结果汇总

        Returns:
            {
                "total_episodes": int,
                "total_frames": int,
                "avg_quality": float,
                "quality_grades": Dict[str, int],
                "label_stats": Dict,
                "episodes": List[Dict],
            }
        """
        total_frames = sum(d.num_frames for d in self.datasets.values())
        n_episodes = len(self.datasets)

        # Quality grades distribution
        grades = {}
        quality_scores = []
        for key, score in self._quality_scores.items():
            if "error" not in score:
                g = score.get("grade", "N/A")
                grades[g] = grades.get(g, 0) + 1
                quality_scores.append(score.get("overall", 0))

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Per-episode summary
        episodes = []
        for key, data in self.datasets.items():
            ep = {
                "file": key,
                "frames": data.num_frames,
                "duration_s": round(data.duration_s, 2),
                "sensor": data.sensor_type,
                "modified": data.modified_count,
            }
            if key in self._quality_scores:
                qs = self._quality_scores[key]
                ep["quality"] = qs.get("overall", 0)
                ep["grade"] = qs.get("grade", "N/A")
            if key in self._label_summaries:
                ls = self._label_summaries[key]
                ep["labeled_fields"] = ls.get("predicted_fields", {})
            episodes.append(ep)

        return {
            "total_episodes": n_episodes,
            "total_frames": total_frames,
            "avg_quality": round(avg_quality, 1),
            "quality_grades": grades,
            "label_stats": self._label_summaries,
            "episodes": episodes,
        }

    def get(self, key: str) -> Optional[TLabelData]:
        """按key获取单个TLabelData"""
        return self.datasets.get(key)

    def __len__(self):
        return len(self.datasets)

    def __repr__(self):
        return (f"BatchProcessor(episodes={len(self.datasets)}, "
                f"dir={self.source_dir})")

    def _scan_files(self) -> List[Path]:
        """扫描目录中所有支持的数据文件"""
        files = []
        if self.recursive:
            for root, dirs, fnames in os.walk(self.source_dir):
                for fname in fnames:
                    fpath = Path(root) / fname
                    if fpath.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        files.append(fpath)
        else:
            for fpath in self.source_dir.iterdir():
                if fpath.is_file() and fpath.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    files.append(fpath)

        return sorted(files)
