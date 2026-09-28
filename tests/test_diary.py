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


def test_backfill_walks_the_cursor_in_capped_slices(monkeypatch, tmp_path):
    cur = tmp_path / "cursor"
    cur.write_text(str(10 * H))                       # posted up to 10:00
    monkeypatch.setenv("DIARY_STATE", str(cur))
    monkeypatch.setenv("DIARY_MAX_HOURS", "4")
    start, end = diary.window("x/y", 30 * H, None)    # 20h of backlog, but only a 4h slice this run
    assert start == 10 * H and end == 14 * H


def test_backfill_is_an_empty_slice_once_caught_up(monkeypatch, tmp_path):
    cur = tmp_path / "cursor"
    cur.write_text(str(30 * H))
    monkeypatch.setenv("DIARY_STATE", str(cur))
    monkeypatch.setenv("DIARY_MAX_HOURS", "4")
    assert diary.window("x/y", 30 * H, None) == (30 * H, 30 * H)


def test_hours_override_ignores_the_cursor_and_the_cap(monkeypatch, tmp_path):
    cur = tmp_path / "cursor"
    cur.write_text(str(10 * H))
    monkeypatch.setenv("DIARY_STATE", str(cur))
    monkeypatch.setenv("DIARY_MAX_HOURS", "4")         # a manual --hours must not be truncated by the cap
    start, end = diary.window("x/y", 30 * H, 6)
    assert end == 30 * H and start == 30 * H - 6 * H


def test_cursor_is_saved_and_read_back(monkeypatch, tmp_path):
    cur = tmp_path / "cursor"
    monkeypatch.setenv("DIARY_STATE", str(cur))
    diary.save_cursor(14 * H)
    assert cur.read_text() == str(14 * H) and diary._cursor() == 14 * H


def test_a_missing_or_bad_cursor_reads_as_none(monkeypatch, tmp_path):
    monkeypatch.delenv("DIARY_STATE", raising=False)
    assert diary._cursor() is None
    bad = tmp_path / "cursor"
    bad.write_text("not-a-number")
    monkeypatch.setenv("DIARY_STATE", str(bad))
    assert diary._cursor() is None


def test_writer_prefers_free_gemini_then_anthropic(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert diary.writer() == ("anthropic", "claude-sonnet-5")
    monkeypatch.setenv("GEMINI_API_KEY", "g")            # gemini wins when both are present
    assert diary.writer() == ("gemini", "gemini-3.8-flash")
    monkeypatch.setenv("DIARY_MODEL", "gemini-2.0-flash")
    assert diary.writer() == ("gemini", "gemini-2.0-flash")


def test_write_uses_gemini_and_appends_release_links(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("DIARY_MODEL", raising=False)
    monkeypatch.setattr(diary, "_post",
                        lambda req: {"candidates": [{"content": {"parts": [{"text": "<b>Shipped</b>\nfetch fixed on two chains"}]}}]})
    out = diary.write({"releases": [{"tag": "v0.1", "url": "http://x/v0.1"}]})
    assert out.startswith("<b>Shipped</b>") and out.endswith("v0.1: http://x/v0.1")


def test_write_honours_a_nothing_reply_from_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(diary, "_post",
                        lambda req: {"candidates": [{"content": {"parts": [{"text": "NOTHING"}]}}]})
    assert diary.write({"releases": []}) == "NOTHING"


def test_gate_drops_what_the_rules_forbid():
    assert diary.unfit("<b>Fine</b>\nwe fixed the fetch on two chains") is None
    assert diary.unfit("we shipped it — finally") == "dash"
    assert diary.unfit("see https://example.com") == "link"
    assert diary.unfit("deployed at 0xdeadbeefcafe") == "address or hash"
    assert diary.unfit("thanks @someone") == "handle"
    assert diary.unfit("a robust fix").startswith("word")
    assert diary.unfit("we won the hackathon").startswith("word")
    assert diary.unfit("x" * 901) == "too long"
