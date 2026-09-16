"""The diary's pure parts: the scrub, the window arithmetic, and the NOTHING rule. No network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "diary"))
import diary  # noqa: E402

H = 3600 * 1000


def test_scrub_removes_links_keys_hashes_and_addresses():
    s = diary.scrub("see https://example.com/x?token=abc ghp_ABCDEFGHIJKLMNOP 0x" + "ab" * 20 + " " + "f" * 40 + " api_key=zzz")
    assert "https://" not in s and "ghp_" not in s and "0xabab" not in s and "f" * 40 not in s and "zzz" not in s
    assert "[link]" in s and "[secret]" in s and "[address]" in s and "[hash]" in s and "api_key=[redacted]" in s


def test_scrub_keeps_ordinary_words():
    assert diary.scrub("Eight lenses, 52 tests, block 60762176") == "Eight lenses, 52 tests, block 60762176"


def test_window_with_hours_is_a_fixed_span_back_from_the_closed_boundary():
    now = 13 * H + 25 * 60 * 1000  # 13:25 on day zero
    start, end = diary.window("x/y", now, 48)
    assert end == 12 * H and start == end - 48 * H


def test_window_end_never_includes_the_open_step():
    assert diary.window("x/y", 2 * H - 1, 2)[1] == 0
    assert diary.window("x/y", 2 * H, 2)[1] == 2 * H


def test_nothing_rule_accepts_only_the_word():
    assert diary.is_nothing("NOTHING") and diary.is_nothing("  nothing.\n") and diary.is_nothing("")
    assert not diary.is_nothing("<b>Nothing broke</b>\nwe shipped the diary")
