import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
import buybot


def word(signed: int) -> bytes:
    return (signed & (1 << 256) - 1).to_bytes(32, "big")


def swap_log(eth_delta: int, quorum_delta: int, block=1, tx="0xaa", idx=0) -> dict:
    # currency0 = ETH, currency1 = QUORUM; then sqrtPrice, liquidity, tick, fee (unused)
    data = word(eth_delta) + word(quorum_delta) + word(0) * 4

    class H(str):
        def hex(self):
            return self
    return {"data": data, "blockNumber": block, "logIndex": idx,
            "transactionHash": H(tx), "topics": [buybot.SWAP_TOPIC, buybot.POOL_ID]}


class FakeW3:
    def __init__(self, logs):
        self._logs = logs
        self.eth = self

    def get_logs(self, _):
        return self._logs


def test_a_swap_that_receives_quorum_is_a_buy():
    """v4 emits the swapper's delta: positive QUORUM means QUORUM was received -> a buy."""
    w3 = FakeW3([swap_log(eth_delta=-10**16, quorum_delta=5_000_000 * 10**18)])
    buys = buybot.buys_in(w3, 1, 2, price=2000.0)
    assert len(buys) == 1 and round(buys[0]["usd"]) == 20  # 0.01 ETH * $2000


def test_a_swap_that_pays_quorum_is_a_sell_and_ignored():
    w3 = FakeW3([swap_log(eth_delta=10**16, quorum_delta=-5_000_000 * 10**18)])
    assert buybot.buys_in(w3, 1, 2, price=2000.0) == []


def test_usd_is_the_eth_leg_times_the_pool_price():
    w3 = FakeW3([swap_log(eth_delta=-3 * 10**16, quorum_delta=1 * 10**18)])
    assert round(buybot.buys_in(w3, 1, 2, price=2689.55)[0]["usd"]) == 81  # 0.03 * 2689.55


def test_no_price_leaves_usd_unknown_rather_than_guessed():
    w3 = FakeW3([swap_log(eth_delta=-10**16, quorum_delta=10**18)])
    assert buybot.buys_in(w3, 1, 2, price=None)[0]["usd"] is None


def test_signed_int128_round_trips_a_negative_leg():
    assert buybot.s128(int.from_bytes(word(-(10**16)), "big")) == -(10**16)


def test_the_message_shows_usd_and_the_tx_link():
    msg = buybot.format_buy({"usd": 80, "eth": 0.0297, "quorum": 4_491_775, "tx": "0xf41e", "log": 0, "block": 1})
    assert "$80" in msg and "QUORUM buy" in msg and buybot.EXPLORER_TX in msg
