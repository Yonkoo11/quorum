"""Print your Telegram chat id, reading the token from the environment (never from the chat).

Run after you have created the bot AND sent it a message (or added it to your channel and posted once):
    source ~/.quorum-buybot.env && python bot/chat-id.py
It prints only the chat id and title. It never prints the token.
"""
import json, os, sys, urllib.request
tok = os.environ.get("BUYBOT_TG_TOKEN")
if not tok:
    sys.exit("set BUYBOT_TG_TOKEN in ~/.quorum-buybot.env and `source` it first")
with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=15) as r:
    for u in json.load(r).get("result", []):
        chat = (u.get("channel_post") or u.get("message") or {}).get("chat", {})
        if chat:
            print(f"chat id: {chat.get('id')}   title: {chat.get('title') or chat.get('username') or chat.get('first_name')}")
