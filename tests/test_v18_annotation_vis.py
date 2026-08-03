#!/usr/bin/env python3
"""
v0.18 #4 + #5: Primitive/Event 标注集成 + 触觉可视化 测试

覆盖:
  #4 Primitive+Event:
  - validate_annotations(): 校验一致性
  - annotate_from_taxonomy(): 批量预标注
  - annotate_events_from_data(): 自动事件检测
  - clear_annotations(): 清除标注
  - get_annotation_summary(): 统一查询
  - TLabelData 便捷方法集成

  #5 触觉可视化:
  - contact_heatmap(): 热力图
  - force_vector_field(): 向量场
  - contact_region_overlay(): 区域高亮
  - composite_view(): 组合视图
  - text_summary(): 文本降级
  - visualize_frame(): 自动降级
  - frame_animation(): 动画
"""

import sys
import os
import math
import traceback
import numpy as np
from pathlib import Path

# 确保 tlabel 在 sys.path 上
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ============================================================================
# 测试结果收集
# ============================================================================

test_results = {}
issues_found = []


def record_test(test_name: str, passed: bool, details: str):
    test_results[test_name] = {"passed": passed, "details": details}
    status = "✅" if passed else "❌"
    print(f"  {status} {test_name}: {details}")
    if not passed:
        issues_found.append(f"{test_name}: {details}")


# ============================================================================
# 辅助工具
# ============================================================================

def make_test_data(num_frames: int = 20, with_contact: bool = True):
    """创建测试用 TLabelData"""
    from tlabel.core.types import TLabelData, TLabelFrame
    from tlabel.core.schema import TLabelSchemaV2

    frames = []
    for i in range(num_frames):
        # 模拟接触 → 稳定 → 释放的过程
        if with_contact:
            if i < 5:
                contact = False
                force = 0.0
            elif i < 15:
                contact = True
                force = 0.3 + 0.1 * math.sin(i * 0.5)
            else:
                contact = False
                force = 0.0
        else:
            contact = False
            force = 0.0

        sv2 = TLabelSchemaV2(
            contact=contact,
            force_magnitude=round(force, 4),
            slip_event=(i == 10),  # 中间一帧 slip
            confidence=0.9,
            compliance_level="L2",
            contact_centroid=[0.5, 0.5] if contact else None,
        )

        # 模拟触觉图像
        h, w = 32, 32
        image = np.random.randint(0, 50, (h, w, 3), dtype=np.uint8)
        if contact:
            # 中心区域加亮
            cy, cx = h // 2, w // 2
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if 0 <= cy + dy < h and 0 <= cx + dx < w:
                        image[cy + dy, cx + dx] = [200, 100, 50]

        frame = TLabelFrame(
            frame_idx=i,
            timestamp_s=i * 0.033,
            schema_v2=sv2,
            confidence=0.9,
            image=image,
        )
        frames.append(frame)

    return TLabelData(
        frames=frames,
        sensor_info={"type": "test_sensor", "manufacturer": "test"},
        episode_info={"source": "test"},
        capabilities={"contact": True, "force_magnitude": True},
    )


# ============================================================================
# Test 1: validate_annotations()
# ============================================================================

def test_validate_annotations():
    """测试标注校验"""
    print("\n[Test 1] validate_annotations()")

    data = make_test_data(20)

    # 1a. 空标注应该通过
    result = data.validate_annotations()
    record_test("empty annotations valid",
                result["valid"] is True,
                f"valid={result['valid']}, errors={result['errors']}")
    record_test("empty stats correct",
                result["stats"]["num_primitive_annotations"] == 0,
                f"stats={result['stats']}")

    # 1b. 添加合法标注
    data.add_primitive("grasp", 5, 14, confidence=0.8, source="ai_predicted")
    data.add_event("contact_onset", 5, source="ai_predicted")
    result = data.validate_annotations()
    record_test("valid annotations pass",
                result["valid"] is True,
                f"valid={result['valid']}, errors={result['errors']}")
    record_test("stats count correct",
                result["stats"]["num_primitive_annotations"] == 1
                and result["stats"]["num_tactile_events"] == 1,
                f"stats={result['stats']}")

    # 1c. 非法 primitive 名称
    data2 = make_test_data(20)
    from tlabel.core.primitive import PrimitiveAnnotation
    # 手动添加一个无效标注（绕过构造函数验证）
    ann = PrimitiveAnnotation.__new__(PrimitiveAnnotation)
    ann.primitive_name = "invalid_primitive"
    ann.start_frame = 0
    ann.end_frame = 5
    ann.confidence = 0.8
    ann.source = "manual"
    data2.primitive_annotations.append(ann)
    result = data2.validate_annotations()
    record_test("invalid primitive detected",
                result["valid"] is False and len(result["errors"]) > 0,
                f"errors={result['errors'][:2]}")


# ============================================================================
# Test 2: annotate_from_taxonomy()
# ============================================================================

def test_annotate_from_taxonomy():
    """测试批量 taxonomy 预标注"""
    print("\n[Test 2] annotate_from_taxonomy()")

    data = make_test_data(20, with_contact=True)

    # 应用默认 taxonomy
    count = data.annotate_from_taxonomy(min_confidence=0.3, clear_existing=True)
    record_test("taxonomy annotation produces results",
                count > 0,
                f"annotated {count} primitives")

    # 验证标注
    result = data.validate_annotations()
    record_test("taxonomy annotations valid",
                result["valid"] is True,
                f"valid={result['valid']}, errors={result['errors']}")

    # 检查是否有 reach (无接触帧) 和 grasp/press (有接触帧)
    prim_names = set(p.primitive_name for p in data.primitive_annotations)
    record_test("taxonomy detects reach",
                "reach" in prim_names,
                f"primitives found: {prim_names}")


# ============================================================================
# Test 3: annotate_events_from_data()
# ============================================================================

def test_annotate_events():
    """测试自动事件检测"""
    print("\n[Test 3] annotate_events_auto()")

    data = make_test_data(20, with_contact=True)

    count = data.annotate_events_auto(clear_existing=True)
    record_test("event detection produces results",
                count > 0,
                f"detected {count} events")

    # 检查 contact_onset 和 contact_loss
    event_types = set(e.event_type for e in data.tactile_events)
    record_test("contact_onset detected",
                "contact_onset" in event_types,
                f"events found: {event_types}")
    record_test("contact_loss detected",
                "contact_loss" in event_types,
                f"events found: {event_types}")

    # 验证
    result = data.validate_annotations()
    record_test("events valid",
                result["valid"] is True,
                f"valid={result['valid']}, errors={result['errors']}")


# ============================================================================
# Test 4: clear_annotations()
# ============================================================================

def test_clear_annotations():
    """测试清除标注"""
    print("\n[Test 4] clear_annotations()")

    data = make_test_data(20)
    data.add_primitive("grasp", 5, 14)
    data.add_event("contact_onset", 5)

    result = data.clear_annotations()
    record_test("clear returns counts",
                result["cleared_primitives"] == 1 and result["cleared_events"] == 1,
                f"result={result}")
    record_test("annotations cleared",
                len(data.primitive_annotations) == 0 and len(data.tactile_events) == 0,
                f"primitives={len(data.primitive_annotations)}, events={len(data.tactile_events)}")


# ============================================================================
# Test 5: get_annotation_summary()
# ============================================================================

def test_annotation_summary():
    """测试标注摘要"""
    print("\n[Test 5] get_annotation_summary()")

    data = make_test_data(20)
    data.add_primitive("grasp", 5, 14, confidence=0.8)
    data.add_event("contact_onset", 5)

    summary = data.get_annotation_summary()
    record_test("summary has all keys",
                all(k in summary for k in ["primitives", "events", "timeline", "validation"]),
                f"keys={list(summary.keys())}")
    record_test("summary primitives count",
                len(summary["primitives"]) == 1,
                f"count={len(summary['primitives'])}")
    record_test("summary events count",
                len(summary["events"]) == 1,
                f"count={len(summary['events'])}")
    record_test("summary timeline non-empty",
                len(summary["timeline"]) > 0,
                f"timeline_len={len(summary['timeline'])}")


# ============================================================================
# Test 6: contact_heatmap()
# ============================================================================

def test_contact_heatmap():
    """测试接触热力图"""
    print("\n[Test 6] contact_heatmap()")

    from tlabel.viewer.tactile_vis import contact_heatmap

    # 创建测试图像
    img = np.zeros((64, 64, 3), dtype=np.uint8)

    # 6a. 有 intensity
    intensity = np.zeros((64, 64), dtype=np.float32)
    intensity[20:44, 20:44] = 0.8
    result = contact_heatmap(img, intensity=intensity)
    record_test("heatmap with intensity",
                result is not None and result.shape == (64, 64, 3),
                f"shape={result.shape if result is not None else None}")

    # 6b. 有 contact_mask
    mask = np.zeros((64, 64), dtype=bool)
    mask[10:50, 10:50] = True
    result = contact_heatmap(img, contact_mask=mask)
    record_test("heatmap with mask",
                result is not None and result.shape == (64, 64, 3),
                f"shape={result.shape if result is not None else None}")

    # 6c. 无输入返回原图
    result = contact_heatmap(img)
    record_test("heatmap no input returns original",
                result is not None and np.array_equal(result, img),
                f"same={np.array_equal(result, img) if result is not None else False}")


# ============================================================================
# Test 7: force_vector_field()
# ============================================================================

def test_force_vector_field():
    """测试力向量场"""
    print("\n[Test 7] force_vector_field()")

    from tlabel.viewer.tactile_vis import force_vector_field

    img = np.zeros((64, 64, 3), dtype=np.uint8)

    # (H, W, 2) 格式
    vectors = np.zeros((64, 64, 2), dtype=np.float32)
    vectors[32, 32] = [0.5, -0.3]  # 中心一个向量
    result = force_vector_field(img, vectors, grid_size=8)
    record_test("vector field (H,W,2)",
                result is not None and result.shape == (64, 64, 3),
                f"shape={result.shape if result is not None else None}")

    # (N, 4) 格式
    vectors_grid = np.array([[32, 32, 0.5, -0.3]], dtype=np.float32)
    result = force_vector_field(img, vectors_grid)
    record_test("vector field (N,4)",
                result is not None and result.shape == (64, 64, 3),
                f"shape={result.shape if result is not None else None}")


# ============================================================================
# Test 8: contact_region_overlay()
# ============================================================================

def test_contact_region_overlay():
    """测试接触区域高亮"""
    print("\n[Test 8] contact_region_overlay()")

    from tlabel.viewer.tactile_vis import contact_region_overlay

    img = np.zeros((64, 64, 3), dtype=np.uint8)

    # 归一化坐标
    result = contact_region_overlay(img, contact_centroid=[0.5, 0.5])
    record_test("overlay normalized coords",
                result is not None and result.shape == (64, 64, 3),
                f"shape={result.shape if result is not None else None}")

    # 检查圆上有红色像素（非填充模式，圆心可能为空）
    # centroid [0.5, 0.5] → pixel (32, 32), radius=15
    # 圆上某点: (32+15, 32) = (47, 32)
    has_red = False
    for y in range(30, 50):
        for x in range(30, 50):
            if result[y, x, 0] > 0:
                has_red = True
                break
        if has_red:
            break
    record_test("overlay draws circle",
                has_red,
                f"region has_red={has_red}")


# ============================================================================
# Test 9: text_summary()
# ============================================================================

def test_text_summary():
    """测试文本降级"""
    print("\n[Test 9] text_summary()")

    from tlabel.viewer.tactile_vis import text_summary

    data = make_test_data(20)
    frame = data.frames[10]  # 接触帧 (frames 5-14 have contact)

    text = text_summary(frame)
    record_test("text summary generated",
                isinstance(text, str) and len(text) > 0,
                f"len={len(text)}")
    record_test("text contains contact",
                "contact" in text.lower(),
                f"text preview: {text[:100]}")


# ============================================================================
# Test 10: visualize_frame() 自动降级
# ============================================================================

def test_visualize_frame():
    """测试自动降级可视化"""
    print("\n[Test 10] visualize_frame()")

    from tlabel.viewer.tactile_vis import visualize_frame

    data = make_test_data(20)

    # 有图像的帧 → Level 1
    frame_with_img = data.frames[10]
    result = visualize_frame(frame_with_img)
    record_test("visualize with image → Level 1",
                isinstance(result, np.ndarray) and result.ndim == 3,
                f"type={type(result).__name__}, shape={result.shape if isinstance(result, np.ndarray) else None}")

    # 无图像的帧 → Level 3
    from tlabel.core.types import TLabelFrame
    from tlabel.core.schema import TLabelSchemaV2
    frame_no_img = TLabelFrame(
        frame_idx=0, timestamp_s=0.0,
        schema_v2=TLabelSchemaV2(contact=True, force_magnitude=0.5),
    )
    result = visualize_frame(frame_no_img)
    record_test("visualize no image → Level 3 text",
                isinstance(result, str),
                f"type={type(result).__name__}")


# ============================================================================
# Test 11: composite_view()
# ============================================================================

def test_composite_view():
    """测试组合视图"""
    print("\n[Test 11] composite_view()")

    from tlabel.viewer.tactile_vis import composite_view

    data = make_test_data(20)
    frame = data.frames[10]  # 有接触、有图像

    result = composite_view(frame)
    record_test("composite view returns image",
                result is not None and isinstance(result, np.ndarray),
                f"type={type(result).__name__}, shape={result.shape if result is not None else None}")


# ============================================================================
# 主流程
# ============================================================================

def main():
    print("=" * 60)
    print("TLabel v0.18 #4+#5: Annotation + Visualization Tests")
    print("=" * 60)

    tests = [
        ("Test 1 (validate)", test_validate_annotations),
        ("Test 2 (taxonomy)", test_annotate_from_taxonomy),
        ("Test 3 (events)", test_annotate_events),
        ("Test 4 (clear)", test_clear_annotations),
        ("Test 5 (summary)", test_annotation_summary),
        ("Test 6 (heatmap)", test_contact_heatmap),
        ("Test 7 (vectors)", test_force_vector_field),
        ("Test 8 (overlay)", test_contact_region_overlay),
        ("Test 9 (text)", test_text_summary),
        ("Test 10 (auto-level)", test_visualize_frame),
        ("Test 11 (composite)", test_composite_view),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as e:
            record_test(name, False, f"Exception: {e}\n{traceback.format_exc()[:500]}")

    # 汇总
    print("\n" + "=" * 60)
    passed = sum(1 for v in test_results.values() if v["passed"])
    failed = sum(1 for v in test_results.values() if not v["passed"])
    total = len(test_results)
    print(f"总计: {total} 项测试, {passed} 通过, {failed} 失败")

    if issues_found:
        print("\n失败项:")
        for issue in issues_found:
            print(f"  ❌ {issue}")
        sys.exit(1)
    else:
        print("\n✅ 所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
