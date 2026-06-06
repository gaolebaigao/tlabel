"""Generate synthetic demo data for TouchLabel AI examples."""
import numpy as np
import pickle
import json
from pathlib import Path

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

def _make_tlabel_v2(frame_idx, t, sensor="gelsight"):
    """Synthesize a single frame's 22-dim (or 20-dim) tlabel_v2."""
    # Simulate a grasp-hold-release pattern over ~3 seconds
    phase_t = t % 3.0
    if phase_t < 0.5:
        contact, phase = 0.0, "idle"
    elif phase_t < 1.0:
        contact, phase = min((phase_t - 0.5) * 4, 1.0), "initial_contact"
    elif phase_t < 2.2:
        contact, phase = 1.0, "stable_contact"
    elif phase_t < 2.6:
        contact, phase = max(1.0 - (phase_t - 2.2) * 2.5, 0.0), "idle"
    else:
        contact, phase = 0.0, "idle"

    slip = 1.0 if (1.5 < phase_t < 1.8 and contact > 0.5) else 0.0
    force = contact * (0.3 + 0.5 * np.sin(t * 2.1)) if contact > 0 else 0.0
    deformation = contact * (0.2 + 0.3 * np.abs(np.sin(t * 1.7)))

    d = {
        "contact": round(contact, 4),
        "deformation_magnitude": round(deformation, 4),
        "force_magnitude": round(force, 4),
        "force_peak": round(force * 1.3, 4),
        "force_direction": round(contact * (45 + 20 * np.sin(t * 0.9)), 4),
        "slip_entropy": round(0.1 * slip, 4),
        "slip_event": round(slip, 4),
        "texture_energy": round(contact * (0.5 + 0.2 * np.sin(t * 3.1)), 4),
        "edge_density": round(contact * (0.3 + 0.15 * np.sin(t * 2.3)), 4),
        "contact_area": round(contact * (0.6 + 0.2 * np.sin(t * 1.1)), 4),
        "centroid_x": round(contact * (0.45 + 0.05 * np.sin(t * 1.5)), 4),
        "normal_field_magnitude": round(contact * (0.7 + 0.2 * np.sin(t * 1.3)), 4),
        "normal_field_variance": round(contact * (0.15 + 0.05 * np.cos(t * 2.0)), 4),
        "shear_field_magnitude": round(contact * slip * 0.5, 4),
        "shear_field_direction": round(contact * (90 + 30 * np.sin(t * 1.8)), 4),
        "delta_force_normal": round(contact * 0.1 * np.sin(t * 5.0), 4),
        "delta_force_shear": round(contact * slip * 0.05, 4),
        "friction_cone_ratio": round(contact * (0.8 + 0.1 * np.cos(t * 1.2)), 4),
    }

    # Temporal dims (4-dim, v0.2.0)
    if sensor in ("gelsight", "daimon"):
        d["optical_flow_magnitude"] = round(contact * (0.4 + 0.2 * np.sin(t * 2.5)), 4)
        d["optical_flow_direction"] = round(contact * (30 + 15 * np.cos(t * 1.9)), 4)
    d["temporal_deformation_rate"] = round(contact * 0.15 * np.sin(t * 3.0), 4)
    d["contact_transition"] = round(
        1.0 if (abs(phase_t - 0.5) < 0.05 or abs(phase_t - 2.2) < 0.05) else 0.0, 4
    )

    return d, phase


def generate_gelsight_demo(n_frames=150):
    """Generate a small GelSight-style demo dataset."""
    frames = []
    for i in range(n_frames):
        t = i / 30.0  # 30 fps
        tlabel_v2, phase = _make_tlabel_v2(i, t, sensor="gelsight")
        frames.append({
            "frame_idx": i,
            "timestamp_s": round(t, 4),
            "tlabel_v2": tlabel_v2,
            "manipulation_phase": phase,
            "confidence": round(0.85 + 0.1 * np.random.random(), 2),
        })

    # Save as TLabel Format v2 JSON (portable, no pickle)
    data = {
        "schema_version": "0.4.0",
        "format": "tlabel_v2",
        "tlabel_dimensions": 22,
        "sensor": {
            "type": "gelsight_mini",
            "model": "GelSight Mini (Demo)",
            "resolution": "240x320",
        },
        "episode": {
            "description": "Synthetic grasp-hold-release demo (GelSight Mini)",
            "num_frames": n_frames,
            "duration_s": round(n_frames / 30.0, 2),
            "fps": 30,
        },
        "capabilities": {
            "has_image": True,
            "has_force": True,
            "has_optical_flow": True,
            "has_temporal": True,
            "dimensions": 22,
        },
        "frames": frames,
    }
    out_path = OUT / "demo_gelsight.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ GelSight demo: {out_path} ({n_frames} frames)")
    return data


def generate_paxini_demo(n_frames=120):
    """Generate a small Paxini-style demo dataset (20-dim, no optical flow)."""
    frames = []
    for i in range(n_frames):
        t = i / 30.0
        tlabel_v2, phase = _make_tlabel_v2(i, t, sensor="paxini")
        frames.append({
            "frame_idx": i,
            "timestamp_s": round(t, 4),
            "tlabel_v2": tlabel_v2,
            "manipulation_phase": phase,
            "confidence": round(0.80 + 0.15 * np.random.random(), 2),
        })

    data = {
        "schema_version": "0.4.0",
        "format": "tlabel_v2",
        "tlabel_dimensions": 20,
        "sensor": {
            "type": "paxini",
            "model": "PaXini PXCap (Demo)",
        },
        "episode": {
            "description": "Synthetic grasp demo (PaXini PXCap, 20-dim)",
            "num_frames": n_frames,
            "duration_s": round(n_frames / 30.0, 2),
            "fps": 30,
        },
        "capabilities": {
            "has_image": False,
            "has_force": True,
            "has_optical_flow": False,
            "has_temporal": True,
            "dimensions": 20,
        },
        "frames": frames,
    }
    out_path = OUT / "demo_paxini.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ PaXini demo: {out_path} ({n_frames} frames)")
    return data


if __name__ == "__main__":
    np.random.seed(42)
    g = generate_gelsight_demo()
    p = generate_paxini_demo()
    print(f"\nDone! Demo data in {OUT}/")
