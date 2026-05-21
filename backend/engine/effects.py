"""视觉效果模块：模拟涂改、墨迹深浅变化。"""

import math
import random
from typing import Tuple

from PIL import ImageDraw

# 墨迹颜色范围（模拟压力感）
INK_COLOR_MIN = 30
INK_COLOR_MAX = 60

# 涂改线条宽度范围
ERASURE_LINE_WIDTH_MIN = 1
ERASURE_LINE_WIDTH_MAX = 3

# 涂改区域： (x, y, width, height)
BBox = Tuple[int, int, int, int]


def apply_ink_variation(
    base_color: Tuple[int, int, int] = (45, 45, 45),
    variation: int = 15,
) -> Tuple[int, int, int]:
    """生成随机的墨迹颜色，模拟压力感。

    颜色在 (base_color - variation) 到 (base_color + variation) 之间波动，
    但限制在 INK_COLOR_MIN ~ INK_COLOR_MAX 范围内。

    Returns:
        (R, G, B) 颜色元组。
    """
    offset = random.randint(-variation, variation)
    r = max(INK_COLOR_MIN, min(INK_COLOR_MAX, base_color[0] + offset))
    g = max(INK_COLOR_MIN, min(INK_COLOR_MAX, base_color[1] + offset))
    b = max(INK_COLOR_MIN, min(INK_COLOR_MAX, base_color[2] + offset))
    return (int(r), int(g), int(b))


# ---- 涂改相关 ----


def _erasure_color() -> Tuple[int, int, int]:
    """涂改线条颜色（比墨迹略深，模拟用力划掉的笔压）。"""
    v = random.randint(20, 50)
    return (v, v, v)


def _random_width() -> int:
    """1~3px 随机线宽，模拟压力波动。"""
    return random.randint(ERASURE_LINE_WIDTH_MIN, ERASURE_LINE_WIDTH_MAX)


def draw_jittered_line(
    draw: ImageDraw.ImageDraw,
    x1: int, y1: int, x2: int, y2: int,
    color: Tuple[int, int, int],
) -> None:
    """绘制带随机抖动的线段，中间分段添加 ±1-2px 偏移。"""
    distance = math.hypot(x2 - x1, y2 - y1)
    segments = max(3, int(distance / 6))
    prev = (x1, y1)
    for i in range(1, segments + 1):
        t = i / segments
        x = x1 + (x2 - x1) * t + random.randint(-1, 2)
        y = y1 + (y2 - y1) * t + random.randint(-1, 2)
        draw.line([prev, (int(x), int(y))], fill=color, width=_random_width())
        prev = (int(x), int(y))


def draw_horizontal_scratch(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color: Tuple[int, int, int],
) -> None:
    """1-2 条稍微抖动的水平线划过文字区域。"""
    _, y, w, h = bbox
    num_lines = random.randint(1, 2)
    for _ in range(num_lines):
        line_y = y + h // 3 + random.randint(0, h // 3)
        draw_jittered_line(draw, bbox[0], line_y, bbox[0] + w, line_y, color)


def draw_zigzag_scribble(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color: Tuple[int, int, int],
) -> None:
    """之字形快速摆动覆盖文字，模拟乱涂划掉。"""
    x, y, w, h = bbox
    cy = y + h // 2
    segments = max(8, w // 3)
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        x0 = x + w * t0
        y0 = cy + random.randint(-h // 2, h // 2)
        x1 = x + w * t1
        y1 = cy + random.randint(-h // 2, h // 2)
        draw.line(
            [(int(x0), int(y0)), (int(x1), int(y1))],
            fill=color,
            width=_random_width(),
        )


def draw_double_line(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color: Tuple[int, int, int],
) -> None:
    """两条干净利落的平行删除线。"""
    _, y, w, h = bbox
    for offset in [-h // 4, h // 4]:
        line_y = y + h // 2 + offset
        draw_jittered_line(draw, bbox[0], line_y, bbox[0] + w, line_y, color)


_STYLES = {
    "scratch": draw_horizontal_scratch,
    "zigzag": draw_zigzag_scribble,
    "double": draw_double_line,
}


def apply_erasure(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    style: str = None,
) -> None:
    """在指定单词区域应用涂改效果。

    Args:
        draw: 绘图对象。
        bbox: (x, y, width, height) — 单词的包围盒。
        style: 涂改风格，None 则随机选择。
               "scratch" — 横向划线
               "zigzag"  — 之字形乱涂
               "double"  — 双线删除
    """
    color = _erasure_color()
    if style is None:
        style = random.choice(list(_STYLES))
    _STYLES[style](draw, bbox, color)
