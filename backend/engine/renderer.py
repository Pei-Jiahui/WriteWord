"""手写渲染引擎：编排布局 → 绘制 → 涂改 → 重写 全流程。"""

import io
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from .layout import apply_baseline_drift, split_into_lines
from .effects import apply_erasure, apply_ink_variation


@dataclass
class RenderOptions:
    """渲染配置项。"""
    font_path: str
    font_size: int = 32
    line_spacing: float = 1.8
    image_width: int = 800
    image_height: int = 600
    background_color: str = "white"
    text_color: str = "#333333"
    baseline_drift_amplitude: int = 2
    kerning_jitter: int = 1
    error_rate: float = 0.05
    ink_variation: int = 15
    padding: int = 40


def render_handwriting(
    text: str,
    options: RenderOptions,
) -> bytes:
    """渲染手写文本图像，返回 PNG 字节流。

    流程：
        1. 加载字体，将文本拆分为行
        2. 应用基线偏移
        3. 逐单词绘制，记录单词包围盒
        4. 按 error_rate 概率对单词涂改，并在其后重写
        5. 返回 PNG 字节流
    """
    font = ImageFont.truetype(options.font_path, options.font_size)
    line_height = int(options.font_size * options.line_spacing)

    # 1. 文本分行
    max_text_width = options.image_width - options.padding * 2
    lines = split_into_lines(text, font, max_text_width)

    # 2. 基线偏移
    drifted_lines = apply_baseline_drift(
        lines, line_height, options.baseline_drift_amplitude
    )

    # 创建画布
    image = Image.new(
        "RGB",
        (options.image_width, options.image_height),
        options.background_color,
    )
    draw = ImageDraw.Draw(image)

    def _char_width(char: str) -> int:
        bbox = font.getbbox(char)
        return bbox[2] - bbox[0] if bbox else 0

    def _draw_char(x: int, y: int, char: str) -> int:
        """绘制单个字符，返回字宽（含抖动偏移）。"""
        jitter = random.randint(-options.kerning_jitter, options.kerning_jitter) if options.kerning_jitter else 0
        color = apply_ink_variation(base_color=(45, 45, 45), variation=options.ink_variation)
        draw.text((x + jitter, y), char, fill=color, font=font)
        return _char_width(char) + jitter

    # 3-4. 逐行逐词绘制 + 涂改 + 重写
    for line_text, y_base in drifted_lines:
        x = options.padding
        words = line_text.split(" ")

        for word_idx, word in enumerate(words):
            if not word:
                continue

            # 词间空格
            if word_idx > 0:
                x += _char_width(" ")

            # 记录单词起始位置
            word_start_x = x

            # 决定是否涂改
            should_erase = options.error_rate > 0 and random.random() < options.error_rate

            # 绘制单词（原文）
            for char in word:
                x += _draw_char(x, y_base, char)

            # 涂改 + 重写
            if should_erase:
                word_end_x = x
                bbox = (word_start_x, y_base, word_end_x - word_start_x, line_height)
                apply_erasure(draw, bbox)

                # 隔开一段间隙，重写正确单词
                x += options.font_size // 2
                for char in word:
                    x += _draw_char(x, y_base, char)

    # 输出 PNG 字节流
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
