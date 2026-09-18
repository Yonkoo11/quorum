#!/usr/bin/env bash
# One-time setup for the diary. Asks for the three values, sets them as repository
# secrets under the right names, then runs the diary once in dry mode and prints
# what it would have posted. Nothing typed here is echoed or saved anywhere else.
set -euo pipefail
cd "$(dirname "$0")/.."

read -rsp "Anthropic API key (typing is hidden): " ANTHROPIC; echo
read -rsp "Telegram bot token from BotFather (hidden): " TG_TOKEN; echo
read -rp  "Telegram chat id or public group name [@runQuorumchat]: " TG_CHAT
TG_CHAT="${TG_CHAT:-@runQuorumchat}"

printf '%s' "$ANTHROPIC" | gh secret set ANTHROPIC_API_KEY
printf '%s' "$TG_TOKEN"  | gh secret set TELEGRAM_BOT_TOKEN
printf '%s' "$TG_CHAT"   | gh secret set TELEGRAM_CHAT_ID
unset ANTHROPIC TG_TOKEN
echo; echo "Secrets set:"; gh secret list

echo; echo "Dry run over the last 48 hours (posts nothing)..."
gh workflow run diary.yml -f dry=true -f hours=48 >/dev/null
sleep 8
RUN=$(gh run list --workflow diary.yml --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch "$RUN" --exit-status >/dev/null || true
gh run view "$RUN" --log 2>/dev/null | sed -n '/window /,$p' | sed 's/^[^\t]*\t[^\t]*\t//' || gh run view "$RUN"
