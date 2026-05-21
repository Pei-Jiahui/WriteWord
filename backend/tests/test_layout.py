"""布局模块测试。"""

from PIL import ImageFont, ImageDraw, Image

from backend.engine.layout import split_into_lines, apply_baseline_drift, apply_kerning_jitter


def create_test_font() -> ImageFont.FreeTypeFont:
    """使用 Pillow 默认字体创建测试用字体对象。"""
    return ImageFont.load_default()


class TestSplitIntoLines:
    """测试文本换行逻辑。"""

    def test_short_text_stays_one_line(self):
        """短文本不应换行。"""
        font = create_test_font()
        lines = split_into_lines("Hello", font, max_width=500)
        assert len(lines) == 1
        assert lines[0] == "Hello"

    def test_long_text_wraps(self):
        """长文本超出最大宽度时应换行。"""
        font = create_test_font()
        lines = split_into_lines("Hello World Foo Bar", font, max_width=50)
        assert len(lines) > 1

    def test_newline_character_forces_break(self):
        """显式换行符应强制分行。"""
        font = create_test_font()
        lines = split_into_lines("Hello\nWorld", font, max_width=500)
        assert lines == ["Hello", "World"]

    def test_empty_text_returns_single_empty_line(self):
        """空文本应返回一个空行。"""
        font = create_test_font()
        lines = split_into_lines("", font, max_width=500)
        assert lines == [""]


class TestApplyBaselineDrift:
    """测试基线偏移逻辑。"""

    def test_returns_correct_number_of_lines(self):
        """返回的行数应与输入行数一致。"""
        lines = ["Hello", "World"]
        result = apply_baseline_drift(lines, line_height=40)
        assert len(result) == 2

    def test_drift_within_amplitude(self):
        """偏移量应在 ±max_amplitude 范围内。"""
        lines = ["Hello"]
        result = apply_baseline_drift(lines, line_height=40, max_amplitude=2)
        _, y_offset = result[0]
        assert abs(y_offset) <= 2

    def test_consecutive_lines_increase_y(self):
        """连续行的 y 坐标应递增。"""
        lines = ["A", "B", "C"]
        result = apply_baseline_drift(lines, line_height=30)
        for i in range(1, len(result)):
            assert result[i][1] > result[i - 1][1]


class TestApplyKerningJitter:
    """测试字距随机偏移。"""

    def test_preserves_char_count(self):
        """返回的字符数应与输入一致。"""
        chars = ["H", "e", "l", "l", "o"]
        positions = [0, 20, 40, 60, 80]
        result = apply_kerning_jitter(chars, positions, max_jitter=1)
        assert len(result) == len(chars)

    def test_jitter_within_range(self):
        """偏移量应在 ±max_jitter 范围内。"""
        chars = ["H", "e", "l", "l", "o"]
        positions = [100, 120, 140, 160, 180]
        result = apply_kerning_jitter(chars, positions, max_jitter=1)
        for i, (_, x_pos) in enumerate(result):
            diff = x_pos - positions[i]
            assert abs(diff) <= 1
