# QUORUM buy bot

Announces every on-chain buy of **$50 or more** from the QUORUM Uniswap v4 pool on Robinhood Chain.

- Pool (v4, QUORUM/ETH): `0xc05ab314…ca3c8` · PoolManager `0x8366a39CC670B4001A1121B8F6A443A643e40951`
- A buy is a `Swap` event filtered by the pool id where the swapper receives QUORUM. USD is the ETH
  leg times the ETH price the pool itself implies (DexScreener `priceUsd / priceNative`) — no separate
  price oracle is trusted.
- No secret lives in the code. Without Telegram credentials the bot prints instead of posting.

## Run

```bash
# see what it would post, post nothing
.venv/bin/python bot/buybot.py --once --dry-run

# post to Telegram, polling every 30s (you provide the two secrets, never in the repo)
export BUYBOT_TG_TOKEN=...      # from @BotFather
export BUYBOT_TG_CHAT=...       # the channel/group id the bot is an admin of
.venv/bin/python bot/buybot.py
```

Optional env: `BUYBOT_MIN_USD` (default 50), `QUORUM_RPC` (default the public node), `BUYBOT_STATE`
(default `bot/.buybot-state.json`).

## What you need to provide

1. A Telegram bot from **@BotFather** → gives `BUYBOT_TG_TOKEN`. Add the bot to your channel/group as
   an admin, and get the chat id (`BUYBOT_TG_CHAT`), e.g. from `@getidsbot` or the `getUpdates` API.
2. Keep it running: a `launchd`/`tmux`/`systemd` service, or a `* * * * *` cron of `--once`. The state
   file makes a restart safe — it never double-posts.

The two secrets stay in your shell/service env. This bot never reads or stores them.
