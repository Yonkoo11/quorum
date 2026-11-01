#!/bin/bash
# 24/7 watcher, one chain per launchd agent (com.quorum.watch-<chain>). Usage: watch-live.sh ethereum|arbitrum
# Telegram: the bot token and the watch chat come from ~/.quorum-buybot.env (QUORUM_WATCH_TG_CHAT is
# written by scripts/watch-telegram-setup.sh). Without them the watcher prints only.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] && source "$ENV"
case ${1:?chain: ethereum or arbitrum} in
  ethereum)   # 12 s blocks: one block at a time, all five rules
    exec .venv/bin/python -u -m watch.live --chain ethereum --watchlist watch/seeds/binance14-2026-10-29.json \
      --state ai/watch-state.json --log ai/watch-live.jsonl --heartbeat-minutes 60 ;;
  arbitrum)   # ~4 blocks/s on a public endpoint: one pass per poll, code + log rules (see watch/live.py)
    exec .venv/bin/python -u -m watch.live --chain arbitrum --watchlist watch/seeds/quorum-arbitrum.json \
      --range --catch-up 5000 --state ai/watch-state-arbitrum.json --log ai/watch-live-arbitrum.jsonl \
      --heartbeat-minutes 60 ;;
  *) echo "unknown chain: $1" >&2; exit 2 ;;
esac
