# Run the buy bot 24/7 (independent of your Mac)

Your Mac runs the bot only while it's awake and you're logged in (via `launchctl` +
`com.quorum.buybot`). To run it whether your Mac is on or off, put it on a small always-on host. The
bot is one long-lived Python process that polls a public RPC and posts to Telegram — it fits any of
these. **In every case the token goes in the host's secret store, never in the repo or the image.**

Pick one:

## Option A — Railway (easiest, no terminal)
Best if you want a web UI and no server to manage. ~$5/mo of usage, often within the free credit.
1. Push this repo to GitHub (already done: `Yonkoo11/quorum`).
2. On railway.app: **New Project → Deploy from GitHub repo → pick quorum**, set the root/Dockerfile
   path to `bot/`.
3. In the service's **Variables**, add `BUYBOT_TG_TOKEN` and `BUYBOT_TG_CHAT` (and `BUYBOT_MIN_USD=50`).
4. Deploy. It runs the `Dockerfile` here and stays up. Logs are in the Railway dashboard.

## Option B — Fly.io (free-tier friendly, one small always-on machine)
1. Install flyctl and sign in: `brew install flyctl && fly auth login`.
2. From `bot/`: `fly launch --no-deploy` (accept the Dockerfile; name it `quorum-buybot`).
3. Set secrets (these never touch the repo):
   `fly secrets set BUYBOT_TG_TOKEN=... BUYBOT_TG_CHAT=@runQuorumchat BUYBOT_MIN_USD=50`
4. `fly deploy`. One shared-cpu-1x machine runs the worker; `fly logs` to watch it.

## Option C — A $4/mo VPS you control (Hetzner, DigitalOcean, etc.)
Most control, cheapest, a little terminal work. On a fresh Ubuntu box:
```bash
git clone https://github.com/Yonkoo11/quorum && cd quorum/bot
sudo apt update && sudo apt install -y python3-venv
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
printf 'BUYBOT_TG_TOKEN=...\nBUYBOT_TG_CHAT=@runQuorumchat\nBUYBOT_MIN_USD=50\n' > ~/.quorum-buybot.env
```
Then a systemd service so it restarts on crash and boot — copy `quorum-buybot.service` below to
`/etc/systemd/system/`, edit the `User=` and paths, and:
```bash
sudo systemctl enable --now quorum-buybot
journalctl -u quorum-buybot -f    # watch it
```

`quorum-buybot.service`:
```ini
[Unit]
Description=QUORUM buy bot
After=network-online.target

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/quorum
EnvironmentFile=/home/YOUR_USER/.quorum-buybot.env
ExecStart=/home/YOUR_USER/quorum/.venv/bin/python bot/buybot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## After it's live on a host, turn off the Mac copy
So you don't get double posts, stop the launchd agent on your Mac:
```bash
launchctl unload ~/Library/LaunchAgents/com.quorum.buybot.plist
```
(The two would each post the same buys otherwise, since they keep separate state.)

## Which to pick
- Want the least fuss and don't mind ~$5/mo: **Railway** (Option A).
- Want it as free as possible and don't mind a CLI: **Fly.io** (Option B).
- Want full control and the lowest cost, comfortable with a terminal: **a VPS** (Option C).

All three keep the token in the host's secrets, restart the bot if it crashes, and run whether your
Mac is on or not. The bot's own state file prevents double-posting across restarts.
