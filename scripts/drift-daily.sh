#!/bin/bash
# Daily (launchd com.quorum.drift, 09:05): re-fetch the facts the Zcash checks rest on and report any change.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV=$HOME/.quorum-buybot.env
[ -f "$ENV" ] && source "$ENV"
exec .venv/bin/python -u -m watch.drift --notify
