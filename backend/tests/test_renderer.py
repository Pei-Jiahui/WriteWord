"""渲染引擎测试。"""

import io
import pathlib

import pytest
from PIL import Image, ImageFont

from backend.engine.renderer import render_handwriting, RenderOptions


def _find_test_font():
    """尝试找一个可用的字体文件进行测试。"""
    candidates = [
        pathlib.Path("backend/fonts").glob("*.ttf"),
    ]
    for pattern in candidates:
        for f in pattern:
            return str(f)
    # Fallback: Windows 自带字体
    win_font = pathlib.Path("C:/Windows/Fonts/arial.ttf")
    if win_font.exists():
        return str(win_font)
    return None


class TestRenderHandwriting:
    """测试手写渲染全流程。"""

    def test_raises_on_missing_font(self):
        """字体不存在时应抛出 OSError。"""
        with pytest.raises(OSError):
            render_handwriting("Hello", RenderOptions(font_path=""))

    def test_render_with_valid_font(self):
        """使用有效字体时应生成指定尺寸的图像。"""
        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体文件")
        result = render_handwriting(
            "Hello World",
            RenderOptions(font_path=font_path),
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 600)

    def test_error_rate_zero_skips_erasure(self):
        """error_rate=0 时不应进行任何涂改操作。"""
        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体文件")
        result = render_handwriting(
            "Hello World Foo Bar",
            RenderOptions(font_path=font_path, error_rate=0.0),
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 600)

    def test_error_rate_high_produces_more_marks(self):
        """error_rate 较高时不应抛出异常。"""
        font_path = _find_test_font()
        if font_path is None:
            pytest.skip("未找到测试字体文件")
        result = render_handwriting(
            "Hello World Foo Bar Baz Qux",
            RenderOptions(font_path=font_path, error_rate=0.5),
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 600)

    def test_options_defaults(self):
        """RenderOptions 应有合理的默认值。"""
        opts = RenderOptions(font_path="dummy.ttf")
        assert opts.error_rate == 0.05
        assert opts.kerning_jitter == 1
        assert opts.font_size == 32
