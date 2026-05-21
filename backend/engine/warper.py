"""图像变形与合成模块。

功能：
  - 在 A4 画布上渲染文本（支持负间距）
  - 透视变换（warp）将 A4 文字层映射到背景照片的空白区域
  - 正片叠底合成，保留纸张纹理
"""

import json
import random
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .layout import apply_baseline_drift, split_into_lines
from .effects import apply_erasure, apply_ink_variation

# A4 标准尺寸（像素，与 src_points 对应）
A4_WIDTH = 2100
A4_HEIGHT = 2970

# 配置文件路径
_CONFIG_PATH = Path(__file__).resolve().parent / "templates_config.json"


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_template_config(template_id: str) -> dict:
    """从 JSON 中加载模板映射坐标。

    Args:
        template_id: 模板标识，如 "template_v1"

    Returns:
        {"src_points": [...], "dst_points": [...], ...}

    Raises:
        KeyError: 模板不存在
    """
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        configs = json.load(f)
    if template_id not in configs:
        raise KeyError(f"模板 '{template_id}' 不存在，可用模板: {list(configs.keys())}")
    return configs[template_id]


# ---------------------------------------------------------------------------
# A4 文本渲染（支持负间距）
# ---------------------------------------------------------------------------

def render_text_to_a4(
    text: str,
    font_path: str,
    font_size: int = 48,
    letter_spacing: int = 0,
    line_spacing: float = 1.5,
    padding: int = 120,
    baseline_drift_amplitude: int = 2,
    ink_variation: int = 15,
    kerning_jitter: int = 1,
    error_rate: float = 0.05,
    render_rect: tuple = None,
    spacing_randomness: float = 2.0,
) -> Image.Image:
    """在 A4 画布上渲染手写文本，支持负间距、字距抖动、涂改重写。

    Args:
        text: 待渲染文本。
        font_path: 字体文件路径。
        font_size: 字号。
        letter_spacing: 字符间距（px），负值产生笔画重叠。
        line_spacing: 行高倍数。
        padding: 页边距（render_rect 为 None 时生效）。
        baseline_drift_amplitude: 基线抖动幅度。
        ink_variation: 墨迹深浅变化幅度。
        kerning_jitter: 字距随机抖动幅度（px）。
        error_rate: 单词涂改触发率（0~1）。
        render_rect: (x, y, w, h) 渲染区域，若指定则排版局限在该区域内，
                     且 aspect ratio 已匹配 dst 四边形，避免拉伸畸变。
        spacing_randomness: 行列间距随机度（0=关闭）。控制左边界抖动、
                           per-character Y 抖动、行距波动。

    Returns:
        白色背景的 A4 尺寸 PIL Image。
    """
    font = ImageFont.truetype(font_path, font_size)
    base_line_height = int(font_size * line_spacing)

    if render_rect:
        rx, ry, rw, rh = render_rect
        max_text_width = rw
        left_margin = rx
        top_offset = ry
    else:
        max_text_width = A4_WIDTH - padding * 2
        left_margin = padding
        top_offset = padding

    # 文本分行
    lines = split_into_lines(text, font, max_text_width)

    # 基线偏移（加入动态行距随机）
    drifted_lines = apply_baseline_drift(lines, base_line_height, baseline_drift_amplitude)
    # 加 top_offset
    drifted_lines = [(t, y + top_offset) for t, y in drifted_lines]

    # 动态行间距：每行之间的间距加入随机增量
    if spacing_randomness > 0 and len(drifted_lines) > 1:
        sr = int(spacing_randomness)
        adjusted = [drifted_lines[0]]
        for i in range(1, len(drifted_lines)):
            _t, prev_y = adjusted[i - 1]
            _, curr_y = drifted_lines[i]
            base_gap = curr_y - prev_y
            gap_jitter = random.randint(-sr, sr)
            new_y = prev_y + base_gap + gap_jitter
            adjusted.append((drifted_lines[i][0], new_y))
        drifted_lines = adjusted

    # 创建白色 A4 画布
    image = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    def _char_width(char: str) -> int:
        bbox = font.getbbox(char)
        return bbox[2] - bbox[0] if bbox else 0

    def _draw_char(x: int, y: int, char: str) -> int:
        color = apply_ink_variation(base_color=(45, 45, 45), variation=ink_variation)
        jitter = random.randint(-kerning_jitter, kerning_jitter) if kerning_jitter else 0
        # per-character Y 抖动：字在行基线上微浮动
        sr = int(spacing_randomness)
        y_jitter = random.randint(-sr, sr) if sr > 0 else 0
        draw.text((x + jitter, y + y_jitter), char, fill=color, font=font)
        return _char_width(char) + letter_spacing + jitter

    for line_text, y_base in drifted_lines:
        # 左边界抖动：每行起始 x 不严格相等
        sr = int(spacing_randomness)
        left_jitter = random.randint(-sr, sr) if sr > 0 else 0
        x = left_margin + left_jitter
        words = line_text.split(" ") if line_text.strip() else []

        for word_idx, word in enumerate(words):
            if not word:
                x += _char_width(" ") + letter_spacing
                continue

            if word_idx > 0:
                x += _char_width(" ")

            word_start_x = x
            should_erase = error_rate > 0 and random.random() < error_rate

            for char in word:
                x += _draw_char(x, y_base, char)

            if should_erase:
                word_end_x = x
                bbox = (word_start_x, y_base, word_end_x - word_start_x, base_line_height)
                apply_erasure(draw, bbox)
                x += font_size // 2
                for char in word:
                    x += _draw_char(x, y_base, char)

    return image


# ---------------------------------------------------------------------------
# 透视变换
# ---------------------------------------------------------------------------

def warp_text_to_background(
    text_layer: Image.Image,
    background: Image.Image,
    src_points: List[List[float]],
    dst_points: List[List[float]],
) -> Image.Image:
    """将 A4 文字层透视变换到背景图的指定区域。

    Args:
        text_layer: A4 尺寸的文字层图像。
        background: 背景照片（任意尺寸）。
        src_points: 源四边形 4 个顶点 [[x,y], ...]。
        dst_points: 目标四边形 4 个顶点 [[x,y], ...]。

    Returns:
        与 background 等尺寸的变换后图像（白色区域=无文字）。
    """
    import cv2

    src = np.array(src_points, dtype=np.float32)
    dst = np.array(dst_points, dtype=np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    bg_np = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
    text_np = cv2.cvtColor(np.array(text_layer), cv2.COLOR_RGB2BGR)

    warped = cv2.warpPerspective(
        text_np,
        M,
        (bg_np.shape[1], bg_np.shape[0]),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))


# ---------------------------------------------------------------------------
# 正片叠底合成 (Multiply Blending)
# ---------------------------------------------------------------------------

def multiply_blend(
    background: Image.Image,
    foreground: Image.Image,
) -> Image.Image:
    """正片叠底合成两幅等尺寸图像。

    公式: Result = (Background × Foreground) / 255

    适用于将文字层叠加到背景上，保留纸张纹理和阴影。
    """
    bg_np = np.array(background, dtype=np.float32)
    fg_np = np.array(foreground, dtype=np.float32)

    blended = (bg_np * fg_np) / 255.0
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    return Image.fromarray(blended)


def _quad_aspect_ratio(points: list) -> float:
    """计算用户四边形的宽高比 (w/h)，用于确定 A4 上的渲染区域形状。"""
    top_w = abs(points[1][0] - points[0][0])
    bot_w = abs(points[2][0] - points[3][0])
    left_h = abs(points[3][1] - points[0][1])
    right_h = abs(points[2][1] - points[1][1])
    w = (top_w + bot_w) / 2.0
    h = (left_h + right_h) / 2.0
    return w / h if h > 0 else 1.0


def _compute_render_rect(dst_points: list, padding: int = 120) -> tuple:
    """根据 dst 四边形宽高比，在 A4 画布上计算匹配的渲染区域。

    Returns:
        (x, y, w, h) 在 A4 内的渲染矩形，aspect ratio 已匹配 dst。
    """
    aspect = _quad_aspect_ratio(dst_points)
    # A4 内可用的最大区域（两侧各留 padding 边距）
    avail_w = A4_WIDTH - 2 * padding
    avail_h = A4_HEIGHT - 2 * padding

    if aspect >= 1.0:
        # dst 宽 ≥ 高 → 以可用宽度为基准
        w = avail_w
        h = avail_w / aspect
        if h > avail_h:
            h = avail_h
            w = h * aspect
    else:
        # dst 宽 < 高 → 以可用高度为基准
        h = avail_h
        w = avail_h * aspect
        if w > avail_w:
            w = avail_w
            h = w / aspect

    x = padding
    y = padding
    return (int(x), int(y), int(w), int(h))


def compute_text_bbox(image: Image.Image, bg_color: tuple = (255, 255, 255)):
    """计算图像中非背景像素的边界框。

    Args:
        image: PIL Image。
        bg_color: 背景色 (R, G, B)。

    Returns:
        (x1, y1, x2, y2) 或 None（无内容）。
    """
    arr = np.array(image)
    mask = ~np.all(arr == bg_color, axis=2)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not np.any(rows) or not np.any(cols):
        return None
    y1, y2 = np.where(rows)[0][[0, -1]]
    x1, x2 = np.where(cols)[0][[0, -1]]
    return (int(x1), int(y1), int(x2), int(y2))


def auto_dst_points(
    image_width: int,
    image_height: int,
    margin: float = 0.1,
) -> List[List[int]]:
    """自动生成居中的目标点集（图像中心 80% 区域）。

    当用户上传自定义背景且未提供 dst_points 时使用此默认值。

    Args:
        image_width: 背景图像宽度。
        image_height: 背景图像高度。
        margin: 边距比例（0~0.5），0.1 表示每边留 10%。

    Returns:
        [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] 四个顶点。
    """
    mx = int(image_width * margin)
    my = int(image_height * margin)
    return [
        [mx, my],
        [image_width - mx, my],
        [image_width - mx, image_height - my],
        [mx, image_height - my],
    ]


# ---------------------------------------------------------------------------
# 完整管线
# ---------------------------------------------------------------------------

def render_with_template(
    text: str,
    font_path: str,
    background_path: str,
    template_id: str = "template_v1",
    dst_points: list = None,
    font_size: int = 48,
    letter_spacing: int = 0,
    line_spacing: float = 1.5,
    baseline_drift_amplitude: int = 2,
    ink_variation: int = 15,
    kerning_jitter: int = 1,
    error_rate: float = 0.05,
    spacing_randomness: float = 2.0,
) -> Image.Image:
    """完整管线：渲染文本 → 透视变换 → 正片叠底合成。

    Args:
        text: 待渲染文本。
        font_path: 字体路径。
        background_path: 背景照片路径。
        template_id: 模板标识。
        dst_points: 自定义目标四边形顶点，None 则从模板加载或自动居中。
        font_size: 字号。
        letter_spacing: 字间距。
        line_spacing: 行间距倍数。
        baseline_drift_amplitude: 基线抖动。
        ink_variation: 墨迹变化。
        kerning_jitter: 字距随机抖动幅度（px）。
        error_rate: 单词涂改触发率（0~1）。
        spacing_randomness: 行列间距随机度。

    Returns:
        最终合成图像（与背景等尺寸）。
    """
    import cv2  # noqa: F401 — 确保 cv2 已安装

    # 1. 加载背景
    background = Image.open(background_path).convert("RGB")

    # 2. 确定 dst_points
    if dst_points is None:
        try:
            config = load_template_config(template_id)
            dst_points = config["dst_points"]
        except (KeyError, FileNotFoundError):
            dst_points = auto_dst_points(background.width, background.height)

    # 3. 加载模板配置（获取 src_points）
    try:
        config = load_template_config(template_id)
        src_points = config["src_points"]
    except (KeyError, FileNotFoundError):
        src_points = [[0, 0], [A4_WIDTH, 0], [A4_WIDTH, A4_HEIGHT], [0, A4_HEIGHT]]

    # 4. 渲染 A4 文字层
    text_layer = render_text_to_a4(
        text=text,
        font_path=font_path,
        font_size=font_size,
        letter_spacing=letter_spacing,
        line_spacing=line_spacing,
        baseline_drift_amplitude=baseline_drift_amplitude,
        ink_variation=ink_variation,
        kerning_jitter=kerning_jitter,
        error_rate=error_rate,
        spacing_randomness=spacing_randomness,
    )

    # 5. 透视变换
    warped = warp_text_to_background(
        text_layer=text_layer,
        background=background,
        src_points=src_points,
        dst_points=dst_points,
    )

    # 6. 正片叠底合成
    result = multiply_blend(background, warped)

    return result


def render_custom_background(
    text: str,
    font_path: str,
    background: Image.Image,
    dst_points: list = None,
    font_size: int = 48,
    letter_spacing: int = 0,
    line_spacing: float = 1.5,
    baseline_drift_amplitude: int = 2,
    ink_variation: int = 15,
    kerning_jitter: int = 1,
    error_rate: float = 0.05,
    spacing_randomness: float = 2.0,
) -> Image.Image:
    """使用用户上传的背景图进行透视渲染。

    不依赖模板配置，dst_points 为 None 则自动居中。

    Args:
        text: 待渲染文本。
        font_path: 字体路径。
        background: 用户上传的背景 PIL Image。
        dst_points: 自定义四边形顶点，None 则居中 80%。
        font_size: 字号。
        letter_spacing: 字间距。
        line_spacing: 行间距倍数。
        baseline_drift_amplitude: 基线抖动。
        ink_variation: 墨迹变化。
        kerning_jitter: 字距随机抖动幅度（px）。
        error_rate: 单词涂改触发率（0~1）。
        spacing_randomness: 行列间距随机度。

    Returns:
        最终合成图像（与 background 等尺寸）。
    """
    import cv2  # noqa: F401

    if dst_points is None:
        dst_points = auto_dst_points(background.width, background.height)

    # ---- 根据 dst 透视四边形计算 aspect ratio 匹配的 A4 渲染区域 ----
    render_rect = _compute_render_rect(dst_points, padding=120)
    rx, ry, rw, rh = render_rect

    text_layer = render_text_to_a4(
        text=text,
        font_path=font_path,
        font_size=font_size,
        letter_spacing=letter_spacing,
        line_spacing=line_spacing,
        padding=120,
        baseline_drift_amplitude=baseline_drift_amplitude,
        ink_variation=ink_variation,
        kerning_jitter=kerning_jitter,
        error_rate=error_rate,
        render_rect=render_rect,
        spacing_randomness=spacing_randomness,
    )

    # 直接使用 render_rect 的四个角作为 src_points。
    # render_rect 的 aspect ratio 与 dst 四边形一致 → 透视映射保持 S_x = S_y，
    # 字形不会被额外拉伸。文字只占 render_rect 的一部分时，
    # 对应 dst 中只有对应区域有文字，其余留白。
    src = [[rx, ry], [rx + rw, ry], [rx + rw, ry + rh], [rx, ry + rh]]

    warped = warp_text_to_background(
        text_layer=text_layer,
        background=background,
        src_points=src,
        dst_points=dst_points,
    )

    # ---- 边缘软化：极小半径高斯模糊消除数码锐利感 ----
    warped_np = np.array(warped)
    blurred = cv2.GaussianBlur(warped_np, (0, 0), sigmaX=0.3)
    blurred = np.clip(blurred, 0, 255).astype(np.uint8)
    warped = Image.fromarray(blurred)
    # ---------------------------------------------------

    return multiply_blend(background, warped)
