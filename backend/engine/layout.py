"""文本布局模块：处理换行、基线偏移、字距随机。"""

import random
from typing import List, Tuple

from PIL import ImageFont


def split_into_lines(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> List[str]:
    """将文本按最大宽度拆分为多行（按字符切分，避免断词）。"""
    lines: List[str] = []
    current_line = ""

    for char in text:
        if char == "\n":
            lines.append(current_line)
            current_line = ""
            continue

        test_line = current_line + char
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0] if bbox else 0

        if line_width > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def apply_baseline_drift(
    lines: List[str],
    line_height: int,
    max_amplitude: int = 2,
) -> List[Tuple[str, int]]:
    """为每行添加 ±max_amplitude 像素的垂直偏移。

    Returns:
        List of (line_text, y_offset) tuples.
    """
    result: List[Tuple[str, int]] = []
    base_y = 0

    for line in lines:
        drift = random.randint(-max_amplitude, max_amplitude)
        result.append((line, base_y + drift))
        base_y += line_height

    return result


def apply_kerning_jitter(
    chars: List[str],
    base_positions: List[int],
    max_jitter: int = 1,
) -> List[Tuple[str, int]]:
    """为每个字符的 x 位置添加微小的随机偏移。

    Args:
        chars: 字符列表。
        base_positions: 每个字符的基准 x 坐标。
        max_jitter: 最大偏移像素值。

    Returns:
        List of (char, x_position) tuples.
    """
    result: List[Tuple[str, int]] = []
    accumulated_jitter = 0

    for char, base_x in zip(chars, base_positions):
        jitter = random.randint(-max_jitter, max_jitter)
        accumulated_jitter += jitter
        result.append((char, base_x + accumulated_jitter))

    return result
