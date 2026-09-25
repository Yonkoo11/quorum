"""What an explorer's answer may and may not do: it can give us a verified file under targets/<chain>/, or be refused."""
import io
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import requests

from quorum import cli, targets


class _Raw(io.BytesIO):
    def read(self, n=-1, decode_content=False):
        return super().read(n)


def _answer(payload, status=200):
    r = mock.Mock()
    r.status_code = status
    r.raw = _Raw(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
    r.raise_for_status = mock.Mock(side_effect=None if status == 200 else requests.HTTPError(f"HTTP {status}"))
    return r


def _tmp_targets():
    return mock.patch.object(targets, "TARGET_DIR", Path(tempfile.mkdtemp()))


def test_a_multi_file_contract_becomes_one_file_under_its_chain():
    payload = {"is_verified": True, "name": "Router", "file_path": "src/Router.sol", "source_code": "contract Router {}",
               "additional_sources": [{"file_path": "lib/Lib.sol", "source_code": "library Lib {}"},
                                      {"file_path": "lib/Empty.sol", "source_code": ""}]}
    with _tmp_targets(), mock.patch.object(targets.requests, "get", return_value=_answer(payload)) as get:
        path = targets.save("0x" + "ab" * 20, "arbitrum")
        assert get.call_args.args[0] == "https://arbitrum.blockscout.com/api/v2/smart-contracts/0x" + "ab" * 20
        assert path == targets.TARGET_DIR / "arbitrum" / "Router.sol"
        text = path.read_text()
        assert text.startswith("// file: src/Router.sol\ncontract Router {}")
        assert "// file: lib/Lib.sol\nlibrary Lib {}" in text and "Empty" not in text
        assert list(targets.load_targets()) == ["arbitrum/Router.sol"]


def test_a_single_file_contract_is_saved_as_is_and_keys_by_chain_and_name():
    payload = {"is_verified": True, "name": "WETH9", "file_path": "WETH9.sol", "source_code": "contract WETH9 {}"}
    with _tmp_targets(), mock.patch.object(targets.requests, "get", side_effect=lambda *a, **k: _answer(payload)):
        targets.save("0x" + "42" * 20, "base")
        targets.save("0x" + "42" * 20, "optimism")
        got = targets.load_targets()
        assert got == {"base/WETH9.sol": "contract WETH9 {}", "optimism/WETH9.sol": "contract WETH9 {}"}


def test_unverified_or_empty_source_is_refused_naming_the_chain():
    for payload in ({"is_verified": False, "source_code": "x"}, {"is_verified": True, "source_code": ""}, [], b"<html>"):
        with mock.patch.object(targets.requests, "get", return_value=_answer(payload)):
            with pytest.raises(RuntimeError) as exc:
                targets.fetch_source("0x" + "01" * 20, "polygon")
            assert "polygon" in str(exc.value)


def test_a_404_is_no_verified_source_not_a_traceback():
    with mock.patch.object(targets.requests, "get", return_value=_answer({}, status=404)):
        with pytest.raises(RuntimeError) as exc:
            targets.fetch_source("0x" + "01" * 20, "ethereum")
        assert str(exc.value).endswith("has no verified source on ethereum")


def test_bsc_reads_from_sourcify_because_it_has_no_blockscout_instance():
    payload = {"compilation": {"name": "Token"},
               "sources": {"src/Token.sol": {"content": "contract Token {}"},
                           "lib/Math.sol": {"content": "library Math {}"},
                           "lib/Empty.sol": {"content": ""}}}
    with _tmp_targets(), mock.patch.object(targets.requests, "get", return_value=_answer(payload)) as get:
        path = targets.save("0x" + "cd" * 20, "bsc")
        assert get.call_args.args[0] == (
            "https://sourcify.dev/server/v2/contract/56/0x" + "cd" * 20 + "?fields=sources,compilation")
        assert path == targets.TARGET_DIR / "bsc" / "Token.sol"
        text = path.read_text()
        # sorted by path, so the ordering of a multi-file answer is the same on every run
        assert text.startswith("// file: lib/Math.sol\nlibrary Math {}")
        assert "// file: src/Token.sol\ncontract Token {}" in text and "Empty" not in text


def test_a_sourcify_answer_with_no_sources_is_refused_naming_the_chain():
    for payload in ({"sources": {}}, {"sources": {"a.sol": {"content": ""}}}, {}):
        with mock.patch.object(targets.requests, "get", return_value=_answer(payload)):
            with pytest.raises(RuntimeError) as exc:
                targets.fetch_source("0x" + "01" * 20, "bsc")
            assert "no verified source on bsc" in str(exc.value)


def test_an_unknown_chain_is_refused_before_any_request():
    with mock.patch.object(targets.requests, "get") as get:
        with pytest.raises(ValueError):
            targets.save("0x" + "01" * 20, "solana")
        get.assert_not_called()


def test_the_explorers_name_cannot_leave_the_chain_folder():
    payload = {"is_verified": True, "name": "../../etc/passwd", "source_code": "contract X {}"}
    with _tmp_targets(), mock.patch.object(targets.requests, "get", return_value=_answer(payload)):
        path = targets.save("0x" + "01" * 20, "ethereum")
        assert path.parent == targets.TARGET_DIR / "ethereum"
        assert path.name == "_.._etc_passwd.sol"


def test_an_oversized_answer_is_refused():
    big = b'{"is_verified": true, "source_code": "' + b"x" * (targets.MAX_BYTES + 10) + b'"}'
    with mock.patch.object(targets.requests, "get", return_value=_answer(big)):
        with pytest.raises(RuntimeError) as exc:
            targets.fetch_source("0x" + "01" * 20, "base")
        assert "over 5 MB" in str(exc.value)


def test_fetch_command_keeps_going_and_reports_failure(capsys):
    good = {"is_verified": True, "name": "Good", "source_code": "contract Good {}"}
    answers = [_answer({"is_verified": False}), _answer(good)]
    with _tmp_targets(), mock.patch.object(targets.requests, "get", side_effect=answers):
        rc = cli.main(["fetch", "--chain", "optimism", "0x" + "01" * 20, "0x" + "02" * 20])
    out = capsys.readouterr().out
    assert rc == 1
    assert "not saved" in out and "no verified source on optimism" in out
    assert "saved" in out and "optimism/Good.sol" in out


def test_explicit_targets_with_one_name_on_two_chains_stay_two_targets():
    root = Path(tempfile.mkdtemp())
    for chain in ("base", "optimism"):
        (root / chain).mkdir()
        (root / chain / "WETH9.sol").write_text(f"contract WETH9 {{ /* {chain} */ }}")
    (root / "Router.sol").write_text("contract Router {}")
    got = targets.load_targets([str(root / "base/WETH9.sol"), str(root / "optimism/WETH9.sol"), str(root / "Router.sol")])
    assert set(got) == {"base/WETH9.sol", "optimism/WETH9.sol", "Router.sol"}
