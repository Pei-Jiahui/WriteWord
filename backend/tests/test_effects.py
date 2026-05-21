"""效果模块测试。"""

from PIL import Image, ImageDraw

from backend.engine.effects import (
    apply_ink_variation,
    apply_erasure,
    draw_jittered_line,
    draw_horizontal_scratch,
    draw_zigzag_scribble,
    draw_double_line,
    INK_COLOR_MIN,
    INK_COLOR_MAX,
)


def _make_test_bbox(x=0, y=0, w=80, h=30):
    return (x, y, w, h)


class TestApplyInkVariation:
    """测试墨迹深浅变化。"""

    def test_returns_tuple_of_three_ints(self):
        """应返回 (R, G, B) 元组。"""
        color = apply_ink_variation()
        assert isinstance(color, tuple)
        assert len(color) == 3
        assert all(isinstance(v, int) for v in color)

    def test_color_within_bounds(self):
        """颜色分量应在 INK_COLOR_MIN ~ INK_COLOR_MAX 范围内。"""
        for _ in range(50):
            r, g, b = apply_ink_variation(base_color=(45, 45, 45), variation=15)
            assert INK_COLOR_MIN <= r <= INK_COLOR_MAX
            assert INK_COLOR_MIN <= g <= INK_COLOR_MAX
            assert INK_COLOR_MIN <= b <= INK_COLOR_MAX


class TestApplyErasure:
    """测试涂改入口函数。"""

    def test_apply_to_image_does_not_raise(self):
        """在图像上应用涂改不应抛出异常。"""
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        apply_erasure(draw, _make_test_bbox())  # should not raise

    def test_random_style_when_none_given(self):
        """不指定 style 时自动选择一种。"""
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        apply_erasure(draw, _make_test_bbox(), style=None)  # should not raise

    def test_all_styles_run_without_error(self):
        """三种涂改风格都能正常执行。"""
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        for style in ("scratch", "zigzag", "double"):
            apply_erasure(draw, _make_test_bbox(), style=style)


class TestDrawJitteredLine:
    """测试抖动线段。"""

    def test_draws_without_error(self):
        img = Image.new("RGB", (100, 100), "white")
        draw = ImageDraw.Draw(img)
        draw_jittered_line(draw, 10, 10, 90, 90, color=(40, 40, 40))


class TestDrawHorizontalScratch:
    """测试横向划线。"""

    def test_draws_within_bbox(self):
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        draw_horizontal_scratch(draw, _make_test_bbox(50, 50, 80, 30), color=(40, 40, 40))


class TestDrawZigzagScribble:
    """测试之字形乱涂。"""

    def test_draws_without_error(self):
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        draw_zigzag_scribble(draw, _make_test_bbox(), color=(40, 40, 40))


class TestDrawDoubleLine:
    """测试双线删除。"""

    def test_draws_without_error(self):
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        draw_double_line(draw, _make_test_bbox(), color=(40, 40, 40))
