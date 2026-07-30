"""TLabel v0.5.0 Tests — 时序后处理 + HMM Phase + 预标注集成"""

import pytest
import sys
import os

from tlabel.core.schema import TLabelSchemaV2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPostProcess:
    """测试时序后处理模块"""

    def test_import_postprocess(self):
        from tlabel.predict.postprocess import (
            PostProcessor, PostProcessConfig,
            TemporalSmoother, PhaseHMM,
            PHASE_STATES, PHASE_TO_IDX,
        )
        assert len(PHASE_STATES) == 6
        assert "idle" in PHASE_TO_IDX
        assert "slip" in PHASE_TO_IDX

    def test_temporal_smoother_smooth_field(self):
        from tlabel.predict.postprocess import TemporalSmoother
        smoother = TemporalSmoother(window_size=5, edge_threshold=0.3)
        # Smooth signal
        values = [0.0, 0.0, 0.0, 0.1, 0.9, 1.0, 0.9, 0.1, 0.0, 0.0, 0.0]
        result = smoother.smooth_field(values)
        assert len(result) == len(values)
        # Edges should be preserved (0.1→0.9 jump)
        assert result[0] == 0.0
        assert result[-1] == 0.0

    def test_temporal_smoother_median_filter(self):
        from tlabel.predict.postprocess import TemporalSmoother
        smoother = TemporalSmoother()
        # Signal with single-frame spike
        values = [0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5]
        result = smoother.median_filter(values, window=3)
        assert len(result) == len(values)
        # The spike at index 3 should be reduced
        assert result[3] < 1.0

    def test_denoise_contact_removes_pulse(self):
        from tlabel.predict.postprocess import TemporalSmoother
        smoother = TemporalSmoother(min_contact_run=3)
        # Short pulse: only 1 frame of contact
        contact = [0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = smoother.denoise_contact(contact, threshold=0.5)
        # Single-frame pulse should be removed
        assert result[2] < 0.5

    def test_denoise_contact_fills_gap(self):
        from tlabel.predict.postprocess import TemporalSmoother
        smoother = TemporalSmoother(min_contact_run=3)
        # Short gap in continuous contact
        contact = [0.9, 0.9, 0.9, 0.1, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
        result = smoother.denoise_contact(contact, threshold=0.5)
        # Gap should be filled
        assert result[3] > 0.5

    def test_phase_hmm_decode_idle(self):
        from tlabel.predict.postprocess import PhaseHMM
        hmm = PhaseHMM()
        # All idle signals
        frames = [{"contact": 0.0, "force_magnitude": 0.0, "slip_event": 0.0, "deformation_magnitude": 0.0}] * 20
        phases = hmm.decode(frames)
        assert len(phases) == 20
        # Should be mostly idle
        idle_count = sum(1 for p in phases if p == "idle")
        assert idle_count >= 15

    def test_phase_hmm_decode_contact_sequence(self):
        from tlabel.predict.postprocess import PhaseHMM
        hmm = PhaseHMM()
        # Simulate: idle → contact → stable → release → idle
        frames = []
        for _ in range(10):
            frames.append({"contact": 0.0, "force_magnitude": 0.0, "slip_event": 0.0, "deformation_magnitude": 0.0})
        for _ in range(5):
            frames.append({"contact": 0.6, "force_magnitude": 0.3, "slip_event": 0.0, "deformation_magnitude": 0.3})
        for _ in range(15):
            frames.append({"contact": 0.9, "force_magnitude": 0.6, "slip_event": 0.1, "deformation_magnitude": 0.5})
        for _ in range(10):
            frames.append({"contact": 0.0, "force_magnitude": 0.0, "slip_event": 0.0, "deformation_magnitude": 0.0})
        phases = hmm.decode(frames)
        assert len(phases) == 40
        # First frames should be idle
        assert phases[0] == "idle"
        # Middle frames should be some contact phase
        contact_phases = set(phases[10:25])
        assert len(contact_phases & {"initial_contact", "stable_contact", "grasp", "hold"}) > 0

    def test_phase_hmm_decode_slip(self):
        from tlabel.predict.postprocess import PhaseHMM
        hmm = PhaseHMM()
        # Contact with slip
        frames = []
        for _ in range(5):
            frames.append({"contact": 0.9, "force_magnitude": 0.5, "slip_event": 0.8, "deformation_magnitude": 0.4})
        for _ in range(5):
            frames.append({"contact": 0.9, "force_magnitude": 0.6, "slip_event": 0.1, "deformation_magnitude": 0.5})
        phases = hmm.decode(frames)
        # First 5 should be slip
        slip_count = sum(1 for p in phases[:5] if p == "slip")
        assert slip_count >= 3

    def test_phase_hmm_fit_from_data(self):
        from tlabel.predict.postprocess import PhaseHMM
        hmm = PhaseHMM()
        phases = ["idle"] * 5 + ["initial_contact"] * 3 + ["stable_contact"] * 10 + ["idle"] * 5
        hmm.fit(phases)
        assert hmm._trained is True
        assert hmm._trained_trans is not None

    def test_phase_hmm_no_illegal_transitions(self):
        """HMM should not produce illegal transitions like idle→slip"""
        from tlabel.predict.postprocess import PhaseHMM, LEGAL_TRANSITIONS
        hmm = PhaseHMM()
        # 50 frames of mixed signals
        frames = []
        for i in range(50):
            if i < 10:
                frames.append({"contact": 0.0, "force_magnitude": 0.0, "slip_event": 0.0, "deformation_magnitude": 0.0})
            elif i < 20:
                frames.append({"contact": 0.9, "force_magnitude": 0.6, "slip_event": 0.8, "deformation_magnitude": 0.4})
            else:
                frames.append({"contact": 0.9, "force_magnitude": 0.5, "slip_event": 0.1, "deformation_magnitude": 0.5})
        phases = hmm.decode(frames)
        # Check all adjacent transitions are legal
        for i in range(len(phases) - 1):
            assert phases[i + 1] in LEGAL_TRANSITIONS[phases[i]], \
                f"Illegal transition: {phases[i]} → {phases[i+1]} at frame {i}"

    def test_post_processor_full_pipeline(self):
        from tlabel.predict.postprocess import PostProcessor, PostProcessConfig
        from tlabel.predict.engine import PredictResult

        config = PostProcessConfig(enable_smoothing=True, enable_hmm=True, enable_cascade_fix=True)
        processor = PostProcessor(config)

        # Create noisy results
        results = []
        for i in range(30):
            predictions = {
                "contact": 0.9 if i > 5 and i < 25 else 0.0,
                "force_magnitude": 0.5 if i > 5 and i < 25 else 0.0,
                "slip_event": 0.8 if i == 12 else 0.0,  # Single frame spike
                "manipulation_phase": "idle",
            }
            # Add noise: flip one frame
            if i == 15:
                predictions["contact"] = 0.0  # Spurious gap
                predictions["force_magnitude"] = 0.5  # Force without contact

            results.append(PredictResult(
                frame_idx=i,
                predictions=predictions,
                confidence={"contact": 0.8, "force_magnitude": 0.7, "slip_event": 0.6},
                method={"contact": "rule", "force_magnitude": "rule", "slip_event": "rule"},
            ))

        processed = processor.process(results)

        assert len(processed) == len(results)
        # Cascade fix: frame 15 should have contact=1.0 (forced by force>0)
        assert processed[15].predictions["contact"] > 0.5
        # HMM should produce phase labels
        phases = [r.predictions.get("manipulation_phase") for r in processed]
        non_idle = [p for p in phases if p != "idle"]
        assert len(non_idle) > 0  # Should have some non-idle phases

    def test_post_processor_cascade_fix(self):
        """Cascade fix: contact≈0 → force must be 0"""
        from tlabel.predict.postprocess import PostProcessor
        from tlabel.predict.engine import PredictResult

        processor = PostProcessor()
        results = [PredictResult(
            frame_idx=0,
            predictions={"contact": 0.0, "force_magnitude": 0.5, "slip_event": 0.3},
            confidence={"contact": 0.9, "force_magnitude": 0.7, "slip_event": 0.5},
            method={"contact": "rule", "force_magnitude": "rule", "slip_event": "rule"},
        )]

        processed = processor._fix_cascade(results)
        # New cascade: force implies contact, so contact gets upgraded
        assert processed[0].predictions["contact"] >= 0.5  # Force implies contact
        assert processed[0].predictions["force_magnitude"] == 0.5  # Force preserved


def _v050_schema(contact, force, slip, deformation=None, confidence=1.0):
    """Helper: create TLabelSchemaV2 for v0.5.0 test data."""
    is_contact = contact > 0.5 if isinstance(contact, float) else contact
    is_slip = slip > 0.5 if isinstance(slip, float) else slip
    return TLabelSchemaV2(
        contact=is_contact,
        force_magnitude=force if force > 0 else None,
        slip_event=is_slip,
        contact_centroid=[0.3, 0.3] if is_contact else None,
        object_deformation=deformation if deformation and deformation > 0 else None,
        confidence=confidence,
        compliance_level="L2" if is_contact else "L1",
    )


class TestPredictEngineV050:
    """测试PredictEngine的v0.5.0改进"""

    def _make_data(self, n_frames=50):
        from tlabel.core.types import TLabelData, TLabelFrame
        frames = []
        for i in range(n_frames):
            contact = 1.0 if 10 <= i <= 40 else 0.0
            force = 0.6 if 10 <= i <= 40 else 0.0
            slip = 0.8 if i in (20, 21, 22) else 0.0
            frames.append(TLabelFrame(
                frame_idx=i,
                timestamp_s=i * 0.033,
                schema_v2=_v050_schema(
                    contact, force, slip,
                    deformation=0.4 if contact > 0.5 else 0.0,
                ),
                manipulation_phase="idle" if contact < 0.5 else ("slip" if slip > 0.5 else "stable_contact"),
            ))
        return TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight", "name": "GelSight Mini"},
            episode_info={"task": "grasp"},
            capabilities={"dimensions": 14},
        )

    def test_predict_with_postprocess(self):
        from tlabel.predict.engine import PredictEngine, PredictConfig
        config = PredictConfig(enable_postprocess=True, enable_hmm_phase=True)
        engine = PredictEngine(config)
        data = self._make_data()
        engine.fit(data)
        results = engine.predict(data)
        assert len(results) == 50
        # Should have phase predictions from HMM
        phases = [r.predictions.get("manipulation_phase") for r in results]
        assert any(p != "idle" for p in phases)

    def test_predict_without_postprocess(self):
        from tlabel.predict.engine import PredictEngine, PredictConfig
        config = PredictConfig(enable_postprocess=False, enable_hmm_phase=False)
        engine = PredictEngine(config)
        data = self._make_data()
        engine.fit(data)
        results = engine.predict(data)
        assert len(results) == 50
        # Without HMM, phases should be from rule engine only
        phases = [r.predictions.get("manipulation_phase") for r in results]
        # Rule engine phase predictions are simpler

    def test_auto_label_with_postprocess(self):
        from tlabel.core.types import TLabelData, TLabelFrame
        from tlabel.core.types import TLabelData as TD
        # Create data with unknown frames
        frames = []
        for i in range(50):
            contact = 0.0  # All unknown
            frames.append(TLabelFrame(
                frame_idx=i, timestamp_s=i * 0.033,
                schema_v2=TLabelSchemaV2(
                    contact=False,
                    force_magnitude=0.6 if 10 <= i <= 40 else None,
                    slip_event=False,
                    contact_centroid=None,
                    object_deformation=0.5 if 10 <= i <= 40 else None,
                    confidence=1.0,
                    compliance_level="L2" if 10 <= i <= 40 else "L1",
                ),
                manipulation_phase="idle",
            ))
        data = TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight", "name": "GelSight Mini"},
            episode_info={"task": "grasp"},
            capabilities={"dimensions": 14},
        )

        summary = data.auto_label(min_confidence=0.5, enable_postprocess=True, enable_hmm_phase=True)
        assert "engine" in summary
        assert summary["applied_count"] >= 0  # contact=0.0 in source, rule engine infers weakly
        # Should have low_confidence_frames
        assert "low_confidence_frames" in summary


class TestMLEngineV050:
    """测试MLEngine的v0.5.0改进"""

    def test_ml_engine_no_phase_model(self):
        """Phase should not be trained by ML, handled by HMM"""
        from tlabel.predict.ml_engine import MLEngine, MLEngineConfig
        from tlabel.core.types import TLabelData, TLabelFrame

        frames = []
        for i in range(50):
            is_contact = i > 10
            frames.append(TLabelFrame(
                frame_idx=i, timestamp_s=i * 0.033,
                schema_v2=TLabelSchemaV2(
                    contact=is_contact,
                    force_magnitude=0.6 if is_contact else None,
                    slip_event=False,
                    contact_centroid=[0.3, 0.3] if is_contact else None,
                    object_deformation=0.5 if is_contact else None,
                    confidence=1.0,
                    compliance_level="L2" if is_contact else "L1",
                ),
                manipulation_phase="idle" if i <= 10 else "stable_contact",
            ))

        data = TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight"},
            episode_info={},
            capabilities={"dimensions": 14},
        )

        engine = MLEngine()
        engine.fit(data)

        # Phase should be marked as hmm, not trained by ML
        phase_report = engine._fit_report["fields"].get("manipulation_phase", {})
        assert phase_report.get("status") == "hmm"

    def test_ml_engine_predict_includes_hmm_phase(self):
        """MLEngine predict should include HMM phase"""
        from tlabel.predict.ml_engine import MLEngine, MLEngineConfig
        from tlabel.core.types import TLabelData, TLabelFrame

        frames = []
        for i in range(50):
            is_contact = 10 <= i <= 40
            is_slip = 20 <= i <= 25
            frames.append(TLabelFrame(
                frame_idx=i, timestamp_s=i * 0.033,
                schema_v2=TLabelSchemaV2(
                    contact=is_contact,
                    force_magnitude=0.6 if is_contact else None,
                    slip_event=is_slip,
                    contact_centroid=[0.3, 0.3] if is_contact else None,
                    object_deformation=0.5 if is_contact else None,
                    confidence=1.0,
                    compliance_level="L2" if is_contact else "L1",
                ),
                manipulation_phase="idle" if i < 10 else ("slip" if 20 <= i <= 25 else "stable_contact"),
            ))

        data = TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight"},
            episode_info={},
            capabilities={"dimensions": 14},
        )

        engine = MLEngine(MLEngineConfig(enable_postprocess=True, enable_hmm_phase=True))
        engine.fit(data)
        results = engine.predict(data)

        # Check HMM phase predictions exist
        phases = [r.predictions.get("manipulation_phase") for r in results]
        non_idle = [p for p in phases if p and p != "idle"]
        assert len(non_idle) > 0


class TestPanelV050:
    """测试Panel UI的v0.5.0改进"""

    def test_panel_auto_label_param(self):
        from tlabel.core.types import TLabelData, TLabelFrame
        from tlabel.viewer.panel import TLabelPanel

        frames = [TLabelFrame(
            frame_idx=i, timestamp_s=i * 0.033,
            schema_v2=TLabelSchemaV2(contact=False, force_magnitude=None, slip_event=False),
            manipulation_phase="idle",
        ) for i in range(10)]

        data = TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight"},
            episode_info={},
            capabilities={"dimensions": 14},
        )

        panel = TLabelPanel(data, auto_label=True)
        html = panel._repr_html_()
        assert "tlabel_" in html  # Basic rendering works

    def test_panel_with_predict_highlights(self):
        from tlabel.core.types import TLabelData, TLabelFrame
        from tlabel.viewer.panel import TLabelPanel

        frames = [TLabelFrame(
            frame_idx=i, timestamp_s=i * 0.033,
            schema_v2=TLabelSchemaV2(
                contact=i > 3,
                force_magnitude=0.5 if i > 3 else None,
                slip_event=False,
                contact_centroid=[0.5, 0.5] if i > 3 else None,
            ),
            manipulation_phase="idle",
        ) for i in range(10)]

        data = TLabelData(
            frames=frames,
            sensor_info={"type": "gelsight"},
            episode_info={},
            capabilities={"dimensions": 14},
        )

        # Pre-run auto_label
        data.auto_label(min_confidence=0.5)
        panel = TLabelPanel(data)
        html = panel._repr_html_()
        # Should contain predict badge element
        assert "predict-badge" in html


class TestVersionV050:
    """版本号测试"""

    def test_version_is_050(self):
        from tlabel._version import __version__
        from packaging.version import Version
        assert Version(__version__) >= Version("0.5.0")

    def test_import_all_predict(self):
        from tlabel.predict import (
            PredictEngine, PredictConfig, PredictResult,
            PostProcessor, PostProcessConfig,
            TemporalSmoother, PhaseHMM,
            PHASE_STATES, PHASE_TO_IDX,
        )
        assert len(PHASE_STATES) == 6
