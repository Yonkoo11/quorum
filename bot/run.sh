#!/bin/zsh
# Run the QUORUM buy bot. Secrets are sourced from a file OUTSIDE the repo that only you write.
# Create ~/.quorum-buybot.env with:
#   export BUYBOT_TG_TOKEN=123456:ABC...      # from @BotFather
#   export BUYBOT_TG_CHAT=-100xxxxxxxxxx       # your channel/group id
# then: bot/run.sh
set -u
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] && source "$ENV"
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python bot/buybot.py "$@"
