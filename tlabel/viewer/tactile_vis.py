"""
触觉图像可视化 — v0.18 新增

提供多级可视化能力:
  Level 1 (Full):   完整热力图 + 力向量 + 接触区域 — 需要 numpy + cv2
  Level 2 (Simple): 灰度热力图 — 仅需 numpy
  Level 3 (Text):   纯文本描述 — 无依赖

可视化类型:
  - contact_heatmap():     接触热力图 (colormap overlay)
  - force_vector_field():  力向量场 (箭头图)
  - contact_region_overlay(): 接触区域高亮
  - frame_animation():     帧序列动画 (HTML/GIF)
  - composite_view():      组合视图 (热力图 + 向量场 + 区域)
"""

import io
import base64
import math
from typing import Optional, List, Dict, Tuple, Any

import numpy as np


# ============================================================
# 颜色映射
# ============================================================

# Jet colormap (近似) — 低值蓝 → 高值红
_JET_LUT = None


def _get_jet_lut(size: int = 256) -> np.ndarray:
    """获取 Jet colormap 查找表 (size, 3) uint8"""
    global _JET_LUT
    if _JET_LUT is not None and len(_JET_LUT) == size:
        return _JET_LUT

    x = np.linspace(0, 1, size)
    r = np.clip(1.5 - abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - abs(4 * x - 1), 0, 1)
    _JET_LUT = (np.stack([r, g, b], axis=1) * 255).astype(np.uint8)
    return _JET_LUT


def apply_colormap(gray: np.ndarray, cmap: str = "jet") -> np.ndarray:
    """将灰度图应用伪彩色映射

    Args:
        gray: (H, W) float 或 uint8，值域 0-1 或 0-255
        cmap: 颜色映射名称，目前支持 "jet", "hot", "coolwarm"

    Returns:
        (H, W, 3) uint8 RGB 图像
    """
    # 归一化到 0-255
    if gray.dtype == np.float32 or gray.dtype == np.float64:
        g_min, g_max = gray.min(), gray.max()
        if g_max > g_min:
            norm = ((gray - g_min) / (g_max - g_min) * 255).astype(np.uint8)
        else:
            norm = np.zeros_like(gray, dtype=np.uint8)
    else:
        norm = gray.astype(np.uint8)

    lut = _get_jet_lut(256)
    return lut[norm]


# ============================================================
# Level 1: 接触热力图
# ============================================================

def contact_heatmap(image: np.ndarray,
                    contact_mask: Optional[np.ndarray] = None,
                    intensity: Optional[np.ndarray] = None,
                    alpha: float = 0.6,
                    colormap: str = "jet") -> np.ndarray:
    """生成接触热力图

    Args:
        image: (H, W, 3) 原始触觉图像 (uint8 RGB)
        contact_mask: (H, W) bool 或 float，接触区域掩码
                     如果为 None，则使用 intensity 非零区域
        intensity: (H, W) float，接触强度（如压力值）。
                  如果为 None，则使用 contact_mask 作为二值强度
        alpha: 热力图叠加透明度 (0-1)
        colormap: 颜色映射名称

    Returns:
        (H, W, 3) uint8 RGB 热力图叠加图像
    """
    if image is None:
        return None

    h, w = image.shape[:2]
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)

    # 确定强度图
    if intensity is not None:
        if isinstance(intensity, (int, float)):
            # 标量强度值 → 创建均匀强度图
            strength = np.full((h, w), float(intensity), dtype=np.float32)
        else:
            strength = np.asarray(intensity, dtype=np.float32)
    elif contact_mask is not None:
        strength = contact_mask.astype(np.float32)
    else:
        # 无输入 → 返回原图
        return image.copy()

    # 归一化
    s_max = strength.max()
    if s_max > 0:
        strength = strength / s_max

    # 应用伪彩色
    heatmap = apply_colormap(strength, cmap=colormap)

    # 创建 alpha 蒙版
    mask = (strength > 0.01).astype(np.float32)
    alpha_mask = mask * alpha

    # 叠加
    result = image.astype(np.float32) * (1 - alpha_mask[:, :, np.newaxis]) + \
             heatmap.astype(np.float32) * alpha_mask[:, :, np.newaxis]

    return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================
# Level 1: 力向量场
# ============================================================

def force_vector_field(image: np.ndarray,
                       force_vectors: np.ndarray,
                       grid_size: int = 8,
                       scale: float = 10.0,
                       color: Tuple[int, int, int] = (0, 255, 0),
                       min_magnitude: float = 0.01) -> np.ndarray:
    """在图像上绘制力向量场（箭头图）

    Args:
        image: (H, W, 3) 原始触觉图像
        force_vectors: (H, W, 2) 力向量 [fx, fy]，或 (N, 4) 网格向量 [x, y, fx, fy]
        grid_size: 箭头间隔（像素），用于 (H, W, 2) 格式
        scale: 箭头缩放因子
        color: 箭头颜色 (R, G, B)
        min_magnitude: 最小力模长阈值，低于此值不绘制

    Returns:
        (H, W, 3) uint8 RGB 图像
    """
    if image is None or force_vectors is None:
        return image.copy() if image is not None else None

    # 转换为 numpy 数组
    force_vectors = np.asarray(force_vectors, dtype=np.float32)
    
    result = image.copy()
    h, w = result.shape[:2]

    if force_vectors.ndim == 3 and force_vectors.shape[2] == 2:
        # (H, W, 2) 格式 — 每个像素一个向量
        for y in range(0, h, grid_size):
            for x in range(0, w, grid_size):
                fy, fx = force_vectors[y, x]
                mag = math.sqrt(fx ** 2 + fy ** 2)
                if mag < min_magnitude:
                    continue
                # 绘制箭头
                end_x = int(x + fx * scale)
                end_y = int(y + fy * scale)
                _draw_arrow(result, (x, y), (end_x, end_y), color, thickness=1)

    elif force_vectors.ndim == 2 and force_vectors.shape[1] == 4:
        # (N, 4) 格式 — [x, y, fx, fy]
        for row in force_vectors:
            x, y, fx, fy = row
            mag = math.sqrt(fx ** 2 + fy ** 2)
            if mag < min_magnitude:
                continue
            end_x = int(x + fx * scale)
            end_y = int(y + fy * scale)
            _draw_arrow(result, (int(x), int(y)), (end_x, end_y), color, thickness=1)

    return result


def _draw_arrow(img: np.ndarray, start: Tuple[int, int], end: Tuple[int, int],
                color: Tuple[int, int, int], thickness: int = 1):
    """在图像上绘制简单箭头（不依赖 cv2）"""
    x1, y1 = start
    x2, y2 = end
    h, w = img.shape[:2]

    # 画线（Bresenham 简化版）
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy

    while True:
        if 0 <= x1 < w and 0 <= y1 < h:
            img[y1, x1] = color
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy

    # 画箭头头部
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = max(3, int(math.sqrt(dx ** 2 + dy ** 2) * 0.3))
    for da in [2.5, -2.5]:
        ax = int(x2 - arrow_len * math.cos(angle + da))
        ay = int(y2 - arrow_len * math.sin(angle + da))
        if 0 <= ax < w and 0 <= ay < h:
            img[ay, ax] = color


# ============================================================
# Level 1: 接触区域高亮
# ============================================================

def contact_region_overlay(image: np.ndarray,
                           contact_centroid: Optional[List[float]] = None,
                           contact_region: Optional[str] = None,
                           radius: int = 15,
                           color: Tuple[int, int, int] = (255, 0, 0),
                           fill: bool = False) -> np.ndarray:
    """在图像上高亮接触区域

    Args:
        image: (H, W, 3) 原始图像
        contact_centroid: [x, y] 归一化坐标 (0-1) 或像素坐标
        contact_region: 区域名称（如 "palmar", "digital"），用于标注文字
        radius: 高亮圆半径（像素）
        color: 高亮颜色 (R, G, B)
        fill: 是否填充圆

    Returns:
        (H, W, 3) uint8 图像
    """
    if image is None:
        return None

    result = image.copy()
    h, w = result.shape[:2]

    if contact_centroid is not None:
        cx, cy = contact_centroid
        # 如果是归一化坐标 (0-1)，转换为像素
        if 0 <= cx <= 1 and 0 <= cy <= 1:
            cx = int(cx * w)
            cy = int(cy * h)
        else:
            cx, cy = int(cx), int(cy)

        # 画圆
        if fill:
            _draw_filled_circle(result, cx, cy, radius, color)
        else:
            _draw_circle(result, cx, cy, radius, color, thickness=2)

    return result


def _draw_circle(img: np.ndarray, cx: int, cy: int, radius: int,
                 color: Tuple[int, int, int], thickness: int = 1):
    """画圆（不依赖 cv2）"""
    h, w = img.shape[:2]
    for angle_deg in range(0, 360, 1):
        angle = math.radians(angle_deg)
        for t in range(thickness):
            r = radius + t
            x = int(cx + r * math.cos(angle))
            y = int(cy + r * math.sin(angle))
            if 0 <= x < w and 0 <= y < h:
                img[y, x] = color


def _draw_filled_circle(img: np.ndarray, cx: int, cy: int, radius: int,
                        color: Tuple[int, int, int]):
    """画填充圆（不依赖 cv2）"""
    h, w = img.shape[:2]
    for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                img[y, x] = color


# ============================================================
# Level 2: 组合视图
# ============================================================

def composite_view(frame, image: Optional[np.ndarray] = None,
                   show_heatmap: bool = True,
                   show_vectors: bool = True,
                   show_region: bool = True,
                   alpha: float = 0.5) -> Optional[np.ndarray]:
    """组合视图 — 热力图 + 力向量 + 接触区域

    Args:
        frame: TLabelFrame 实例
        image: 可选，覆盖 frame.image
        show_heatmap: 是否显示热力图
        show_vectors: 是否显示力向量
        show_region: 是否显示接触区域
        alpha: 热力图透明度

    Returns:
        (H, W, 3) uint8 图像，或 None（无图像数据时）
    """
    # 获取图像
    img = image
    if img is None and hasattr(frame, 'image') and frame.image is not None:
        img = frame.image
    if img is None:
        return None

    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)

    result = img.copy()
    sv2 = frame.schema_v2 if hasattr(frame, 'schema_v2') else None

    if sv2 is None:
        return result

    # 热力图
    if show_heatmap and sv2.force_magnitude is not None and sv2.force_magnitude > 0:
        # 用 force_magnitude 作为强度（简化版，完整需要 force_vector 的空间分布）
        h, w = result.shape[:2]
        # 创建以 centroid 为中心的高斯强度图
        if sv2.contact_centroid is not None:
            cx = int(sv2.contact_centroid[0] * w) if sv2.contact_centroid[0] <= 1 else int(sv2.contact_centroid[0])
            cy = int(sv2.contact_centroid[1] * h) if sv2.contact_centroid[1] <= 1 else int(sv2.contact_centroid[1])
        else:
            cx, cy = w // 2, h // 2

        y_grid, x_grid = np.mgrid[0:h, 0:w]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        sigma = max(h, w) * 0.2
        intensity = np.exp(-dist ** 2 / (2 * sigma ** 2)) * sv2.force_magnitude
        result = contact_heatmap(result, intensity=intensity, alpha=alpha)

    # 力向量场
    if show_vectors and sv2.force_vector is not None:
        h, w = result.shape[:2]
        fv = sv2.force_vector
        if len(fv) >= 2:
            # 在中心绘制单个力向量（代表整体力方向）
            cx, cy = w // 2, h // 2
            fx, fy = fv[0], fv[1]
            result = force_vector_field(
                result,
                np.array([[cx, cy, fx * w * 0.3, fy * h * 0.3]]),
                grid_size=1, scale=1.0,
            )

    # 接触区域
    if show_region and sv2.contact:
        result = contact_region_overlay(
            result,
            contact_centroid=sv2.contact_centroid,
            contact_region=sv2.contact_region,
        )

    return result


# ============================================================
# 帧序列动画
# ============================================================

def frame_animation(frames: list,
                    max_frames: int = 30,
                    fps: int = 10,
                    mode: str = "html") -> Optional[str]:
    """生成帧序列动画

    Args:
        frames: TLabelFrame 列表或图像列表 (numpy arrays)
        max_frames: 最大帧数
        fps: 帧率
        mode: "html" (GIF inline) 或 "gif" (返回 bytes)

    Returns:
        HTML string (mode="html") 或 bytes (mode="gif")，或 None
    """
    from tlabel.core.types import TLabelFrame

    # 提取图像
    images = []
    for f in frames[:max_frames]:
        if isinstance(f, TLabelFrame):
            img = getattr(f, 'image', None)
        elif isinstance(f, np.ndarray):
            img = f
        else:
            img = None
        if img is not None:
            images.append(img)

    if not images:
        return None

    # 统一尺寸
    target_h, target_w = images[0].shape[:2]
    resized = []
    for img in images:
        if img.shape[:2] != (target_h, target_w):
            # 简单最近邻缩放
            sy = target_h / img.shape[0]
            sx = target_w / img.shape[1]
            y_idx = (np.arange(target_h) / sy).astype(int)
            x_idx = (np.arange(target_w) / sx).astype(int)
            img = img[np.ix_(y_idx, x_idx)]
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)
        resized.append(img)

    # 生成 GIF bytes
    gif_bytes = _encode_gif(resized, fps=fps)
    if gif_bytes is None:
        return None

    if mode == "gif":
        return gif_bytes

    # HTML 模式
    b64 = base64.b64encode(gif_bytes).decode('utf-8')
    return f'<img src="data:image/gif;base64,{b64}" style="max-width:100%;" />'


def _encode_gif(images: List[np.ndarray], fps: int = 10) -> Optional[bytes]:
    """将图像序列编码为 GIF

    优先使用 PIL，失败时尝试 imageio。

    Args:
        images: (H, W, 3) uint8 图像列表
        fps: 帧率

    Returns:
        GIF bytes 或 None
    """
    if not images:
        return None

    duration_ms = int(1000 / fps)

    # 尝试 PIL
    try:
        from PIL import Image
        pil_images = [Image.fromarray(img) for img in images]
        buf = io.BytesIO()
        pil_images[0].save(
            buf, format='GIF', save_all=True,
            append_images=pil_images[1:],
            duration=duration_ms, loop=0,
        )
        return buf.getvalue()
    except ImportError:
        pass

    # 尝试 imageio
    try:
        import imageio
        buf = io.BytesIO()
        writer = imageio.get_writer(buf, format='GIF', fps=fps, loop=0)
        for img in images:
            writer.append_data(img)
        writer.close()
        return buf.getvalue()
    except ImportError:
        pass

    return None


# ============================================================
# Level 3: 文本描述（无依赖降级）
# ============================================================

def text_summary(frame) -> str:
    """帧的纯文本可视化描述（Level 3 降级）

    不需要任何图像数据，仅输出文字摘要。
    """
    sv2 = getattr(frame, 'schema_v2', None)
    if sv2 is None:
        return f"Frame {frame.frame_idx}: no schema data"

    parts = [f"Frame {frame.frame_idx} (t={frame.timestamp_s:.3f}s):"]
    parts.append(f"  contact={'YES' if sv2.contact else 'no'}")

    if sv2.contact:
        if sv2.contact_centroid:
            parts.append(f"  centroid=({sv2.contact_centroid[0]:.2f}, {sv2.contact_centroid[1]:.2f})")
        if sv2.contact_region:
            parts.append(f"  region={sv2.contact_region}")

    if sv2.force_magnitude is not None:
        parts.append(f"  force={sv2.force_magnitude:.3f}")
    if sv2.force_vector is not None:
        fv = sv2.force_vector
        if len(fv) >= 3:
            parts.append(f"  force_vec=[{fv[0]:.2f}, {fv[1]:.2f}, {fv[2]:.2f}]")
        else:
            parts.append(f"  force_vec=[{fv[0]:.2f}, {fv[1]:.2f}]")
    if sv2.slip_event:
        parts.append(f"  SLIP detected")
    if sv2.object_deformation is not None:
        parts.append(f"  deformation={sv2.object_deformation:.3f}")
    if sv2.temperature is not None:
        parts.append(f"  temp={sv2.temperature:.1f}°C")

    parts.append(f"  compliance={sv2.compliance_level}")
    parts.append(f"  confidence={sv2.confidence:.2f}")

    return "\n".join(parts)


# ============================================================
# 自动降级选择
# ============================================================

def visualize_frame(frame, image: Optional[np.ndarray] = None,
                    level: Optional[int] = None,
                    mode: str = "composite") -> Any:
    """自动选择可视化级别

    三级降级策略:
      Level 1 (Full):   composite_view() — 需要 numpy
      Level 2 (Simple): contact_heatmap() 简化版 — 需要 numpy
      Level 3 (Text):   text_summary() — 无依赖

    Args:
        frame: TLabelFrame
        image: 可选覆盖图像
        level: 强制指定级别 (1/2/3)，None 自动检测
        mode: "composite" | "heatmap" | "text"

    Returns:
        numpy array (Level 1/2) 或 str (Level 3)
    """
    # 自动检测级别
    if level is None:
        try:
            import numpy as np
            # 有 numpy，检查图像
            img = image
            if img is None and hasattr(frame, 'image'):
                img = frame.image
            if img is not None:
                level = 1
            else:
                level = 3
        except ImportError:
            level = 3

    if level == 3 or mode == "text":
        return text_summary(frame)

    # Level 1 or 2
    if mode == "heatmap":
        img = image
        if img is None and hasattr(frame, 'image'):
            img = frame.image
        if img is not None:
            sv2 = getattr(frame, 'schema_v2', None)
            if sv2 and sv2.force_magnitude is not None:
                h, w = img.shape[:2]
                if sv2.contact_centroid:
                    cx = int(sv2.contact_centroid[0] * w)
                    cy = int(sv2.contact_centroid[1] * h)
                else:
                    cx, cy = w // 2, h // 2
                y_grid, x_grid = np.mgrid[0:h, 0:w]
                dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
                sigma = max(h, w) * 0.2
                intensity = np.exp(-dist ** 2 / (2 * sigma ** 2)) * sv2.force_magnitude
                return contact_heatmap(img, intensity=intensity)
        return img

    # 默认 composite
    return composite_view(frame, image=image)
