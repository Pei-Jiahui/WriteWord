"""图像逻辑模块测试（TDD：先编写测试，再实现功能）。

覆盖：
  - 负间距渲染
  - 透视变换输出尺寸
  - 正片叠底合成颜色
"""

import io
import json
import pathlib

import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.engine.warper import (
    render_text_to_a4,
    warp_text_to_background,
    multiply_blend,
    load_template_config,
    A4_WIDTH,
    A4_HEIGHT,
)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "engine" / "templates_config.json"


def _find_test_font():
    """尝试找测试用字体。"""
    fonts_dir = pathlib.Path(__file__).resolve().parent.parent / "fonts"
    for f in sorted(fonts_dir.glob("*.ttf")):
        return str(f)
    win_font = pathlib.Path("C:/Windows/Fonts/arial.ttf")
    if win_font.exists():
        return str(win_font)
    return None


def _default_src() -> list:
    """A4 标准 src_points。"""
    return [[0, 0], [A4_WIDTH, 0], [A4_WIDTH, A4_HEIGHT], [0, A4_HEIGHT]]


def _default_dst(bg_w: int, bg_h: int) -> list:
    """根据背景图尺寸生成一个居中的 dst_points（测试用）。"""
    margin_x = int(bg_w * 0.1)
    margin_y = int(bg_h * 0.1)
    return [
        [margin_x, margin_y],
        [bg_w - margin_x, margin_y],
        [bg_w - margin_x, bg_h - margin_y],
        [margin_x, bg_h - margin_y],
    ]


# ---------------------------------------------------------------------------
# 1. 负间距测试
# ---------------------------------------------------------------------------

class TestNegativeLetterSpacing:
    """验证 letter_spacing 负值时，字符 x 坐标正确回退（重叠）。"""

    @staticmethod
    def _text_width(img) -> int:
        """通过查找右边界暗色像素计算文本实际占宽。"""
        import numpy as np
        arr = np.array(img)
        # 文本像素 R/G/B 均 < 200（非白色）
        dark = np.all(arr < 200, axis=2)
        cols = np.any(dark, axis=0)
        indices = np.where(cols)[0]
        if len(indices) == 0:
            return 0
        return int(indices[-1] - indices[0])

    def test_negative_spacing_reduces_total_width(self):
        """负间距应使文本总宽度小于正间距。"""
        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体")

        img_neg = render_text_to_a4("Hello", font_path, letter_spacing=-5, font_size=40)
        img_pos = render_text_to_a4("Hello", font_path, letter_spacing=5, font_size=40)
        img_zero = render_text_to_a4("Hello", font_path, letter_spacing=0, font_size=40)

        w_neg = self._text_width(img_neg)
        w_zero = self._text_width(img_zero)
        w_pos = self._text_width(img_pos)

        assert w_neg < w_zero, f"负间距宽度({w_neg})应小于零间距宽度({w_zero})"
        assert w_pos > w_zero, f"正间距宽度({w_pos})应大于零间距宽度({w_zero})"

    def test_negative_spacing_does_not_raise(self):
        """负间距渲染不应抛异常。"""
        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体")
        img = render_text_to_a4("测试abc", font_path, letter_spacing=-3, font_size=48)
        assert isinstance(img, Image.Image)
        assert img.size == (A4_WIDTH, A4_HEIGHT)


# ---------------------------------------------------------------------------
# 2. 透视变换输出尺寸测试
# ---------------------------------------------------------------------------

class TestWarpOutputSize:
    """验证 warp 后输出图像尺寸与背景图一致。"""

    def test_output_matches_background_size(self):
        """变换后图像尺寸应与背景图完全相同。"""
        pytest.importorskip("cv2", reason="需要 opencv-python")

        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体")

        # 创建测试背景（任意尺寸）
        bg = Image.new("RGB", (1200, 1600), "white")
        text_layer = render_text_to_a4("Hello World", font_path, letter_spacing=0, font_size=64)

        src = _default_src()
        dst = _default_dst(bg.width, bg.height)

        warped = warp_text_to_background(text_layer, bg, src, dst)
        assert warped.size == bg.size, (
            f"变换后尺寸 {warped.size} 应与背景 {bg.size} 一致"
        )

    def test_warp_with_asymmetric_background(self):
        """非正方形背景也能正确变换。"""
        pytest.importorskip("cv2", reason="需要 opencv-python")

        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体")

        bg = Image.new("RGB", (800, 1400), "white")
        text_layer = render_text_to_a4("A" * 20, font_path, letter_spacing=0, font_size=48)

        src = _default_src()
        dst = _default_dst(bg.width, bg.height)

        warped = warp_text_to_background(text_layer, bg, src, dst)
        assert warped.size == (800, 1400)


# ---------------------------------------------------------------------------
# 3. 正片叠底合成颜色测试
# ---------------------------------------------------------------------------

class TestMultiplyBlend:
    """验证 multiply_blend 合成后的像素值。"""

    def test_dark_on_light_produces_darker(self):
        """深色文字叠加在浅色背景上，结果应比背景暗。"""
        pytest.importorskip("cv2", reason="需要 opencv-python")

        bg = Image.new("RGB", (100, 100), (200, 200, 200))  # 浅灰背景
        fg = Image.new("RGB", (100, 100), (50, 50, 50))      # 深灰前景（模拟文字）

        result = multiply_blend(bg, fg)

        # 结果像素应比背景暗
        r, g, b = result.getpixel((50, 50))
        assert r < 200 and g < 200 and b < 200, f"结果 ({r},{g},{b}) 应比背景 (200,200,200) 暗"

    def test_multiply_formula_accuracy(self):
        """验证 Result = (Bg * Fg) / 255 公式准确性。"""
        pytest.importorskip("cv2", reason="需要 opencv-python")

        bg = Image.new("RGB", (1, 1), (180, 100, 220))
        fg = Image.new("RGB", (1, 1), (80, 200, 60))

        result = multiply_blend(bg, fg)
        r, g, b = result.getpixel((0, 0))

        expected_r = (180 * 80) // 255
        expected_g = (100 * 200) // 255
        expected_b = (220 * 60) // 255

        assert r == expected_r, f"R: 期望 {expected_r}, 实际 {r}"
        assert g == expected_g, f"G: 期望 {expected_g}, 实际 {g}"
        assert b == expected_b, f"B: 期望 {expected_b}, 实际 {b}"

    def test_white_foreground_no_change(self):
        """白色前景 (255,255,255) 合成后应与背景相同。"""
        pytest.importorskip("cv2", reason="需要 opencv-python")

        bg = Image.new("RGB", (50, 50), (180, 120, 200))
        fg = Image.new("RGB", (50, 50), (255, 255, 255))  # 白色

        result = multiply_blend(bg, fg)
        px = result.getpixel((25, 25))
        assert px == (180, 120, 200), f"白色前景不应改变背景: {px}"


# ---------------------------------------------------------------------------
# 4. 配置文件加载测试
# ---------------------------------------------------------------------------

class TestTemplateConfig:
    """验证模板配置加载。"""

    def test_load_template_v1(self):
        """能正确加载 template_v1 的配置。"""
        if not CONFIG_PATH.exists():
            pytest.skip("templates_config.json 不存在")

        config = load_template_config("template_v1")
        assert "src_points" in config
        assert "dst_points" in config
        assert len(config["src_points"]) == 4
        assert len(config["dst_points"]) == 4

    def test_unknown_template_raises(self):
        """不存在的模板应抛出 KeyError。"""
        if not CONFIG_PATH.exists():
            pytest.skip("templates_config.json 不存在")

        with pytest.raises(KeyError):
            load_template_config("nonexistent_template")
