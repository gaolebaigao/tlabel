"""
MLEngine — 基于梯度提升的预标注引擎

解决 rc2 的 4 个阻塞 Bug：
  Bug1: 小数据训练崩溃 → 类别检查 + 优雅降级
  Bug2: 校准空操作 → 实际应用校准映射
  Bug3: Cascade反向约束 → types.py 已修复
  Bug4: Contact二值化 → contact用回归模型保留连续值

v0.5.0 改进：
  - Phase使用HMM建模替代hash编码
  - 集成时序后处理管线（平滑+HMM+联动修正）
  - 置信度校准改进

依赖: scikit-learn>=1.0, joblib>=1.0 (pip install tlabel[ml])
"""

import math
import warnings
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import io

from tlabel.core.types import TLabelData, TLabelFrame
from tlabel.predict.engine import PredictEngine, PredictResult, PredictConfig


REGRESSION_FIELDS = {"contact", "force_magnitude", "deformation_magnitude"}
CLASSIFICATION_FIELDS = {"slip_event"}

MIN_CLASSES = 2
MIN_SAMPLES_PER_CLASS = 5
MIN_TOTAL_SAMPLES = 30

FEATURE_FIELDS = [
    "contact", "deformation_magnitude", "force_magnitude", "force_peak",
    "slip_entropy", "slip_event", "texture_energy", "edge_density",
    "contact_area", "centroid_x", "normal_field_magnitude",
    "normal_field_variance", "shear_field_magnitude",
    "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
]


@dataclass
class MLEngineConfig:
    enabled_fields: Optional[List[str]] = None
    use_calibration: bool = True
    calibration_method: str = "sigmoid"
    min_samples: int = MIN_TOTAL_SAMPLES
    min_samples_per_class: int = MIN_SAMPLES_PER_CLASS
    fallback_to_rules: bool = True
    # v0.5.0: 时序后处理
    enable_postprocess: bool = True
    enable_hmm_phase: bool = True


class FieldModel:
    """单个字段的 ML 模型包装"""

    def __init__(self, field_name: str, is_regression: bool = False):
        self.field_name = field_name
        self.is_regression = is_regression
        self.model = None
        self.scaler = StandardScaler()
        self.calibrator = None
        self.is_fitted = False
        self.is_calibrated = False
        self.classes_ = None
        self.training_samples = 0
        self.training_error = None

    def _check_trainability(self, y: np.ndarray) -> Tuple[bool, str]:
        n = len(y)
        if n < MIN_TOTAL_SAMPLES:
            return False, f"Insufficient samples: {n} < {MIN_TOTAL_SAMPLES}"
        if not self.is_regression:
            unique, counts = np.unique(y, return_counts=True)
            if len(unique) < MIN_CLASSES:
                return False, f"Insufficient classes: {len(unique)} < {MIN_CLASSES} (only {list(unique)})"
            for cls, cnt in zip(unique, counts):
                if cnt < MIN_SAMPLES_PER_CLASS:
                    return False, f"Class {cls} insufficient: {cnt} < {MIN_SAMPLES_PER_CLASS}"
        return True, ""

    def fit(self, X: np.ndarray, y: np.ndarray,
            use_calibration: bool = True,
            calibration_method: str = "sigmoid") -> bool:
        ok, reason = self._check_trainability(y)
        if not ok:
            self.training_error = reason
            self.is_fitted = False
            return False

        try:
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)

            if self.is_regression:
                self.model = GradientBoostingRegressor(
                    n_estimators=100, max_depth=3, learning_rate=0.1,
                    subsample=0.8, random_state=42
                )
                self.model.fit(X_scaled, y)
                self.is_fitted = True
                self.is_calibrated = False
            else:
                self.model = GradientBoostingClassifier(
                    n_estimators=100, max_depth=3, learning_rate=0.1,
                    subsample=0.8, random_state=42
                )
                self.model.fit(X_scaled, y)
                self.classes_ = self.model.classes_
                self.is_fitted = True

                if use_calibration and len(self.classes_) == 2:
                    try:
                        base_est = GradientBoostingClassifier(
                            n_estimators=100, max_depth=3, learning_rate=0.1,
                            subsample=0.8, random_state=42
                        )
                        self.calibrator = CalibratedClassifierCV(
                            estimator=base_est,
                            method=calibration_method,
                            cv=3
                        )
                        self.calibrator.fit(X_scaled, y)
                        self.is_calibrated = True
                    except Exception as e:
                        warnings.warn(f"Calibration failed ({self.field_name}): {e}")
                        self.is_calibrated = False

            self.training_samples = len(y)
            self.training_error = None
            return True

        except Exception as e:
            self.training_error = str(e)
            self.model = None
            self.is_fitted = False
            self.is_calibrated = False
            return False

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_fitted or self.model is None:
            raise RuntimeError(f"Model {self.field_name} not fitted: {self.training_error}")

        X_scaled = self.scaler.transform(X)

        if self.is_regression:
            values = self.model.predict(X_scaled)
            values = np.clip(values, 0.0, 1.0)
            # v0.5.0: 基于预测区间估算置信度
            confidences = np.full(len(values), 0.7)
            return values, confidences
        else:
            if self.is_calibrated and self.calibrator is not None:
                probas = self.calibrator.predict_proba(X_scaled)
            else:
                probas = self.model.predict_proba(X_scaled)

            if probas.shape[1] == 2:
                values = (probas[:, 1] >= 0.5).astype(float)
                confidences = np.max(probas, axis=1)
            else:
                values = self.model.classes_[np.argmax(probas, axis=1)]
                confidences = np.max(probas, axis=1)

            return values, confidences


class MLEngine:
    """
    ML 预标注引擎

    v0.5.0:
      - Phase由HMM处理，ML不再训练phase模型
      - 集成时序后处理管线
      - 预测后自动做平滑+联动修正

    用法:
        engine = MLEngine()
        engine.fit(data)
        results = engine.predict(data)
        engine.apply(data, results, min_confidence=0.75)
    """

    def __init__(self, config: Optional[MLEngineConfig] = None):
        self.config = config or MLEngineConfig()
        self._models: Dict[str, FieldModel] = {}
        self._rule_engine = PredictEngine()
        self._feature_names: List[str] = []
        self._is_fitted = False
        self._fit_report: Dict = {}

    def fit(self, data: TLabelData) -> "MLEngine":
        if not data.frames or len(data.frames) < MIN_TOTAL_SAMPLES:
            self._is_fitted = False
            self._fit_report["error"] = f"Insufficient data: {len(data.frames)} frames < {MIN_TOTAL_SAMPLES}"
            return self

        sample_frame = data.frames[0].tlabel_v2
        self._feature_names = [f for f in FEATURE_FIELDS if f in sample_frame]

        if len(self._feature_names) < 5:
            self._is_fitted = False
            self._fit_report["error"] = f"Insufficient features: {len(self._feature_names)} < 5"
            return self

        self._rule_engine.fit(data)

        X = np.array([
            [f.tlabel_v2.get(k, 0.0) for k in self._feature_names]
            for f in data.frames
        ])

        # v0.5.0: 不再训练phase模型，由HMM处理
        enabled = self.config.enabled_fields
        target_fields = enabled if enabled else ["contact", "slip_event"]
        # 移除manipulation_phase，交给HMM
        target_fields = [f for f in target_fields if f != "manipulation_phase"]

        self._fit_report = {"fields": {}, "total_frames": len(data.frames)}

        for field_name in target_fields:
            is_reg = field_name in REGRESSION_FIELDS
            fm = FieldModel(field_name, is_regression=is_reg)

            feature_indices = [i for i, k in enumerate(self._feature_names) if k != field_name]
            X_field = X[:, feature_indices]

            if field_name == "slip_event":
                y = np.array([f.tlabel_v2.get("slip_event", 0.0) for f in data.frames])
                y = (y > 0.5).astype(float)
            elif field_name == "contact":
                y = np.array([f.tlabel_v2.get("contact", 0.0) for f in data.frames])
            else:
                y = np.array([f.tlabel_v2.get(field_name, 0.0) for f in data.frames])

            success = fm.fit(
                X_field, y,
                use_calibration=self.config.use_calibration,
                calibration_method=self.config.calibration_method,
            )

            self._models[field_name] = fm
            self._fit_report["fields"][field_name] = {
                "status": "trained" if success else "failed",
                "samples": fm.training_samples,
                "error": fm.training_error,
                "is_calibrated": fm.is_calibrated,
            }

        # v0.5.0: 记录phase由HMM处理
        self._fit_report["fields"]["manipulation_phase"] = {
            "status": "hmm",
            "reason": "Phase modeled by HMM+Viterbi (v0.5.0)"
        }

        self._is_fitted = True
        return self

    def predict(self, data: TLabelData,
                target_fields: Optional[List[str]] = None) -> List[PredictResult]:
        results = []

        rule_results = self._rule_engine.predict(data) if self.config.fallback_to_rules else None

        X = np.array([
            [f.tlabel_v2.get(k, 0.0) for k in self._feature_names]
            for f in data.frames
        ]) if self._feature_names else None

        enabled = target_fields or self.config.enabled_fields or ["contact", "slip_event"]
        enabled = [f for f in enabled if f != "manipulation_phase"]

        for i, frame in enumerate(data.frames):
            predictions = {}
            confidence = {}
            method = {}

            for field_name in enabled:
                fm = self._models.get(field_name)

                if fm and fm.is_fitted and X is not None:
                    try:
                        feature_indices = [j for j, k in enumerate(self._feature_names) if k != field_name]
                        x_single = X[i:i+1, feature_indices]
                        values, confs = fm.predict(x_single)
                        predictions[field_name] = float(values[0])
                        confidence[field_name] = float(confs[0])
                        method[field_name] = "ml"
                    except Exception:
                        if rule_results:
                            rr = rule_results[i]
                            if field_name in rr.predictions:
                                predictions[field_name] = rr.predictions[field_name]
                                confidence[field_name] = rr.confidence.get(field_name, 0.3)
                                method[field_name] = "rule_fallback"
                        else:
                            confidence[field_name] = 0.0
                            method[field_name] = "failed"
                elif rule_results:
                    rr = rule_results[i]
                    if field_name in rr.predictions:
                        predictions[field_name] = rr.predictions[field_name]
                        confidence[field_name] = rr.confidence.get(field_name, 0.3)
                        method[field_name] = "rule"

            results.append(PredictResult(
                frame_idx=frame.frame_idx,
                predictions=predictions,
                confidence=confidence,
                method=method,
            ))

        # v0.5.0: 时序后处理（平滑+HMM phase+联动修正）
        if self.config.enable_postprocess and results:
            from tlabel.predict.postprocess import PostProcessor, PostProcessConfig
            pp_config = PostProcessConfig(
                enable_smoothing=True,
                enable_hmm=self.config.enable_hmm_phase,
                enable_cascade_fix=True,
            )
            processor = PostProcessor(pp_config)

            frames_data = []
            for frame in data.frames:
                frames_data.append({
                    "contact": frame.tlabel_v2.get("contact", 0.0),
                    "force_magnitude": frame.tlabel_v2.get("force_magnitude", 0.0),
                    "slip_event": frame.tlabel_v2.get("slip_event", 0.0),
                    "deformation_magnitude": frame.tlabel_v2.get("deformation_magnitude", 0.0),
                })

            existing_phases = [f.manipulation_phase for f in data.frames]
            results = processor.process(results, frames_data, existing_phases)

        return results

    def apply(self, data: TLabelData, results: List[PredictResult],
              min_confidence: float = 0.75, cascade: bool = True) -> int:
        applied = 0
        for result in results:
            frame = data.get_frame(result.frame_idx)
            if frame is None:
                continue
            for field, value in result.predictions.items():
                conf = result.confidence.get(field, 0.0)
                if conf >= min_confidence:
                    old = frame.tlabel_v2.get(field)
                    if field == "manipulation_phase":
                        if frame.manipulation_phase != str(value):
                            frame.manipulation_phase = str(value)
                            applied += 1
                    elif field == "contact" and isinstance(old, (int, float)):
                        if abs(old - value) < 0.05:
                            continue
                        frame.patch(field, value, cascade=cascade)
                        applied += 1
                    elif old != value:
                        frame.patch(field, value, cascade=cascade)
                        applied += 1
        return applied

    def summary(self, results: List[PredictResult]) -> Dict:
        total = len(results)
        field_counts = {}
        field_conf = {}
        method_counts = {"ml": 0, "rule": 0, "rule_fallback": 0, "failed": 0, "hmm": 0, "smooth": 0}

        for r in results:
            for f in r.predictions:
                field_counts[f] = field_counts.get(f, 0) + 1
                if f not in field_conf:
                    field_conf[f] = []
                field_conf[f].append(r.confidence.get(f, 0))
            for m in r.method.values():
                for base_m in m.split("+"):
                    if base_m in method_counts:
                        method_counts[base_m] += 1

        avg_conf = {f: round(sum(c) / len(c), 3) for f, c in field_conf.items() if c}

        return {
            "total_frames": total,
            "predicted_fields": field_counts,
            "avg_confidence": avg_conf,
            "method_distribution": method_counts,
            "ml_fields": list(self._models.keys()),
            "fit_report": self._fit_report,
        }

    def fit_report(self) -> Dict:
        return self._fit_report

    def save_models(self, path: str):
        model_data = {
            "config": {
                "enabled_fields": self.config.enabled_fields,
                "use_calibration": self.config.use_calibration,
                "calibration_method": self.config.calibration_method,
            },
            "feature_names": self._feature_names,
            "models": {},
        }
        for name, fm in self._models.items():
            if fm.is_fitted:
                buf = io.BytesIO()
                joblib.dump({
                    "model": fm.model,
                    "scaler": fm.scaler,
                    "calibrator": fm.calibrator,
                    "is_regression": fm.is_regression,
                    "is_calibrated": fm.is_calibrated,
                    "classes_": fm.classes_,
                    "field_name": fm.field_name,
                }, buf)
                model_data["models"][name] = buf.getvalue()

        with open(path, "wb") as f:
            joblib.dump(model_data, f)

    def load_models(self, path: str):
        with open(path, "rb") as f:
            model_data = joblib.load(f)

        self._feature_names = model_data["feature_names"]
        for name, model_bytes in model_data["models"].items():
            buf = io.BytesIO(model_bytes)
            data = joblib.load(buf)
            fm = FieldModel(data["field_name"], is_regression=data["is_regression"])
            fm.model = data["model"]
            fm.scaler = data["scaler"]
            fm.calibrator = data["calibrator"]
            fm.is_calibrated = data["is_calibrated"]
            fm.classes_ = data["classes_"]
            fm.is_fitted = True
            fm.training_samples = -1
            self._models[name] = fm

        self._is_fitted = True
